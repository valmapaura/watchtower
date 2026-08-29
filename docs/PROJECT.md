# � Watchtower — Project Vision & Principles

This is the _why_ and _how_ of the project. It guides every design decision. If a change
violates these principles, it's probably the wrong change.

---

## 1. Mission

> A **home, open‑source camera streaming service** that watches your IP cameras and
> **saves footage to a drive you own** — starting with your local hard disk and growing
> to cloud storage (Google Drive, Firebase, etc.).

It should be the camera‑recording equivalent of "self‑hosted but simple": set it up once,
forget it, and always be able to look back at what happened.

## 2. Core goals

| Goal                     | Meaning                                                               |
| ------------------------ | --------------------------------------------------------------------- |
| **Reliable capture**     | Motion‑triggered clips with a 30‑s pre‑buffer and 5‑s post‑roll.      |
| **Own your data**        | Footage is written to local disk first; cloud sync is an add‑on.      |
| **Private by default**   | Credentials stay local, never committed, never sent to third parties. |
| **Simple to run**        | One service, one config file, minimal moving parts.                   |
| **Good UX for the user** | A browser client to watch/export clips (implemented later).           |

## 3. Design principles

### 🧩 3.1 Modular — plug in / plug out

Features are **isolated modules** behind small, stable interfaces. You should be able to:

- Swap the **motion detector** (OpenCV → ML model) without touching the recorder.
- Swap the **storage backend** (Local Disk → Google Drive → Firebase) without touching capture.
- Remove **audio** or **cloud‑upload** entirely and everything else still works.

```
camera ──► capture ──► detector ──► recorder ──► storage (local/cloud)
                 ▲                                      │
                 └────────── status / events ───────────┘
```

### 🪶 3.2 Clean & uncomplicated

- One obvious way to do things, not ten.
- Config lives in **one file** with sane defaults.
- No framework dependencies where a plain module suffices.
- Failures are **logged clearly** and recover gracefully (the camera rate‑limits; we retry).

### 🔒 3.3 Private & secure

- Never hardcode credentials in code or docs.
- `config.json` is git‑ignored; the committed example uses placeholders.
- Streams stay on the trusted LAN by default; expose publicly only with explicit opt‑in.

### ♻️ 3.4 Portable by design

- Storage layer is **abstracted** so the same code runs on Windows today and Android later.
- Avoid OS‑specific assumptions in the core (keep platform code behind thin adapters).

## 4. What we are NOT doing (yet / deliberately)

- No cloud‑first storage. Local disk is the source of truth in Phase 1.
- No public internet exposure of the camera. Local‑LAN only.
- No complex ML / facial recognition in the first version — motion = pixel change.
- No mobile app yet. A **browser client** is the target UI.

## 5. How decisions are made

1. Does it keep footage on hardware the user controls? ✅ / ❌
2. Does it add a new way of doing something that already works? (avoid)
3. Is it more complex than it needs to be? (simplify)
4. Can it be removed without breaking the rest? (modular)

## 6. Language & tech stack (decided)

**Python end to end.** No C++.

The heavy lifting is already native C/C++ under the hood; Python orchestrates it:

| Layer    | Choice                                                | Why                                          |
| -------- | ----------------------------------------------------- | -------------------------------------------- |
| Language | **Python 3**                                          | Fast to iterate, readable, widely understood |
| Capture  | **ffmpeg** (bundled binary, as subprocess)            | Best-in-class RTSP + audio, already on hand  |
| Video IO | **OpenCV** (`cv2.VideoCapture`)                       | C++ core, simple Python API                  |
| Motion   | **OpenCV** frame‑diff / numpy                         | Simple, proven, swappable                    |
| Storage  | **fsspec** or a thin custom `StorageBackend`          | Plug‑in local/S3/Drive/Cloud                 |
| Config   | plain JSON (existing) + `pydantic` validation (later) | One file, sane defaults                      |
| Web UI   | **FastAPI** + small vanilla JS SPA                    | Lightweight, no framework weight             |
| Tests    | **pytest**                                            | Industry standard                            |

> **Note on Android (Phase 5):** Python doesn't run natively on Android. By that phase the core
> modules are stable enough that only the platform adapter (capture + storage) needs a narrow
> reimplementation — not the whole project.
