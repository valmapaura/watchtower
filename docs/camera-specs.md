# cam720 — Camera Specs & Discovery Notes

Everything we learned about the camera that appeared on the LAN. Use this as the single source of truth for the hardware and firmware facts.

---

## 🏷️ Quick facts

| Item                         | Value                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------- |
| **IP address**               | `192.168.1.247` (DHCP on `192.168.1.0/24`)                                      |
| **MAC address**              | `F4-E2-5D-48-D1-FB`                                                             |
| **OUI vendor**               | **AltoBeam Inc.** — B808, Tsinghua Tongfang Hi-Tech Plaza, Haidian, Beijing, CN |
| **Firmware family**          | **APCam** — generic WiFi IP-camera platform (sold under many cheap brands)      |
| **Cloud backend**            | **QACloud** — `policy.qacloud.com.cn` (mobile app pairing via QR code)          |
| **Web UI**                   | `http://192.168.1.247` → login at `/home.htm`                                   |
| **Admin panel**              | `http://192.168.1.247/apcam/index.asp` (frameset)                               |
| **Local device credentials** | `admin` / password set during setup → see `config.json`                         |
| **Live stream**              | `rtsp://<user>:<pass>@192.168.1.247:554/live/ch0`                               |

---

## 🌐 Network

# Camera Specifications

This document outlines the specifications, configuration, and future roadmap for the **CAM720** camera system. It covers the hardware, network, RTSP stream, configuration file, file structure, and a proposed motion‑recording feature that captures short clips around detected movement.

## Hardware Overview

The CAM720 camera is a high‑definition, network‑enabled device designed for continuous video monitoring. It supports the following key features:

- **Resolution**: 1920×1080 (Full HD)
- **Frame Rate**: 30 fps (configurable up to 60 fps)
- **Video Codec**: H.264 (compressed) and H.265 (optional)
- **Audio**: Mono, 16‑bit, 48 kHz
- **Connectivity**: Ethernet (RJ‑45), Wi‑Fi (802.11b/g/n)
- **Power**: 12 V DC, 2 A
- **Storage**: Supports external SD card up to 128 GB

## Network Configuration

The camera can be accessed over the local network via its IP address. The following ports are used:

| Port | Service        |
| ---- | -------------- |
| 80   | HTTP Web UI    |
| 443  | HTTPS Web UI   |
| 554  | RTSP stream    |
| 8899 | Camera SDK API |

## RTSP Stream

The RTSP stream URL follows the pattern:

```
rtsp://<username>:<password>@<ip_address>:<port>/<path>
```

For example:

```
rtsp://admin:password@192.168.1.100:554/live/ch0
```

## Configuration File

The `config.json` file contains the camera credentials and connection details. It is used by the Python scripts and the viewer application.

```json
{
  "camera": {
    "name": "cam720",
    "host": "192.168.1.247",
    "web_port": 80,
    "rtsp_port": 554,
    "username": "admin",
    "password": "<YOUR_PASSWORD>",
    "rtsp_path": "/live/ch0"
  }
}
```

### 📹 Capturing the RTSP stream

The bundled **ffmpeg** binary can be used to pull the live stream and write it to a file on disk. The following PowerShell helper script makes this a one‑liner:

```powershell
# Capture-Stream.ps1 – Record an RTSP stream to an MP4 file
# Usage:
#   .\Capture-Stream.ps1 -RtspUrl <url> -Duration 30 -OutputDir .\recordings
```

**Parameters**

| Parameter    | Description                                                                 |
| ------------ | --------------------------------------------------------------------------- |
| `-RtspUrl`   | Full RTSP URL (including credentials).                                      |
| `-Duration`  | Number of seconds to record (default 30).                                   |
| `-OutputDir` | Directory where the resulting file will be stored (default `.\recordings`). |

The script resolves the bundled `ffmpeg.exe` (located under `installation\CAM720VmsTools\ffmpegExe\ffmpeg.exe`), creates the output folder if needed, and runs:

```bash
# Video is always copied (no re‑encoding). Audio handling depends on the `-IncludeAudio` flag:
#   • Without audio (default) → `-an`
#   • With audio (`-IncludeAudio $true`) → `-c:a aac -b:a 128k`
ffmpeg -i "<RtspUrl>" -t <Duration> -c:v copy \
   $(if ($IncludeAudio) { "-c:a aac -b:a 128k" } else { "-an" }) \
   "<OutputDir>\cam_<timestamp>.mp4"
```

- `-c:v copy` tells ffmpeg to **remux** the incoming H.264/H.265 video stream without re‑encoding, preserving quality and using minimal CPU.
- When `-IncludeAudio $true` is supplied, the script re‑encodes the original PCM ALAW audio to AAC (`-c:a aac -b:a 128k`), which is compatible with the MP4 container.
- The output filename contains a timestamp (`yyyyMMdd_HHmmss`) so multiple recordings can be collected sequentially.

#### Example

```powershell
.\Capture-Stream.ps1 \
   -RtspUrl "rtsp://<user>:<password>@192.168.1.247:554/live/ch0" \
   -Duration 60 \
   -OutputDir ".\recordings"
```

