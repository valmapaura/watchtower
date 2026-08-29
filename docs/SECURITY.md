# 🔐 Watchtower — Security & Remote Access

How to keep your camera and recordings safe while still being able to check in
remotely. **Read this before exposing anything beyond your LAN.**

---

## 1. The threat model

The cameras Watchtower talks to are **cheap IP cameras** (APCam / CamHi-style). Two
hard realities:

1. They use **plain HTTP and MD5 digest auth** — weak by modern standards.
2. Cheap cameras often have **known firmware vulnerabilities** and are actively
   scanned by internet botnets looking for open cameras.

> **Rule #1: Never port-forward the camera's ports (80, 554, 8899) to the internet.**
> That single action is the most common way these cameras get compromised.

## 2. The key decisions

| Topic               | Recommended choice                          | Why                                                     |
| ------------------- | ------------------------------------------- | ------------------------------------------------------- |
| **Remote access**   | **VPN / mesh tunnel** (Tailscale, ZeroTier) | Encrypted, no open ports, camera stays off the internet |
| **Camera exposure** | **LAN-only**                                | Never open the camera to the public internet            |
| **Recordings**      | **Local disk you control**                  | Already the design — local-first                        |
| **Credentials**     | **Strong, unique password** + git-ignored   | Prevent reuse/leak                                      |
| **Web UI (future)** | **LAN-only or behind Tailscale**            | Same rule as the camera                                 |

## 3. Secure remote access with Tailscale (recommended)

Tailscale creates a private, encrypted tunnel between your devices. From anywhere,
your phone/laptop reaches the camera at its **LAN IP** as if you were home.

1. Install Tailscale on your **PC** and your **phone/laptop**.
2. Sign in to the same Tailscale account on both.
3. That's it — your devices are on a private mesh. Open VLC / the web UI using the
   camera's LAN IP (e.g. `192.168.1.247`) from anywhere.

**Why not port forwarding?** Port forwarding exposes the camera to the whole internet.
Tailscale exposes it only to _your_ devices, with modern encryption. Same convenience,
a fraction of the risk.

## 4. Camera password hygiene

- Use a **strong, unique** password for the camera — don't reuse one from another account.
- If a password has ever leaked (e.g. in a repo), **assume it's compromised** and change it.
- Never put the real password in a README, doc, chat, or the repo. Use placeholders:
  ```
  rtsp://<user>:<password>@<ip>:554/live/ch0
  ```

## 5. Watchtower hardening checklist

- [ ] `config.json` is git-ignored (it is) — never commit real credentials.
- [ ] Camera ports **not** forwarded on the router.
- [ ] Remote access via Tailscale (or VPN), **not** port forwarding.
- [ ] Strong, unique camera password.
- [ ] Recordings on a drive you control (local disk).
- [ ] Keep Watchtower's own service/web-UI LAN-only or behind Tailscale.

## 6. VLC playback (LAN)

To watch a live feed in VLC on the same network, use the placeholder form:

```
rtsp://<user>:<password>@<ip>:554/live/ch0
```

Or use the helper script (reads credentials from your local `config.json`):

```powershell
cd "D:\coding projects\cam720"
.\scripts\open-in-vlc.ps1
```

> The helper reads your password from the local (git-ignored) `config.json`, so it never
> appears in the repo or in docs.
