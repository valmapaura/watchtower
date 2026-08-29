# cam720 — Access Guide

Step-by-step walkthrough: logging in, the admin panel, watching the stream, and troubleshooting.

---

## 1. Logging in to the web UI

1. Open `http://192.168.1.247` in a browser.
2. Tick the **"I Agree"** policy checkbox (login is blocked until you do).
3. Enter:
   - **Username:** `admin`
   - **Password:** *(the device password you set — stored in `config.json`)*
4. Click **Login** → you land on the admin panel (`/apcam/index.asp`).

> The login button shows a generic `alert("failed")` for wrong passwords. There is no lockout warning, but the camera **rate-limits** after many attempts — don't brute-force it.

## 2. Admin panel tour

The panel is a frameset with a left menu (Chinese labels):

| Menu | What it does |
|---|---|
| **升级** (Upgrade) | Firmware upload — **avoid unless you know what you're doing** |
| **用户** (Users) | Change username/password + configure **RTSP** |
| **备份** (Backup) | Backup/restore config |
| **退出** (Logout) | End session |

### Change password or RTSP mode (用户 page)

1. Click **用户** in the left menu.
2. Username + password fields (password must be **8–31 chars, letters AND digits**).
3. Pick the **RTSP 摘要认证 (Digest auth)** radio for the most secure local streaming.
4. Click **保存 (Save)** — success is silent (no error alert).

## 3. Watching the live stream

### VLC (recommended, easiest)

```
Media → Open Network Stream
rtsp://admin:<password>@192.168.1.247:554/live/ch0
```

Or just run the helper:

```powershell
.\scripts\open-in-vlc.ps1
```

VLC handles the digest auth automatically.

> Path note: the camera's SDP advertises `Content-Base: .../ch0/`, but the only path that answers `DESCRIBE` properly is `/live/ch0` (bare `/ch0/` → `461 Unsupported Transport`).

### Python viewer (snapshots + FPS)

```powershell
pip install -r requirements.txt
python src\cam_viewer.py
```

Keys: `q`/`ESC` quit · `s` save snapshot to `snapshots/`.

## 4. Under the hood (API cheat sheet)

| Purpose | Request |
|---|---|
| Verify credentials | `GET /goform/getVideoSettings?userid=<u>&userkey=<md5(pw)>` — success = JSON contains `fps` |
| Read RTSP config | `GET /goform/getOtherSetttings?userid=<u>&userkey=<md5(pw)>&singleCMD=RtspConf` |
| Save RTSP config | `GET /goform/getOtherSetttings?...&singleCMD=RtspConf&authset=<0-3>&userset=<u>&keyset=<pw>` |
| Stream (RTSP) | `rtsp://<u>:<pw>@192.168.1.247:554/live/ch0` — digest auth, `realm="ipc"`, no qop |

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Requests hang / time out | **Rate limit.** Wait 2–3 minutes, then try a single request. |
| Login says "failed" | Wrong password, or the policy checkbox wasn't ticked. |
| VLC shows black / can't connect | Camera rate-limiting, or RTSP auth mode is `0` (off) — check the 用户 page. |
| Stream auth rejected | RTSP auth mode must be 摘要认证 (digest, value `3`) for the credentials to work. |
| Can't reach the camera at all | Confirm you're on `192.168.1.0/24` (Cloudflare WARP doesn't affect LAN access). |

## 6. Security checklist

- [ ] Use a **unique password** for the camera (don't reuse email/banking passwords)
- [ ] Keep RTSP on **Digest auth** (not "no auth")
- [ ] Check your router for **UPnP** — many cheap cameras auto-open ports to the internet
- [ ] Don't expose ports 80/554/8899 to the internet (no port forwarding, no DMZ)
- [ ] The web UI sends passwords as **MD5 over plain HTTP** — local LAN only