After the command finishes you will find a file such as `cam_20260829_143210.mp4` in the `recordings` folder. The file can be played with any standard media player (VLC, Windows Media Player, etc.).

#### Notes & Tips

- **Long‑running recordings** – omit `-t` (or set a very large value) to record indefinitely until you stop the script (Ctrl‑C). This is useful for continuous monitoring.
- **Segmented files** – ffmpeg supports segmenting (`-f segment -segment_time 300`) to automatically split a long capture into 5‑minute chunks.
- **Storage considerations** – at ~5 Mbps a 1‑hour recording consumes ~2.25 GB. Ensure sufficient disk space or rotate old files.
- **Automation** – the script can be called from a scheduled task or from the Python motion‑recorder daemon to store clips when motion is detected.

---

With this helper in place you can now **capture** and **store** video streams from the CAM720 for later analysis, archiving, or upload to cloud storage.

## File Structure

```
├── config.example.json
├── config.json
├── README.md
├── requirements.txt
├── docs/
│   ├── access-guide.md
│   ├── camera-177.md
│   └── camera-specs.md
├── installation/
│   └── CAM720VmsTools/
│       ├── CAM720VmsTools.url
│       ├── vmsTools.ini
│       ├── VmsToolsLicence.txt
│       ├── appConfigure/
│       │   ├── CardVideoDownLoad/
│       │   ├── DeviceMessage/
│       │   └── PreviewCache/
│       ├── audio/
│       ├── bearer/
│       ├── Certificat/
│       │   ├── Jooan/
│       │   └── Leovo/
│       ├── excel/
│       │   └── citys.csv
│       ├── ffmpegExe/
│       ├── font/
│       │   ├── msyh.ttc
│       │   ├── msyhbd.ttc
│       │   └── msyhl.ttc
│       ├── iconengines/
│       ├── imageformats/
│       ├── log/
│       │   └── logFile
│       ├── MediaFile/
│       │   ├── CardVideo/
│       │   ├── CloudPictureCache/
│       │   ├── CloudVideo/
│       │   ├── MsgWranPicture/
│       │   ├── Picture/
│       │   ├── TS/
│       │   └── Video/
│       ├── mediaservice/
│       ├── platforminputcontexts/
│       ├── platforms/
│       ├── playlistformats/
│       ├── plugins/
│       │   └── sqldrivers/
│       ├── position/
│       ├── printsupport/
│       ├── qmltooling/
│       ├── Qt/
│       │   ├── labs/
│       │   └── test/
│       ├── QtGraphicalEffects/
│       │   ├── Blend.qml
│       │   ├── BrightnessContrast.qml
│       │   ├── Colorize.qml
│       │   ├── ColorOverlay.qml
│       │   ├── ConicalGradient.qml
│       │   ├── Desaturate.qml
│       │   ├── DirectionalBlur.qml
│       │   ├── Displace.qml
│       │   ├── DropShadow.qml
│       │   ├── FastBlur.qml
│       │   ├── GammaAdjust.qml
│       │   ├── GaussianBlur.qml
│       │   ├── Glow.qml
│       │   ├── HueSaturation.qml
│       │   ├── InnerShadow.qml
│       │   ├── LevelAdjust.qml
│       │   ├── LinearGradient.qml
│       │   ├── MaskedBlur.qml
│       │   ├── OpacityMask.qml
│       │   ├── plugins.qmltypes
│       │   ├── qmldir
│       │   ├── RadialBlur.qml
│       │   ├── RadialGradient.qml
│       │   ├── RectangularGlow.qml
│       │   ├── RecursiveBlur.qml
│       │   ├── ThresholdMask.qml
│       │   └── ZoomBlur.qml
│       │   └── private/
│       ├── QtMultimedia/
│       │   ├── plugins.qmltypes
│       │   ├── qmldir
│       │   └── Video.qml
│       ├── QtQml/
│       │   ├── plugins.qmltypes
│       │   ├── qmldir
│       │   ├── Models.2/
│       │   ├── RemoteObjects/
│       │   ├── StateMachine/
│       │   └── WorkerScript.2/
│       ├── QtQuick/
│       │   ├── Controls/
│       │   ├── Controls.2/
│       │   ├── Dialogs/
│       │   ├── Extras/
│       │   ├── Layouts/
│       │   ├── PrivateWidgets/
│       │   ├── Templates.2/
│       │   └── Window.2/
│       ├── QtQuick.2/
│       │   ├── plugins.qmltypes
│       │   └── qmldir
│       ├── QtTest/
│       │   ├── plugins.qmltypes
│       │   ├── qmldir
│       │   ├── SignalSpy.qml
│       │   ├── TestCase.qml
│       │   └── testlogger.js
│       ├── QtWebChannel/
│       │   ├── plugins.qmltypes
│       │   └── qmldir
│       ├── QtWebEngine/
│       ├── QtWebSockets/
│       ├── QtWebView/
│       ├── QtWinExtras/
│       ├── resources/
│       ├── scenegraph/
│       ├── styles/
│       ├── translations/
│       ├── update/
│       ├── virtualkeyboard/
│       ├── webview/
│       └── XQSdkLog/
├── scripts/
│   ├── check-camera.ps1
│   └── open-in-vlc.ps1
├── src/
│   ├── cam_viewer.py
│   └── rtsp_digest_probe.py
```

