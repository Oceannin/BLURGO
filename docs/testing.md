# Runtime testing

[Documentation](README.md) · [Development](development.md)

Run against a disposable OBS profile or a backed-up test scene collection. Python 3.10+ and the pinned QA dependencies are required. Commands below run from the repository root.


The runtime harness exercises real OBS rendering, filter settings, source and scene workflows, transparency, filter reorder/removal, resize, scene switching, and restart persistence. Enable OBS WebSocket, then run:

```powershell
python -m pip install -r tools/requirements-qa.txt
python tools/obs-smoke.py run --output-dir artifacts/obs-smoke
```

Restart OBS normally and verify that the scene filter and its settings persisted:

```powershell
python tools/obs-smoke.py verify-persistence --output-dir artifacts/obs-smoke --report artifacts/obs-smoke/report.json
```

Use `--password` when OBS WebSocket authentication is enabled. The harness creates uniquely named QA scenes and leaves them in the test scene collection so restart persistence can be verified.

For controlled resolution and stability testing, use a disposable portable OBS profile:

```powershell
python tools/obs-smoke.py run --output-dir artifacts/obs-stress --width 1920 --height 1080 --fps 60 --set-video-settings --stress-seconds 1800
```

`--set-video-settings` changes the active OBS profile's canvas/output settings. `--test-display-capture` additionally attempts all modes on the first available monitor. `--test-window-capture "Title fragment"` selects a matching window through OBS and attempts all modes on that source. On Windows, `--test-game-capture "Game title fragment"` selects OBS Game Capture's matching specific-window target, waits for the hook, exercises every BlurGo mode, and records baseline/per-mode OBS Stats. Capture checks keep only numeric/hash results and delete the temporary private screenshots before exit. Add `--require-requested-captures` when a skipped, unmatched, or black-frame result must fail the run. Do not use these options in a production scene collection.

For optional post-alpha Game Capture qualification, start an authorized game in windowed or borderless mode, use a disposable OBS scene collection, and run:

```powershell
python tools/obs-smoke.py run --output-dir artifacts/game-capture-qa --test-game-capture "Game title fragment" --game-capture-wait-seconds 30 --require-requested-captures
```

Keep the OBS preview visible during the per-mode measurements for manual visual confirmation. The report deliberately does not retain the matched title, executable, or screenshots.

For an isolated Windows Window Capture run, stage BlurGo in a disposable portable OBS copy, enable obs-websocket in that copy, and run `tools/run-windows-window-smoke.ps1`. The runner launches the deterministic target from `tools/show-window-capture-target.ps1`, invokes the harness with required-capture enforcement, records the OBS log, and closes only the two processes it created.


## Sharing results

Commit concise, redacted findings with versions, settings, limitations, and relevant commit/package hashes. Keep raw OBS logs, generated reports, recordings, local paths, WebSocket passwords, and exported profiles in ignored `artifacts/` or `.local/`. Inspect screenshots before sharing; use generated patterns for public examples. See [documentation policy](README.md#what-belongs-in-git).
