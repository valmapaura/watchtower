# 📷 cam720

> The cameras that showed up on the LAN one day — documented, reverse-engineered, and streamable.

A hobby project capturing **everything** we learned about the WiFi IP cameras on the network: full hardware/firmware specs, the login + RTSP auth internals we reverse-engineered, and a small toolbox to poke them from your PC.

> **🎯 Direction:** growing into a home, open‑source camera streaming service that records
> footage to a drive you own — local disk first, cloud later, with a browser client.
> See [`docs/PROJECT.md`](docs/PROJECT.md) (vision & principles) and
> [`docs/ROADMAP.md`](docs/ROADMAP.md) (phased plan).

## 📹 Cameras

| Camera     | IP              | MAC vendor    | Platform        | Status                                                                    |
| ---------- | --------------- | ------------- | --------------- | ------------------------------------------------------------------------- |
| **cam720** | `192.168.1.247` | AltoBeam Inc. | APCam / QACloud | ✅ Working — documented in [`docs/camera-specs.md`](docs/camera-specs.md) |

## 🧰 What's inside

```
cam720/
├── README.md                  ← you are here
├── config.json                ← your real credentials (git-ignored)
├── config.example.json        ← template with placeholders
├── requirements.txt           ← Python deps (opencv-python)
├── Capture-Stream.ps1         ← record the RTSP stream to MP4 (video + optional AAC audio)
├── Camera-Limit-Tester.ps1    ← test how many concurrent streams the camera handles
├── docs/
│   ├── PROJECT.md             ← vision, design principles, modular architecture
│   ├── ROADMAP.md             ← phased plan: local disk → cloud → browser UI → Android
│   ├── camera-specs.md        ← cam720 hardware/firmware/network facts
│   └── access-guide.md        ← how to log in, admin panel, RTSP, troubleshooting
├── scripts/
│   ├── check-camera.ps1       ← health check: ping, ports, RTSP server
│   └── open-in-vlc.ps1        ← opens the live stream in VLC
└── src/
    ├── cam_viewer.py          ← live RTSP viewer (OpenCV) with snapshots
    └── rtsp_digest_probe.py   ← pure-Python RTSP digest-auth explorer
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
