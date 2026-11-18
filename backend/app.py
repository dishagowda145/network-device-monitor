"""Network Device Monitor API (Flask + SQLite).

A background thread checks every device with a TCP connection to its host and port,
stores each result, and records an alert whenever a device goes down or comes back up.
TCP checks are used instead of ICMP ping because ping needs admin rights.
"""
import ipaddress
import logging
import os
import re
import socket
import sqlite3
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

MAX_DEVICES = 50
CHECK_TIMEOUT = 2.0  # seconds
HOST_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}"  # IPv4
    r"|(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*)$"
)

IPV4_RE = re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$")


def valid_host(host):
    """Accept an IPv4 address or a host name. All-digit values must be a real IPv4 address."""
    if re.fullmatch(r"[\d.]+", host):
        return bool(IPV4_RE.match(host))
    return bool(HOST_RE.match(host))


def blocking_enabled():
    return os.environ.get("BLOCK_PRIVATE_HOSTS") == "1"


def is_blocked_host(host):
    """Security: when BLOCK_PRIVATE_HOSTS=1, refuse loopback, private and link-local addresses.

    A public demo must not let visitors probe the server's own network (SSRF).
    Off by default so local development and tests can use 127.0.0.1.
    """
    if not blocking_enabled():
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False  # unresolvable names are reported as "down" by the check itself
    return any(not ipaddress.ip_address(info[4][0]).is_global for info in infos)


