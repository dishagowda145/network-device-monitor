import os
import socket
import tempfile
import threading
import unittest

import app as monitor
from app import check_tcp, create_app


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TcpServer:
    """A tiny local server so tests can check a device that is really up."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
                conn.close()
            except OSError:
                return

    def stop(self):
        self.sock.close()


class CheckTests(unittest.TestCase):
    def test_up_device(self):
        server = TcpServer()
        self.addCleanup(server.stop)
        is_up, ms, err = check_tcp("127.0.0.1", server.port)
        self.assertTrue(is_up)
        self.assertIsNotNone(ms)
        self.assertIsNone(err)

    def test_down_device(self):
        is_up, ms, err = check_tcp("127.0.0.1", free_port())
        self.assertFalse(is_up)
        self.assertIsNone(ms)
        self.assertTrue(err)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.client = create_app(db_path=self.db_path).test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def add(self, name="Router", host="127.0.0.1", port=80):
        return self.client.post("/api/devices", json={"name": name, "host": host, "port": port})

    def test_validation(self):
        self.assertEqual(self.add(name="").status_code, 400)
        self.assertEqual(self.add(host="bad host!").status_code, 400)
        self.assertEqual(self.add(host="999.1.1.1").status_code, 400)
        self.assertEqual(self.add(host="-bad.example.com").status_code, 400)
        self.assertEqual(self.add(port=0).status_code, 400)
        self.assertEqual(self.add(port=70000).status_code, 400)
        res = self.client.post("/api/devices", json={"name": "x", "host": "127.0.0.1", "port": "abc"})
        self.assertEqual(res.status_code, 400)

    def test_add_up_device_and_summary(self):
        server = TcpServer()
        self.addCleanup(server.stop)
        res = self.add(port=server.port)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["status"], "up")
        self.assertEqual(self.client.get("/api/summary").get_json(),
                         {"total": 1, "up": 1, "down": 0, "unknown": 0})

    def test_duplicate_rejected(self):
        port = free_port()
        self.assertEqual(self.add(port=port).status_code, 201)
        self.assertEqual(self.add(name="Other", port=port).status_code, 409)

    def test_down_device_creates_alert(self):
        res = self.add(port=free_port())
        self.assertEqual(res.get_json()["status"], "down")
        alerts = self.client.get("/api/alerts").get_json()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "down")

    def test_down_then_recovered(self):
        port = free_port()
        device = self.add(port=port).get_json()  # down
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(5)
        self.addCleanup(server.close)
        res = self.client.post(f"/api/devices/{device['id']}/check")
        self.assertEqual(res.get_json()["status"], "up")
        kinds = [a["kind"] for a in self.client.get("/api/alerts").get_json()]
        self.assertEqual(kinds, ["recovered", "down"])

    def test_history_and_delete(self):
        device = self.add(port=free_port()).get_json()
        self.client.post(f"/api/devices/{device['id']}/check")
        history = self.client.get(f"/api/devices/{device['id']}/history").get_json()
        self.assertEqual(len(history), 2)
        self.assertEqual(self.client.delete(f"/api/devices/{device['id']}").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/devices/{device['id']}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/devices/{device['id']}/history").status_code, 404)

    def test_security_headers_present(self):
        res = self.client.get("/api/devices")
        self.assertEqual(res.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(res.headers["X-Frame-Options"], "DENY")

    def test_bad_history_limit(self):
        device = self.add(port=free_port()).get_json()
        res = self.client.get(f"/api/devices/{device['id']}/history?limit=abc")
        self.assertEqual(res.status_code, 400)

    def test_check_all_runs_for_every_device(self):
        a, b = free_port(), free_port()
        self.add(name="A", port=a)
        self.add(name="B", port=b)
        monitor.check_all(self.db_path)
        for d in self.client.get("/api/devices").get_json():
            history = self.client.get(f"/api/devices/{d['id']}/history").get_json()
            self.assertEqual(len(history), 2)

class BlockedHostTests(unittest.TestCase):
    """The SSRF guard refuses private addresses only when BLOCK_PRIVATE_HOSTS=1."""

    def setUp(self):
        os.environ["BLOCK_PRIVATE_HOSTS"] = "1"

    def tearDown(self):
        os.environ.pop("BLOCK_PRIVATE_HOSTS", None)

    def test_private_hosts_blocked(self):
        self.assertTrue(monitor.is_blocked_host("127.0.0.1"))
        self.assertTrue(monitor.is_blocked_host("10.0.0.5"))
        self.assertTrue(monitor.is_blocked_host("192.168.1.1"))
        self.assertTrue(monitor.is_blocked_host("169.254.169.254"))

    def test_check_refuses_private_host(self):
        up, ms, err = check_tcp("127.0.0.1", 80)
        self.assertFalse(up)
        self.assertEqual(err, "Address not allowed")

    def test_check_connects_to_the_address_it_validated(self):
        """A name that resolves to a private address is refused at check time (DNS rebinding)."""
        real = socket.getaddrinfo
        def fake(host, port, *a, **k):
            if host == "rebind.example.com":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", port or 0))]
            return real(host, port, *a, **k)
        socket.getaddrinfo = fake
        self.addCleanup(setattr, socket, "getaddrinfo", real)
        up, _ms, err = check_tcp("rebind.example.com", 80)
        self.assertFalse(up)
        self.assertEqual(err, "Address not allowed")

    def test_guard_off_by_default(self):
        os.environ.pop("BLOCK_PRIVATE_HOSTS", None)
        self.assertFalse(monitor.is_blocked_host("127.0.0.1"))


if __name__ == "__main__":
    unittest.main()