## Usage

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the viewer**:

   ```bash
   python src/cam_viewer.py
   ```

3. **Check camera health**:

   ```powershell
   ./scripts/check-camera.ps1
   ```

4. **Open in VLC**:
   ```powershell
   ./scripts/open-in-vlc.ps1
   ```

## Motion‑Recording Feature (Proposed)

### Goal

Record a short clip that starts **30 seconds before** detected movement and ends **5 seconds after** the movement stops. The clip is then uploaded to a cloud folder (e.g., Google Drive) and all other frames are discarded.

### High‑level Architecture

```
Camera RTSP stream → FFmpeg (or OpenCV) → Ring‑buffer (30 s) → Motion detector
   │
   └─► When motion starts → Start writing to output file
   │
   └─► When motion stops → Stop writing after 5 s
   │
   └─► Upload clip to Google Drive via Drive API
   │
   └─► Delete local clip (optional)
```

### Implementation Options

| Language               | Pros                                                                                   | Cons                                                                                                 | Typical Use‑case                                                               |
| ---------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Python**             | Rapid prototyping, rich libraries (OpenCV, ffmpeg‑python, google‑apiclient).           | GIL limits CPU‑bound performance; not ideal for long‑running 24/7 service on low‑power hardware.     | Prototype, small‑scale deployment, integration with existing Python scripts.   |
| **Go**                 | Compiled, lightweight binaries, excellent concurrency, good for long‑running services. | Requires more boilerplate; fewer high‑level media libraries (but `gocv` exists).                     | Production daemon on a Raspberry Pi or small server.                           |
| **Rust**               | Zero‑cost abstractions, high performance, strong safety guarantees.                    | Steeper learning curve; ecosystem for media handling is maturing.                                    | High‑performance, low‑resource deployment.                                     |
| **TypeScript/Node.js** | Easy to build web UI, Firebase integration, npm ecosystem.                             | Single‑threaded event loop; not ideal for heavy video processing unless offloaded to native modules. | UI/UX layer, serverless functions for upload, orchestrating a separate worker. |

### Why Python is a good starting point

- The existing repo already contains Python scripts (`cam_viewer.py`).
- OpenCV and `ffmpeg-python` provide quick access to motion detection and encoding.
- The Google Drive API has a well‑documented Python client.
- You can prototype the 30‑s ring buffer logic in < 200 lines.

### When to move to a lower‑level language

- If the 24/7 service must run on a very low‑power device (e.g., Raspberry Pi 3) and you hit CPU or memory limits.
- If you need deterministic latency for real‑time alerts.
- If you plan to bundle the binary into a Docker image for a cloud VM and want a smaller footprint.

### TypeScript / Firebase Path

- **UI**: Build a simple React/Next.js app hosted on Firebase Hosting. Users log in via Firebase Auth.
- **Backend**: Deploy a Cloud Function (Node.js) that triggers on a new clip in a Cloud Storage bucket. The function can call the Drive API or move the file to a Drive folder.
- **Worker**: Keep the motion‑recording daemon in Python (or Go) running on a small VM or local machine. It writes clips to a shared folder that the Cloud Function watches.
- **Storage**: Use Google Drive or Cloud Storage. For a 5 GB budget, Cloud Storage is cheaper and easier to manage programmatically.

### Suggested Roadmap

1. **Prototype** (Python)
   - Implement the ring‑buffer + motion detector.
   - Test with a short clip and verify upload to Drive.
2. **Refactor** (optional)
   - Profile CPU/memory. If acceptable, keep Python.
   - If not, rewrite the core loop in Go or Rust.
3. **Integrate** with Firebase
   - Build a minimal UI that shows the last clip and allows manual upload.
   - Use Firebase Auth for user login.
4. **Deploy** 24/7
   - Run the daemon on a small VM or local machine.
   - Use a systemd service or Docker container.
5. **Monitoring & Alerts** (optional)
   - Send a Slack or email notification when a clip is captured.
   - Store metadata in Firestore for quick search.

## Storage Considerations

- **Clip size**: 30 s of 1080p H.264 at ~5 Mbps ≈ 18 MB.
- **Daily quota**: 5 GB ≈ 280 clips per day.
- **Retention**: Keep only the last 30 days in Drive; delete older clips automatically.

## Next Steps

1. Create a new branch `motion‑recording`.
2. Add a `motion_recorder.py` script under `src/`.
3. Add a `requirements.txt` entry for `opencv-python`, `ffmpeg-python`, and `google-api-python-client`.
4. Write unit tests for the ring‑buffer logic.
5. Commit and open a PR for review.

## License

This project is licensed under the MIT License.