log = logging.getLogger("monitor")

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    UNIQUE (host, port)
);
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    is_up INTEGER NOT NULL,
    response_ms REAL,
    error TEXT,
    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,            -- 'down' or 'recovered'
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_checks_device ON checks (device_id, id DESC);
"""


def check_tcp(host, port, timeout=CHECK_TIMEOUT):
    """Try a TCP connection. Returns (is_up, response_ms, error_message).

    The name is resolved once and we connect to that exact address. Checking the name and
    then connecting to it separately would let a DNS answer change in between (DNS rebinding)
    and bypass the private-address guard.
    """
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False, None, "Host name could not be resolved"
    if blocking_enabled() and any(not ipaddress.ip_address(i[4][0]).is_global for i in infos):
        return False, None, "Address not allowed"
    last_error = "Connection failed"
    for family, socktype, proto, _name, sockaddr in infos:
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(timeout)
                sock.connect(sockaddr)
            return True, round((time.perf_counter() - start) * 1000, 1), None
        except socket.timeout:
            last_error = "Connection timed out"
        except OSError as exc:
            last_error = exc.strerror or "Connection failed"
    return False, None, last_error


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def record_check(conn, device_id, is_up, response_ms, error):
    """Store a check and write an alert if the state changed since the last check."""
    previous = conn.execute(
        "SELECT is_up FROM checks WHERE device_id = ? ORDER BY id DESC LIMIT 1", (device_id,)
    ).fetchone()
    conn.execute(
        "INSERT INTO checks (device_id, is_up, response_ms, error) VALUES (?, ?, ?, ?)",
        (device_id, int(is_up), response_ms, error),
    )
    device = conn.execute("SELECT name, host, port FROM devices WHERE id = ?", (device_id,)).fetchone()
    label = f"{device['name']} ({device['host']}:{device['port']})"
    if previous is not None and bool(previous["is_up"]) != is_up:
        kind = "recovered" if is_up else "down"
        message = f"{label} is back up" if is_up else f"{label} is down: {error}"
        conn.execute(
            "INSERT INTO alerts (device_id, kind, message) VALUES (?, ?, ?)", (device_id, kind, message)
        )
        log.warning(message)
    elif previous is None and not is_up:
        conn.execute(
            "INSERT INTO alerts (device_id, kind, message) VALUES (?, 'down', ?)",
            (device_id, f"{label} is down: {error}"),
        )
    conn.commit()


def check_all(db_path):
    conn = connect(db_path)
    try:
        for d in conn.execute("SELECT id, host, port FROM devices").fetchall():
            is_up, ms, err = check_tcp(d["host"], d["port"])
            record_check(conn, d["id"], is_up, ms, err)
        # Keep the table small: remove checks older than the newest 500 per device.
        conn.execute(
            "DELETE FROM checks WHERE id NOT IN ("
            "SELECT id FROM checks c WHERE (SELECT COUNT(*) FROM checks x "
            "WHERE x.device_id = c.device_id AND x.id > c.id) < 500)"
        )
        conn.commit()
    finally:
        conn.close()


def start_monitor(db_path, interval):
    def loop():
        while True:
            try:
                check_all(db_path)
            except Exception:  # keep the monitor alive whatever happens
                log.exception("Monitor cycle failed")
            time.sleep(interval)

    thread = threading.Thread(target=loop, daemon=True, name="monitor")
    thread.start()
    return thread


def create_app(db_path=None, start_background=False, interval=30):
    app = Flask(__name__, static_folder=None)
    db_path = db_path or os.path.join(BASE_DIR, "monitor.db")
    app.config["DB_PATH"] = db_path

    init = connect(db_path)
    init.executescript(SCHEMA)
    init.commit()
    init.close()

    def error(message, code=400):
        return jsonify({"error": message}), code

    LATEST_SQL = """
        SELECT d.id, d.name, d.host, d.port,
               c.is_up, c.response_ms, c.error, c.checked_at
        FROM devices d
        LEFT JOIN checks c ON c.id = (SELECT MAX(id) FROM checks WHERE device_id = d.id)
    """

    def device_dict(row):
        return {
            "id": row["id"], "name": row["name"], "host": row["host"], "port": row["port"],
            "status": None if row["is_up"] is None else ("up" if row["is_up"] else "down"),
            "response_ms": row["response_ms"], "error": row["error"], "checked_at": row["checked_at"],
        }

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/api/devices")
    def list_devices():
        conn = connect(db_path)
        try:
            rows = conn.execute(LATEST_SQL + " ORDER BY d.name").fetchall()
        finally:
            conn.close()
        return jsonify([device_dict(r) for r in rows])

    @app.post("/api/devices")
    def add_device():
        body = request.get_json(silent=True) or {}
        name = str(body.get("name", "")).strip()
        host = str(body.get("host", "")).strip().lower()
        try:
            port = int(body.get("port"))
        except (TypeError, ValueError):
            return error("Port must be a number")
        if not 1 <= len(name) <= 60:
            return error("Name must be 1 to 60 characters")
        if not valid_host(host):
            return error("Enter a valid host name or IPv4 address")
        if is_blocked_host(host):
            return error("Private and local addresses are not allowed on this server")
        if not 1 <= port <= 65535:
            return error("Port must be between 1 and 65535")
        conn = connect(db_path)
        try:
            if conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] >= MAX_DEVICES:
                return error(f"Limit of {MAX_DEVICES} devices reached", 409)
            try:
                cur = conn.execute(
                    "INSERT INTO devices (name, host, port) VALUES (?, ?, ?)", (name, host, port)
                )
            except sqlite3.IntegrityError:
                return error("That host and port is already being monitored", 409)
            conn.commit()
            device_id = cur.lastrowid
            # First check straight away so the dashboard does not show "unknown".
            is_up, ms, err = check_tcp(host, port)
            record_check(conn, device_id, is_up, ms, err)
            row = conn.execute(LATEST_SQL + " WHERE d.id = ?", (device_id,)).fetchone()
        finally:
            conn.close()
        return jsonify(device_dict(row)), 201

    @app.delete("/api/devices/<int:device_id>")
    def delete_device(device_id):
        conn = connect(db_path)
        try:
            cur = conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            conn.commit()
        finally:
            conn.close()
        if cur.rowcount == 0:
            return error("Device not found", 404)
        return "", 204

    @app.post("/api/devices/<int:device_id>/check")
    def check_now(device_id):
        conn = connect(db_path)
        try:
            device = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
            if device is None:
                return error("Device not found", 404)
            is_up, ms, err = check_tcp(device["host"], device["port"])
            record_check(conn, device_id, is_up, ms, err)
            row = conn.execute(LATEST_SQL + " WHERE d.id = ?", (device_id,)).fetchone()
        finally:
            conn.close()
        return jsonify(device_dict(row))

    @app.get("/api/devices/<int:device_id>/history")
    def history(device_id):
        try:
            limit = min(max(int(request.args.get("limit", 50)), 1), 200)
        except ValueError:
            return error("limit must be a number")
        conn = connect(db_path)
        try:
            if conn.execute("SELECT 1 FROM devices WHERE id = ?", (device_id,)).fetchone() is None:
                return error("Device not found", 404)
            rows = conn.execute(
                "SELECT is_up, response_ms, error, checked_at FROM checks "
                "WHERE device_id = ? ORDER BY id DESC LIMIT ?",
                (device_id, limit),
            ).fetchall()
        finally:
            conn.close()
        return jsonify([
            {"status": "up" if r["is_up"] else "down", "response_ms": r["response_ms"],
             "error": r["error"], "checked_at": r["checked_at"]} for r in rows
        ])

    @app.get("/api/summary")
    def summary():
        conn = connect(db_path)
        try:
            rows = conn.execute(LATEST_SQL).fetchall()
        finally:
            conn.close()
        up = sum(1 for r in rows if r["is_up"] == 1)
        down = sum(1 for r in rows if r["is_up"] == 0)
        return jsonify({"total": len(rows), "up": up, "down": down, "unknown": len(rows) - up - down})

    @app.get("/api/alerts")
    def alerts():
        conn = connect(db_path)
        try:
            rows = conn.execute(
                "SELECT id, device_id, kind, message, created_at FROM alerts ORDER BY id DESC LIMIT 30"
            ).fetchall()
        finally:
            conn.close()
        return jsonify([dict(r) for r in rows])

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:name>")
    def static_files(name):
        return send_from_directory(FRONTEND_DIR, name)

    if start_background:
        start_monitor(db_path, interval)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    interval = int(os.environ.get("CHECK_INTERVAL", "30"))
    # use_reloader=False so only one background monitor thread runs.
    create_app(start_background=True, interval=interval).run(
        host="0.0.0.0" if os.environ.get("PORT") else "127.0.0.1",
        port=int(os.environ.get("PORT", "5001")),
        debug=False,
    )
