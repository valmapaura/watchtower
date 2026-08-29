# � Watchtower — RTSP camera recorder

> An open‑source, self‑hosted motion recorder for any RTSP camera. Watch your feeds,
> record motion‑gated clips to a drive you own, and stay private by default.

Built to be **generic**: it talks to any camera that speaks RTSP (H.264/H.265, optional
audio). This repo's original dev hardware was a generic APCam WiFi camera — see
[`docs/camera-specs.md`](docs/camera-specs.md) for those notes.

> **🎯 Direction:** a home, open‑source camera streaming service that records footage to a
> drive you own — local disk first, cloud later, with a browser client.
> See [`docs/PROJECT.md`](docs/PROJECT.md) (vision & principles) and
> [`docs/ROADMAP.md`](docs/ROADMAP.md) (phased plan).

## 📹 Test camera

| Camera     | IP              | MAC vendor    | Platform        | Status                                                                    |
| ---------- | --------------- | ------------- | --------------- | ------------------------------------------------------------------------- |
| **cam720** | `192.168.1.247` | AltoBeam Inc. | APCam / QACloud | ✅ Working — documented in [`docs/camera-specs.md`](docs/camera-specs.md) |

## 🧰 What's inside

```
cam720/                  (repo root — rename to watchtower/ if you like)
├── README.md                  ← you are here
├── config.json                ← your real credentials (git-ignored)
├── config.example.json        ← template with placeholders
├── requirements.txt           ← Python deps (opencv-python)
├── Capture-Stream.ps1         ← record the RTSP stream to MP4 (video + optional AAC audio)
├── Camera-Limit-Tester.ps1    ← test how many concurrent streams the camera handles
├── docs/
│   ├── PROJECT.md             ← vision, design principles, modular architecture
│   ├── ROADMAP.md             ← phased plan: local disk → cloud → browser UI → Android
│   ├── camera-specs.md        ← test-camera hardware/firmware/network facts
│   └── access-guide.md        ← how to log in, admin panel, RTSP, troubleshooting
├── scripts/
│   ├── check-camera.ps1       ← health check: ping, ports, RTSP server
│   └── open-in-vlc.ps1        ← opens the live stream in VLC
└── src/
    ├── watchtower/            ← the recorder package (detector, recorder, storage)
    ├── cam_viewer.py          ← live RTSP viewer (OpenCV) with snapshots
    └── rtsp_digest_probe.py   ← pure-Python RTSP digest-auth explorer
```

## 🎥 Motion recorder (Phase 1)

Records motion‑gated clips: keeps a **30‑s pre‑buffer**, saves a clip when motion is
seen, and continues **5‑s after** motion stops. Pure Python + OpenCV, modular.

```bash
pip install -e .          # install the package (editable)
python -m pytest          # run the test suite (60 tests)

# Run continuously against the camera(s) in config.json
python -m watchtower.main --config config.json

# Record one short pass and exit (for testing)
python -m watchtower.main --config config.json --once
```

Clips are saved under `recordings/<camera>/<date>/` with a `manifest.json`.
Tune motion in `config.json` (`sensitivity`, `pre_seconds`, `post_seconds`, `min_duration`).

## 💾 Storage limits

Two independent rules keep disk usage in check (whichever triggers first):

- **`retention_days`** (default 30) — delete clips older than this. `0` = keep all.
- **`max_storage_gb`** (default 20) — delete the **oldest** clips until the total
  size of `recordings/` is under the cap. `0` = unlimited.

Both are adjustable in `config.json` or the Settings UI.

```json
{
  "retention_days": 30,
  "max_storage_gb": 20
}
```

## 🧠 Object detection (categorised clips)

By default the recorder uses **frame differencing** (motion = pixel change). You can
switch a camera to **object detection** (YOLO) to identify _what_ moved — people,
vehicles, animals — and store clips under a category folder:

```json
{
  "cameras": [
    {
      "name": "watchtower",
      "detector": "object",
      "detect_categories": ["person", "vehicle", "animal"]
    }
  ]
}
```

- Requires `pip install ultralytics` (opt-in per camera; more CPU/GPU-hungry).
- Categorised clips save to `recordings/<camera>/<date>/<category>/`.
- The web UI's Timeline filters by category; Settings picks the detector + categories.

## 🌐 Web API (Phase 4 prep)

A FastAPI layer that serves the clip library to a browser client. It does **not**
run the recorder — it reads what the recorder wrote.

```bash
python -m watchtower.api --config config.json          # localhost:8000
python -m watchtower.api --config config.json --host 0.0.0.0   # expose on LAN
```

| Endpoint                   | Description                                         |
| -------------------------- | --------------------------------------------------- |
| `GET /health`              | Liveness check                                      |
| `GET /clips`               | List all clips (metadata from each `manifest.json`) |
| `GET /clips/{id}/stream`   | Stream the MP4 (HTTP range → seeking works)         |
| `GET /clips/{id}/download` | Download the clip as an attachment                  |
| `DELETE /clips/{id}`       | Delete a clip + its manifest                        |
| `GET /live`                | List cameras available for live viewing             |
| `GET /live/{name}/stream`  | Live MJPEG stream (browser-playable via `<img>`)    |

**Auth:** set `"api_token"` in `config.json` to require a bearer token on every
request. Leave it empty (`""`) for an open API — fine when bound to localhost only.

### Windows desktop notifications (optional)

Get a toast when motion is recorded. In `config.json` set
`"notifications_enabled": true` (and `pip install winotify`). A notification
fires at most once a minute to avoid spam.

### Run automatically in the background (Windows)

Uses **Windows Task Scheduler** (built in — no extra software). Records 24/7
automatically at startup/login:

```powershell
.\scripts\install-service.ps1               # install + start
.\scripts\install-service.ps1 -Status       # check status
.\scripts\install-service.ps1 -Uninstall    # stop + remove
```

## 📼 Record a clip

```powershell
.\Capture-Stream.ps1 `
    -RtspUrl "rtsp://<user>:<password>@<ip>:554/live/ch0" `
    -Duration 30 `
    -IncludeAudio $true      # adds AAC audio (default: video only)
```

Files are written to `.\recordings\cam_<timestamp>.mp4`.

## 🚀 Quick start

**Watch the live stream in VLC**

```powershell
cd "D:\coding projects\cam720"
.\scripts\open-in-vlc.ps1
```

Or paste this directly into VLC (Media → Open Network Stream):

```
rtsp://<user>:<password>@<ip>:554/live/ch0
```

> The camera's SDP advertises `Content-Base: .../ch0/`, but the **DESCRIBE-ready** path is `/live/ch0` (a bare `/ch0/` gets `461 Unsupported Transport`). Use `/live/ch0`.

**Python live viewer** (with snapshot + FPS overlay)

```powershell
pip install -r requirements.txt
python src/cam_viewer.py
```

**Health check**

```powershell
.\scripts\check-camera.ps1
```

**Explore the RTSP auth flow yourself**

```powershell
python src/rtsp_digest_probe.py
```

## ⚠️ Notes

- This is a **local-LAN** hobby project. The camera's web UI and RTSP use **plain HTTP / MD5 digest** — don't expose them to the internet, and don't reuse a valuable password.
- The camera's SoC **rate-limits** after bursts of requests — if something hangs, wait 2–3 minutes.
- Cloud app account (email + password) ≠ local device password. The web UI / RTSP use the **device** password in `config.json`.

## 🔒 Privacy

`config.json` holds your camera password and is git-ignored — if you ever push this repo, the example config (with placeholder) is what travels.
