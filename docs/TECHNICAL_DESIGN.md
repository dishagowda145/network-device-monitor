# Technical Design: Network Device Monitor

## Goal
Show at a glance whether devices or websites are reachable, how fast they respond, and warn when one goes down or recovers.

## Architecture
```
React dashboard --polls every 10 s--> Flask REST API --SQL--> SQLite
                                          ^
                          background thread: TCP check every 30 s
```
- **Front end:** React in `frontend/app.jsx`, plain CSS in `styles.css`.
- **API:** Flask app factory in `backend/app.py` (7 endpoints, see README).
- **Monitor:** one background thread loops over all devices, tries a TCP connection with a 2 second timeout, and stores the result.
- **Alerts:** a new alert is written only when the state changes (up to down, or down to up), so there is no alert spam.

## Data model
| Table | Columns |
| --- | --- |
| devices | id, name, host, port, created_at, UNIQUE(host, port) |
| checks | id, device_id, is_up, response_ms, error, created_at (index on device_id, id) |
| alerts | id, device_id, kind (`down` or `recovered`), message, created_at |

## Design decisions
| Decision | Why |
| --- | --- |
| TCP checks instead of ICMP ping | Ping needs administrator rights; TCP works anywhere |
| Only the newest 500 checks per device are kept | Keeps the database small |
| One monitor thread, one gunicorn worker | Two workers would run two monitors and write duplicate checks |
| Polling instead of WebSockets | Simple and enough for a 10 second refresh |

## Security and privacy
| Risk | Control |
| --- | --- |
| Bad input | Host must be a valid name or IPv4, port 1 to 65535, name 1 to 60 characters, at most 50 devices |
| SQL injection | Every query is parameterised |
| Duplicate devices | SQL UNIQUE constraint |
| Slow or hanging checks | 2 second timeout |
| XSS | React escapes all rendered text |
| **SSRF** (visitors making the server probe its own network) | `BLOCK_PRIVATE_HOSTS=1` refuses loopback, private and link-local addresses at add time and at check time. It is switched on in `render.yaml` and the Dockerfile. |
| No login | Fine for a local tool. Add authentication before exposing it widely. |

## Testing
`python -m unittest -v` (13 tests): validation, up and down checks against a real local TCP server and a closed port, alert creation, retention, and the SSRF guard. CI runs them on every push.

## Future work
Email or Slack alerts, response-time line chart, login and per-user device lists, HTTP status checks.
