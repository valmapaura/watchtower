# 🗺️ cam720 — Roadmap

A phased plan from "captures video to a file" today, to a full home camera‑recording
service with a browser client. Each phase is **independently useful** and delivers
something runnable.

> Current status (Phase 0): ✅ capture‑to‑file works, including audio.

---

## 🧭 Where we are

| Capability          | Status      | Notes                                    |
| ------------------- | ----------- | ---------------------------------------- |
| RTSP stream capture | ✅ Works    | `Capture-Stream.ps1` (video + AAC audio) |
| Concurrent streams  | ✅ Verified | 4 streams OK (`Camera-Limit-Tester.ps1`) |
| Live viewer         | ✅ Works    | `src/cam_viewer.py` (OpenCV)             |
| Health check        | ✅ Works    | `scripts/check-camera.ps1`               |
| Motion recording    | ❌          | Next big milestone                       |
| Storage abstraction | ❌          | Planned (local → cloud)                  |
| Browser UI          | ❌          | Planned (later phase)                    |

---

## Phase 0 — Foundation (done)

- [x] RTSP capture with optional audio.
- [x] Concurrent‑stream limit testing.
- [x] Health‑check script.
- [x] Secure git hygiene (credentials ignored/redacted).

## Phase 1 — Local disk recorder (Windows first) ⭐ next

Goal: a **daemon/service** that records to a local folder, motion‑gated.

- [ ] `motion_recorder` (Python) that continuously buffers the stream.
- [ ] **Pre‑buffer 30 s** before motion (circular buffer in RAM, then flushed to disk).
- [ ] **Post‑roll 5 s** after motion stops (keep recording briefly).
- [ ] Motion detection = simple frame‑diff / pixel‑change (OpenCV), modular interface.
- [ ] Segment clips into timestamped files under `recordings/<date>/`.
- [ ] Retention policy (e.g. keep last N days, auto‑delete old clips).
- [ ] Run as a background service on Windows (Task Scheduler / NSSM / `pywin32` service).
- [ ] Config: motion sensitivity, buffer seconds, output dir, per‑camera entries.

**Exit criteria:** leave it running; it writes a handful of motion clips/day, playable in VLC.

## Phase 2 — Storage abstraction

Goal: decouple "where footage goes" from "how footage is captured".

- [ ] Define a small `StorageBackend` interface:
      `save(clip)`, `list()`, `get(path)`, `delete(path)`.
- [ ] Implement `LocalDiskBackend` (Windows paths first).
- [ ] Add `manifest.json` per clip (timestamp, camera, motion score) for future indexing.
- [ ] Design for future backends (Google Drive, Firebase/Cloud Storage, S3, NAS) — no code yet.

## Phase 3 — Cloud sync (optional add‑on)

Goal: mirror local footage to the cloud, **still keeping local as source of truth**.

- [ ] `SyncBackend` that uploads new clips to Google Drive / Firebase Storage.
- [ ] Upload‑then‑delete or upload‑and‑keep (config).
- [ ] Resume/retry on network loss; don't block the recorder.
- [ ] Auth via a local token file (never committed), OAuth where available.

## Phase 4 — Browser UI

Goal: watch and export clips from any browser. _Simple and uncomplicated._

- [ ] Lightweight web server (FastAPI/Flask) serving `GET /clips` (list) and `GET /clips/{id}/stream` (video).
- [ ] Minimal SPA: grid of clips, click to play, download/delete buttons, filter by date/camera.
- [ ] Serve video efficiently (HTTP range requests so MP4 seeking works).
- [ ] Optional live thumbnail view of cameras.

## Phase 5 — Portability (Android & beyond)

Goal: same codebase, different platforms.

- [ ] Move capture to a cross‑platform engine or keep ffmpeg as subprocess.
- [ ] Implement `LocalDiskBackend` for Android storage (scoped storage / media store).
- [ ] Package as an app or a headless service; reuse the same config + modules.

---

## 🧩 Proposed architecture (modular)

