# 📹 Camera 2 — 192.168.1.177 (Jooan / CamHi)

> The second camera. Unlike cam720 (camera 247), this one **joined the WiFi but never finished setup** — the firmware's application layer is stuck half-initialized. This file records the full diagnosis.

---

## 🏷️ Quick facts

| Item                | Value                                                                    |
| ------------------- | ------------------------------------------------------------------------ |
| **IP address**      | `192.168.1.177` (DHCP on `192.168.1.0/24`)                               |
| **MAC address**     | `5C-5C-75-DF-F1-FD`                                                      |
| **OUI vendor**      | **Shenzhen Jooan Technology Co., Ltd.** — Longhua District, Shenzhen, CN |
| **Platform family** | **Jooan / CamHi-style** (NOT the same as camera 247's APCam/QACloud)     |
| **Status**          | ⚠️ **Half-broken** — on WiFi, services not responding                    |
| **Setup**           | ❌ Never completed (app can't finish pairing)                            |

---

## ⚠️ Key insight: different platform than cam720

|               | Camera 247 (cam720)            | Camera 177 (this one)                         |
| ------------- | ------------------------------ | --------------------------------------------- |
| **MAC OUI**   | `F4-E2-5D` → AltoBeam Inc.     | `5C-5C-75` → Shenzhen Jooan                   |
| **Firmware**  | APCam (`/goform/*`, `/apcam/`) | Jooan / CamHi-style                           |
| **Cloud/app** | QACloud                        | **CamHi-branded app** (check the box/sticker) |
| **Working?**  | ✅ Fully                       | ❌ Not yet                                    |

> **If pairing 177 with the QACloud app** (the one used for cam720), it will **never work** — different cloud platform. The correct app is likely **CamHi** or whatever brand name is printed on the camera/box.

---

## 🔬 Diagnosis performed (2026-08-18)

### Network checks

| Check     | Result                                              |
| --------- | --------------------------------------------------- |
| Ping      | ✅ Alive (369ms — slowish for LAN, but up)          |
| DHCP      | ✅ Got `192.168.1.177` on the same subnet as the PC |
| ARP entry | ✅ `5c-5c-75-df-f1-fd`                              |

### Port scan

| Port        | State                           | Notes                      |
| ----------- | ------------------------------- | -------------------------- |
| 80 (HTTP)   | ⚠️ OPEN but **every page 404s** | web app not serving        |
| 443 (HTTPS) | ⚠️ OPEN, same behavior          |                            |
| 554 (RTSP)  | ⚠️ OPEN but **never responds**  | accepts TCP, no RTSP reply |
| 8899 (SDK)  | OPEN                            | proprietary SDK port       |

All other common ports closed: 21, 22, 23, 53, 81, 82, 8000, 8001, 8080, 8081, 8443, 9000, 10000, 34567, 34599, 6100, 2000, 37777.

### Web probes (all fail)

| Probe                                  | Result                              |
| -------------------------------------- | ----------------------------------- |
| `/` , `/index.asp` , `/index.html`     | 404                                 |
| `/home.htm` , `/login.htm` , `/web/`   | 404                                 |
| `/CamHi` , `/en/login.html`            | 404                                 |
| `/cgi-bin/`                            | 500 (Internal Server Error)         |
| `/cgi-bin/mjpg/video.cgi`              | 500                                 |
| `/goform/getVideoSettings` (APCam API) | ❌ timeout — **not** APCam firmware |
| `/cgi-bin/hi3510/param.cgi`            | ❌ timeout                          |
| RTSP `OPTIONS`                         | ❌ timeout (no reply)               |
| Port 8899 HTTP probe                   | ❌ timeout                          |

### Discovery / hotspot checks

| Check                                                           | Result                                                       |
| --------------------------------------------------------------- | ------------------------------------------------------------ |
| UDP broadcast discovery (CamHi 32108 / 34567, QACloud, generic) | ❌ no responses (Starlink router may not forward broadcasts) |
| WiFi scan for a setup hotspot (`IPCAM-*` / `CamHi-*` SSID)      | ❌ **none visible** — the camera is NOT in AP mode           |
| Router root (`192.168.1.1`, Starlink)                           | ✅ reachable — router is not blocking LAN traffic            |

---

## 🧠 Conclusion

> **The camera joined the WiFi network but its firmware never finished booting the application layer.**

Evidence:

- It has a valid IP and responds to ping (WiFi + TCP stack alive)
- TCP listeners are up (80/443/554/8899 accept connections)
- But every HTTP/RTSP/API request times out or 404s → the **application daemons are hung or crashed**
- No setup hotspot → the camera isn't in AP (setup) mode either

It's in a **limbo state** between "connected to WiFi" and "setup complete."

---

## 🔧 Recommended fixes (in order)

1. **Power-cycle** — unplug 30 seconds, replug, wait ~2 minutes, retry the app.
   - Clears a hung firmware; works surprisingly often on cheap boards.
2. **Factory reset** — hold the **pinhole reset button** (paperclip) for **10–15 seconds** until the camera beeps / LED blinks.
   - Wipes the half-baked config → camera boots fresh into **setup mode** (should broadcast its own hotspot like `IPCAM-*` / `CamHi-*`).
3. **Re-pair with the CORRECT app** — after reset, connect the phone to the camera's hotspot, open the **CamHi** (or brand) app, scan the QR code on the camera/box.
4. **Verify app match** — if the sticker says CamHi but pairing with QACloud, wrong app.

---

## 🗒️ Related

- cam720 (healthy camera 247): see [`camera-specs.md`](./camera-specs.md)
- Once camera 177 is fixed, we can document its stream URL and API here too.
