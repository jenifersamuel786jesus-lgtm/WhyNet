# WhyNet Live

**Cross-layer network fault diagnosis and intelligent troubleshooting dashboard.** A beginner-friendly Flask/SQLite academic project with bounded TCP/DNS diagnostics, a responsive live dashboard, transparent evidence-based rules, test history, and API endpoints.

> **Scope note:** checks run from the machine hosting this app. A public deployment measures the hosting provider's outbound network—not the browser visitor's Wi-Fi, laptop, or ISP. TCP timing is not ICMP ping, and failed probes are not proof of a universal outage or exact root cause.

## Architecture

```text
Browser dashboard (HTML/CSS/JS, Bootstrap, Chart.js)
          │ JSON over same-origin HTTP; 15s status polling
          ▼
Flask API (validation, bounded diagnostic suite)
   ├── diagnostics/checks.py (DNS, connectivity, TCP timing)
   ├── diagnostics/fault_engine.py (rule-based findings)
   └── database/db.py ── SQLite (test_results, incidents)
```

Project layout:

```text
WhyNet/
├── app.py                    # Flask factory and REST API
├── config.py                 # timeouts and configurable thresholds
├── requirements.txt
├── database/db.py            # schema, persistence, history
├── diagnostics/checks.py     # bounded checks and validation
├── diagnostics/fault_engine.py
├── templates/index.html
├── static/css/style.css
├── static/js/dashboard.js
├── tests/                    # offline/mocked pytest suite
├── scripts/seed_database.py  # initialize empty DB (no fake samples)
├── README.md
└── PROJECT_REPORT.md         # academic report and viva prep
```

## Requirements

Python 3.10+ (tested with Python 3.11), pip, and outbound access for live diagnostics. The automated tests mock network I/O and do not need internet access.

### Windows (PowerShell)

```powershell
cd WhyNet
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/seed_database.py
python app.py
```

Open <http://127.0.0.1:5000>. If PowerShell blocks activation, use `\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `\.venv\Scripts\python.exe app.py`.

### Linux / macOS

```bash
cd WhyNet
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/seed_database.py
python app.py
```

Open <http://127.0.0.1:5000>.

### Run tests

```bash
python -m pytest -q
```

Tests use mocks for network-dependent paths. They cover validation, TCP success/refusal/timeout, latency and failure-rate calculations, diagnosis rules, API JSON responses, and SQLite history persistence.

## Demonstration

1. Load the dashboard and select **Run full suite**. The suite performs one fixed IP TCP reachability check, a DNS lookup, a TCP connect to `example.com:443`, and four bounded TCP timing attempts.
2. Inspect the green/amber/red cards and the diagnosis panel. Findings state evidence strength and list plausible causes/recommendations; they do not claim proof of a root cause.
3. View recent checks in the history table. Records persist in SQLite for the current database volume.
4. Use **Test connectivity**, **Test DNS**, or **Test TCP** for individual actions. TCP API callers can specify their own authorized hostname and single port.
5. Toggle monitoring pause/resume. While active, the browser refreshes the status and history every 15 seconds.

## API

All requests/responses are JSON where applicable. Example:

```bash
curl -s http://127.0.0.1:5000/api/health
curl -s -X POST http://127.0.0.1:5000/api/test/tcp \
  -H 'Content-Type: application/json' \
  -d '{"host":"example.com","port":443}'
curl -s -X POST http://127.0.0.1:5000/api/diagnostics/run \
  -H 'Content-Type: application/json' -d '{}'
```

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/status` | Latest result by test type |
| POST | `/api/test/connectivity` | Fixed IP-based TCP reachability check |
| POST | `/api/test/dns` | DNS lookup; optional `host` |
| POST | `/api/test/tcp` | Single host/port connection; optional `host`, `port` |
| POST | `/api/test/latency` | Bounded TCP timing; optional `host`, `port`, `attempts` (1–10) |
| POST | `/api/diagnostics/run` | Full suite; optional `dns_host`, `tcp_host`, `tcp_port` |
| GET | `/api/history?limit=50` | Recent persisted tests (1–200) |
| GET | `/api/incidents` | Recent persisted findings |

Invalid targets/ports return HTTP 400. All TCP socket connection attempts have a finite timeout; latency attempts are capped at ten. There is no arbitrary shell execution, port-range scanning, packet capture, or background daemon.

## Configuration

| Environment variable | Default | Meaning |
|---|---:|---|
| `DATABASE_PATH` | `./whynet.db` | SQLite file path |
| `CHECK_TIMEOUT` | `2.5` | Per TCP/socket timeout in seconds |
| `LATENCY_ATTEMPTS` | `4` | Full-suite TCP timing attempts |
| `HIGH_LATENCY_MS` | `250` | Rule threshold for high average timing |
| `PORT` | `5000` | Local HTTP port |

Use `python scripts/seed_database.py` to create schema. It intentionally inserts no fake history or fabricated test results.

## Deployment

This is a Python Flask app, so deploy as a Python web service (for example Render), not a static-only host. Build command: `pip install -r requirements.txt`; start command: `gunicorn app:app`. Configure a persistent disk and set `DATABASE_PATH` to its mount path if long-term history is required. Many free-tier filesystems are ephemeral and may reset SQLite history on restart/redeploy. A production deployment should also set a unique `SECRET_KEY`, configure resource/network limits, and use a managed database if durable multi-instance storage is needed.

## Limitations and security

- This checks the app server's egress only; browsers cannot use server-side socket calls to diagnose their own LAN.
- TCP handshake duration is an application-level approximation and depends on remote service health, DNS, firewall, geography, and load. ICMP may be blocked or deprioritized, so no ping-based claims are made.
- A small set of attempts is a sample, not a statistically robust packet-loss estimate. Its metric is labeled **failed attempts**, not ICMP packet loss.
- DNS is subject to the host operating system's resolver behavior. Target input is validated, but public deployment operators should add authentication/rate limiting before exposing diagnostic APIs broadly.
- The app uses SQLite by default. Concurrent production deployments should use a managed database.
- Rule-based diagnoses are heuristic explanations, not causal proof.

## License

Educational demonstration project. Add a license before redistribution if needed.