```
                    ┌────────────────────────────────────────────┐
 camera (RTSP) ──►  │  capture / reader                          │
                    └──────────────┬─────────────────────────────┘
                                   │ frames
                    ┌──────────────▼─────────────┐
                    │ detector (motion)          │   <- swappable
                    └──────────────┬─────────────┘
                                   │ "motion!" / "idle"
                    ┌──────────────▼─────────────┐
                    │ recorder (pre/post buffer) │
                    └──────────────┬─────────────┘
                                   │ clip bytes
                    ┌──────────────▼─────────────┐
                    │ storage backend            │   <- LocalDisk / GoogleDrive / Firebase
                    └──────────────┬─────────────┘
                                   │
                              recordings/<date>/
```

Key idea: **each box is a module with a stable interface.** To add cloud, you add a new
`StorageBackend`. To add ML motion, you swap the `detector`. Nothing else changes.

---

## 💡 Suggested features (future / optional)

| Feature                      | Value                               | Effort |
| ---------------------------- | ----------------------------------- | ------ |
| **Motion sensitivity zones** | Ignore noisy regions (trees/road)   | Med    |
| **Email/notification alert** | Push on motion via webhook          | Low    |
| **Multi‑camera support**     | One config, N cameras               | Med    |
| **Timeline scrubber**        | Jump to motion events on a time bar | Med    |
| **Snapshot on motion**       | Save a JPEG thumbnail per event     | Low    |
| **Night‑vision toggle**      | Expose camera IR / preset controls  | Low    |
| **Secure remote access**     | Tailscale / VPN / reverse proxy     | Low    |
| **Storage usage dashboard**  | How much disk is left, per day      | Low    |
| **Export/Share**             | Download a clip or batch            | Low    |
| **Object detection (later)** | Person/car detection (YOLO)         | High   |

---

## UI/UX direction (Phase 4, design in mind now)

- **Browser‑based** (no install), works on desktop + phone.
- Three views, keep it minimal:
  1. **Live** — current camera view(s).
  2. **Timeline** — recent clips as a scrollable list with a thumbnail + timestamp + motion indicator.
  3. **Settings** — cameras, motion sensitivity, retention, storage backend.
- **Principle:** 3 clicks or fewer to get from "I'm in the app" to "I'm watching a clip".
- Clean dark UI (cameras/surveillance fit it), big play targets, obvious download/delete.
- Video playback with native `<video>` + HTTP range requests — no heavy players needed.

## Milestone ordering (priority)

1. **Phase 1 recorder** (biggest value) — motion clips on disk.
2. **Phase 2 storage interface** (cheap, unlocks everything) — do this _with_ Phase 1.
3. **Phase 4 minimal browser UI** (watch what you recorded) — before cloud.
4. **Phase 3 cloud sync** (nice‑to‑have once local works).
5. **Phase 5 portability** (Android etc.) — last.

---

## 🧪 Testing strategy (pytest, baked into every phase)

Tests are **not an afterthought** — each phase ships with its own tests. We use **pytest**.

### Test levels

| Level             | What it covers                                   | Example                                       |
| ----------------- | ------------------------------------------------ | --------------------------------------------- |
| **Unit**          | A single function/class in isolation             | Ring‑buffer stores and drops frames correctly |
| **Integration**   | Modules working together                         | Recorder + LocalDisk writes a real file       |
| **Hardware/real** | Against the actual camera (tagged, run manually) | Capture 3 s from the live RTSP stream         |

### Key conventions

- `tests/` mirrors `src/`: `tests/test_ringbuffer.py`, `tests/test_storage.py`, etc.
- **No camera needed for most tests** — use a synthetic frame generator or a short local MP4 fixture.
- Real‑camera tests are marked `@pytest.mark.hardware` and excluded by default:
  `pytest -m "not hardware"`.
- Deterministic: avoid time.sleep(); inject a fake clock where timing matters.

### What each phase tests

- **Phase 1:** ring‑buffer correctness (pre‑buffer/roll), motion detector (on synthetic frames),
  clip segmentation, retention deletion, config loading.
- **Phase 2:** `StorageBackend` interface contract + a fake backend; LocalDisk `save/list/get/delete`
  against a temp dir.
- **Phase 3:** upload/retry logic with a fake network; auth‑file handling.
- **Phase 4:** HTTP endpoints (FastAPI `TestClient`), range‑request serving.
- **Phase 5:** platform adapter tests with mocks.
