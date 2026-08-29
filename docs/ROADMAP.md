# 🗺️ Watchtower — Roadmap

A phased plan from "captures video to a file" today, to a full home camera‑recording
service with a browser client. Each phase is **independently useful** and delivers
something runnable.

> Current status (Phase 1): ✅ motion recorder built & tested (25 tests passing).

---

## 🧭 Where we are

| Capability          | Status      | Notes                                    |
| ------------------- | ----------- | ---------------------------------------- |
| RTSP stream capture | ✅ Works    | `Capture-Stream.ps1` (video + AAC audio) |
| Concurrent streams  | ✅ Verified | 4 streams OK (`Camera-Limit-Tester.ps1`) |
| Live viewer         | ✅ Works    | `src/cam_viewer.py` (OpenCV)             |
| Health check        | ✅ Works    | `scripts/check-camera.ps1`               |
| Motion recording    | ✅ Built    | `src/watchtower/` + 25 tests passing     |
| Storage abstraction | ✅ Built    | `LocalDiskBackend` + interface           |
| Browser UI          | ❌          | Planned (Phase 4)                        |

---

## Phase 0 — Foundation (done)

- [x] RTSP capture with optional audio.
- [x] Concurrent‑stream limit testing.
- [x] Health‑check script.
- [x] Secure git hygiene (credentials ignored/redacted).

## Phase 1 — Local disk recorder (Windows first) ✅ built

Goal: a **daemon/service** that records to a local folder, motion‑gated.

- [x] `motion_recorder` (Python) that continuously buffers the stream. (`src/watchtower/`)
- [x] **Pre‑buffer 30 s** before motion (time‑based buffer, flushed on motion).
- [x] **Post‑roll 5 s** after motion stops.
- [x] Motion detection = frame‑diff (OpenCV) behind a `MotionDetector` interface.
- [x] Clips written to MP4 and saved under `recordings/<camera>/<date>/`.
- [x] Config: motion sensitivity, pre/post buffer, min duration, per‑camera entries.
- [x] 35 unit + integration tests passing (see [`docs/TESTING.md`](TESTING.md)).
- [x] Retention policy — auto‑delete clips older than `retention_days` (0 = keep all).
- [x] Snapshot on motion — JPEG thumbnail per event (`snapshot_on_motion`).
- [x] Motion score — detector returns an intensity 0‑100, stored in each clip's `manifest.json`.
- [x] Windows background task — [`scripts/install-service.ps1`](../scripts/install-service.ps1)
      (Task Scheduler — built into Windows, no third-party software).
- [x] Windows local notifications — `winotify` toast on motion (`notifications_enabled`).

**Phase 1 is complete** 🎉

## Suggested fixes / follow-ups (documented)

- **Log rotation** — the scheduled task writes logs to the Task Scheduler history; for
  verbose app logs, redirect `python -m watchtower.main` output to a file and rotate it.
- **Motion score as a category** — expose `sensitivity` → threshold, and optionally record
  at different quality/skip based on the score (low motion = keep low-res).

## Phase 2 — Storage abstraction

Goal: decouple "where footage goes" from "how footage is captured".

- [x] Define a small `StorageBackend` interface:
      `save(clip)`, `list()`, `get(path)`, `delete(path)`.
- [x] Implement `LocalDiskBackend` (Windows paths first).
- [x] Add `manifest.json` per clip (timestamp, camera, motion score) for future indexing.
- [ ] Design for future backends (Google Drive, Firebase/Cloud Storage, S3, NAS) — no code yet.

## Phase 3 — Cloud sync (optional add‑on)

Goal: mirror local footage to the cloud, **still keeping local as source of truth**.

- [ ] `SyncBackend` that uploads new clips to Google Drive / Firebase Storage.
- [ ] Upload‑then‑delete or upload‑and‑keep (config).
- [ ] Resume/retry on network loss; don't block the recorder.
- [ ] Auth via a local token file (never committed), OAuth where available.

## Phase 4 — Browser UI

Goal: watch and export clips from any browser. _Simple and uncomplicated._

- [x] **API layer (prep)** — `src/watchtower/api.py` (FastAPI): `GET /clips`,
      `GET /clips/{id}/stream` (range requests), `GET /clips/{id}/download`,
      `DELETE /clips/{id}`, `GET /health`. 9 integration tests.
- [x] **Metadata listing** — `StorageBackend.list_metadata()` reads each clip's
      `manifest.json` so the UI can show thumbnails, timestamps, motion scores.
- [x] **Optional bearer auth** — `api_token` in config.json; empty = open (localhost).
- [ ] Minimal SPA: grid of clips, click to play, download/delete buttons, filter by date/camera.
- [ ] Serve video efficiently (HTTP range requests so MP4 seeking works) — API ready.
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
| **Motion detection level**   | Intensity 0‑100 per clip (built)    | Done   |

---

## 🔮 Future: object-type detection & categorized videos

Planned follow‑up (designed for, not yet built):

- **Swap the detector** for an object detector (e.g. YOLO / MediaPipe) implementing the same
  `MotionDetector` interface. No recorder changes needed — the modular design already allows it.
- **Categories per clip:** add a `category` field to `ClipMetadata`
  (e.g. `person`, `car`, `animal`, `unknown`).
- **Categorised storage:** `recordings/<camera>/<date>/<category>/` so videos are organised
  automatically by what triggered them.
- **Confidence/score:** reuse the existing `motion_score` field (or add `confidence`) so the UI
  can sort/filter by how strong a detection was.
- **Sensitivity per object:** e.g. only record when a _person_ is seen, ignore a swaying tree.

**Why this is easy now:** the detector, writer, and storage are all behind interfaces. Adding
object detection is "write a new detector + add one metadata field" — not a rewrite.

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
