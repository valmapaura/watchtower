# cam720 — Camera Specs & Discovery Notes

Everything we learned about the camera that appeared on the LAN. Use this as the single source of truth for the hardware and firmware facts.

---

## 🏷️ Quick facts

| Item | Value |
|---|---|
| **IP address** | `192.168.1.247` (DHCP on `192.168.1.0/24`) |
| **MAC address** | `F4-E2-5D-48-D1-FB` |
| **OUI vendor** | **AltoBeam Inc.** — B808, Tsinghua Tongfang Hi-Tech Plaza, Haidian, Beijing, CN |
| **Firmware family** | **APCam** — generic WiFi IP-camera platform (sold under many cheap brands) |
| **Cloud backend** | **QACloud** — `policy.qacloud.com.cn` (mobile app pairing via QR code) |
| **Web UI** | `http://192.168.1.247` → login at `/home.htm` |
| **Admin panel** | `http://192.168.1.247/apcam/index.asp` (frameset) |
| **Local device credentials** | `admin` / password set during setup → see `config.json` |
| **Live stream** | `rtsp://<user>:<pass>@192.168.1.247:554/live/ch0` |

---

## 🌐 Network

- Camera sits on the **same LAN** as the PC: `192.168.1.0/24`, gateway `192.168.1.1`.
- The `172.16.0.2 / 255.255.255.255` interface on the PC is **Cloudflare WARP** (a virtual tunnel adapter, no gateway, `/32` is normal for tunnels) — **unrelated** to the camera.

## 🚪 Open ports

| Port | Service | Notes |
|---|---|---|
| **80** | Web UI (HTTP) | login page, admin panel |
| **443** | Web UI (HTTPS) | same app, still plain-HTTP auth under the hood |
| **554** | **RTSP** | live video/audio streaming |
| **8899** | Camera SDK port | proprietary (used by phone apps / desktop tools) |

Closed: 21 (FTP), 22 (SSH), 23 (Telnet), 53, 8000, 8080, 8443, 37777.

---

## 🔐 Web login internals (reverse-engineered)

1. Login page: `GET /home.htm` — requires ticking the "I agree" policy checkbox.
2. Auth request (from `js/login.js`):

   ```
   GET /goform/getVideoSettings?userid=<username>&userkey=<md5(password)>
   ```

3. **Success** = response is JSON that contains an `fps` field.
   **Failure** = response JSON without `fps` → page shows `alert("failed")`.
4. On success the firmware sets cookies (used for the admin session):

   | Cookie | Value |
   |---|---|
   | `userid` | username |
   | `userkey` | `md5(password)` (lowercase hex) |
   | `policy` | `1` |
   | `loginflag_<hostname>` | `1` |

> ⚠️ The password travels as **MD5 over plain HTTP** — fine on a trusted LAN, do NOT expose this camera to the internet.

## 🖥️ Admin panel map (`/apcam/index.asp`)

A frameset: left menu (`/apcam/left.asp`) + main content frame.

| Menu (Chinese) | English | Page |
|---|---|---|
| **升级** | Upgrade (firmware) | `/apcam/adm/upload_firmware.asp` |
| **用户** | Users (username/password + RTSP) | `/apcam/adm/users.asp` |
| **备份** | Backup (config) | `/apcam/adm/backup.asp` |
| **退出** | Logout | — |

### Users page (`/apcam/adm/users.asp`)

- Username: ≤ 31 bytes, **letters/digits only**
- Password: 8–31 bytes, **must contain letters AND digits**
- RTSP auth mode radio (`authchk`):

  | Value | Meaning |
  |---|---|
  | `0` | RTSP **off** |
  | `1` | RTSP on, **no auth** |
  | `2` | RTSP on, **Basic auth** |
  | `3` | RTSP on, **Digest auth** ← what we use |

- Save sends `GET /goform/getOtherSetttings?...&singleCMD=RtspConf&authset=<mode>&userset=<user>&keyset=<password>`
  - 🐛 Fun firmware quirk: the endpoint is spelled **`getOtherSetttings`** (three `t`'s) — that's how the firmware itself calls it.
- Current config reads back through the same endpoint with `singleCMD=RtspConf` (requires `userid` + `userkey`).

---

## 📡 RTSP details

| Property | Value |
|---|---|
| **Stream URL** | `rtsp://<user>:<pass>@192.168.1.247:554/live/ch0` (**DESCRIBE-ready**) |
| **SDP Content-Base** | `rtsp://192.168.1.247:554/ch0/` (advertised by camera; a bare `/ch0/` DESCRIBE returns `461 Unsupported Transport`) |
| **Auth** | **Digest**, `realm="ipc"`, **no qop** → `response = MD5(ha1:nonce:ha2)` |
| **Video** | H.264, **2304×1296 (3MP)**, 15 fps |
| **Audio** | PCMA (G.711 a-law), 8 kHz |
| **Server** | LIVE555 Media Server (embedded) |
| **Transport** | RTP over TCP (interleaved) works; UDP available |

Full RTSP methods supported: `OPTIONS, DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE, GET_PARAMETER, SET_PARAMETER`.

### Digest auth recipe (no-qop variant)

```
HA1 = MD5(user:realm:password)
HA2 = MD5(method:uri)
response = MD5(HA1:nonce:HA2)
```

`realm="ipc"` for this camera. See `src/rtsp_digest_probe.py` for a working example.

---

## 🐢 Known behavior

- The SoC **rate-limits** after a burst of requests (web + RTSP). Symptoms: requests hang/time out, then recover after ~2–3 minutes of silence. Be patient — single gentle requests are fine.
- The camera supports **firmware upgrade** through the web UI (untested, risky — don't).

---

## ☁️ Cloud / app notes

- Paired via a QACloud-based mobile app (QR code on the device). The **app account (email + password) is separate** from the **local device password** used by the web UI and RTSP.
- Some brands on this platform: iCSee-style apps under various names. The camera's chipset is **AltoBeam**.
