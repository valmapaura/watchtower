# 🧪 Watchtower — Testing

We use **pytest**. Tests are a first‑class part of every phase, not an afterthought.

## Setup

```bash
pip install pytest
```

Run the fast suite (no camera, no network):

```bash
pytest -m "not hardware"
```

Run everything (including live‑camera tests):

```bash
pytest
```

## Layout

```
tests/
├── conftest.py              # shared fixtures (fake clock, temp dirs, fake frames)
├── unit/
│   ├── test_ringbuffer.py   # pre-buffer / roll logic
│   ├── test_detector.py     # motion detection on synthetic frames
│   ├── test_clipnames.py    # timestamp/segment naming
│   └── test_config.py       # config loading & validation
├── integration/
│   ├── test_recorder.py     # recorder -> LocalDisk writes a real file
│   └── test_storage.py      # LocalDisk save/list/get/delete against tmp dir
└── hardware/
    └── test_capture.py      # @pytest.mark.hardware — real RTSP camera
```

## Principles

1. **Fast & deterministic.** Most tests need no camera, no network, no real clock.
   Inject fakes (`FakeClock`, `FakeDetector`, temp dirs) instead of sleeping.
2. **Hardware tests opt‑in.** Anything touching the live camera is marked
   `@pytest.mark.hardware` so CI / daily runs skip it by default.
3. **Interface‑level tests for storage.** Define the `StorageBackend` contract once and
   test every backend against it — a fake backend and `LocalDisk` both pass the same tests.
4. **Synthetic fixtures.** Motion tests use procedurally generated frames (a moving box on a
   static background), so results are reproducible without a camera.

## Adding a new module?

Create `tests/<area>/test_<module>.py` alongside it. If it talks to the outside world
(network, disk, camera), abstract the boundary so the unit test can use a fake.
