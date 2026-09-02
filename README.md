# BlurGo for OBS

BlurGo is an open-source, GPU-accelerated blur filter for OBS Studio. Add the filter to one source, or add it to a scene to process the complete composited scene.

> Status: `0.1.0` alpha candidate. Windows/D3D11, Ubuntu/OpenGL, and Apple Silicon macOS/OpenGL source and nested-scene rendering have passed runtime smoke tests; production streams should keep a tested OBS scene collection backup until the complete release checklist is signed off.

## Features

- Gaussian blur with separable GPU passes.
- Box blur for a flatter, more uniform look.
- Pixelate mode with configurable block size.
- Adjustable radius, 1–4 quality passes, and 0–100% effect mix.
- Source and complete-scene workflows through the standard OBS filter stack.
- English and Russian UI.
- SDR, 16-bit sRGB, and extended Rec. 709 render-target handling.
- Fail-safe rendering: invalid dimensions or GPU resource failures bypass the filter.

## Requirements

- OBS Studio 31.1.1 or newer.
- A graphics backend supported by OBS Studio.
- Windows x64 is the primary alpha performance platform. Ubuntu 24.04 x86_64 and Apple Silicon macOS have packaged-plugin runtime coverage; the macOS package is Universal.

## Install a release

1. Download the package for your operating system from the GitHub Releases page.
2. Close OBS Studio.
3. Run the installer or extract the portable package into the matching OBS installation.
4. Start OBS and check **Help → Log Files → View Current Log** for a `BlurGo` load entry.

No public binary is published until the first alpha tag has passed the complete release checklist. Current QA evidence is recorded in the [Windows runtime report](docs/qa/0.1.0-windows-smoke.md), [Ubuntu runtime report](docs/qa/0.1.0-ubuntu-smoke.md), [macOS runtime report](docs/qa/0.1.0-macos-smoke.md), and [release gate status](docs/qa/0.1.0-gate-status.md). The remaining hardware checks use the [manual sign-off form](docs/qa/0.1.0-manual-signoff.md).

## Use BlurGo

### Blur one source

1. Right-click the source and choose **Filters**.
2. Under **Effect Filters**, select **+ → BlurGo**.
3. Choose Gaussian, Box, or Pixelate and tune the visible controls.

### Blur a complete scene

1. In **Sources**, add an existing scene as a **Scene** source inside a wrapper scene.
2. Add **BlurGo** to that nested scene source.
3. Use the wrapper scene for streaming or recording.

The wrapper-scene pattern avoids feedback and keeps the original scene reusable without blur.

## Build from source

The repository follows the official OBS plugin template and downloads the pinned OBS build dependencies during configuration.

### Windows x64

Prerequisites: Visual Studio 2022 with Desktop development with C++, Git, and CMake 3.30.5.

```powershell
cmake --preset windows-x64
cmake --build --preset windows-x64
ctest --test-dir build_x64 -C RelWithDebInfo --output-on-failure
```

### macOS Universal

Prerequisites: Xcode 16 and CMake 3.30.5.

```bash
cmake --preset macos
cmake --build --preset macos
ctest --test-dir build_macos -C RelWithDebInfo --output-on-failure
```

### Ubuntu 24.04 x86_64

Prerequisites: CMake 3.28.3, Ninja, pkg-config, and build-essential.

```bash
cmake --preset ubuntu-x86_64
cmake --build --preset ubuntu-x86_64
ctest --test-dir build_x86_64 --output-on-failure
```

Build output is staged under the preset's `rundir` directory and packaged by GitHub Actions.

## Reproduce the OBS runtime smoke test

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

For the release-candidate Game Capture check, start an authorized game in windowed or borderless mode, use a disposable OBS scene collection, and run:

```powershell
python tools/obs-smoke.py run --output-dir artifacts/game-capture-qa --test-game-capture "Game title fragment" --game-capture-wait-seconds 30 --require-requested-captures
```

Keep the OBS preview visible during the per-mode measurements for manual visual confirmation. The report deliberately does not retain the matched title, executable, or screenshots.

For an isolated Windows Window Capture run, stage BlurGo in a disposable portable OBS copy, enable obs-websocket in that copy, and run `tools/run-windows-window-smoke.ps1`. The runner launches the deterministic target from `tools/show-window-capture-target.ps1`, invokes the harness with required-capture enforcement, records the OBS log, and closes only the two processes it created.

## Project structure

```text
src/                         OBS module, filter lifecycle, and validated settings
data/                        GPU effects and translations
tests/                       Dependency-free settings tests
tools/                       Reproducible OBS runtime QA harness
docs/                        Architecture, product brief, decisions, and release QA
cmake/, build-aux/           Official OBS plugin-template build infrastructure
.github/                     Cross-platform build, format, package, and release workflows
```

## Performance guidance

GPU cost grows with source resolution and quality passes. The following are conservative starting points, not guarantees; validate them with OBS Stats on the actual scene and capture backend.

| GPU / workload | Starting point |
| --- | --- |
| Entry-level or integrated GPU, 1080p60 | Gaussian/Box radius 8-12, one pass; prefer Pixelate when it fits the look. |
| Mid-tier GPU, 1080p60-1440p60 | Gaussian radius 12, two passes. |
| High-tier GPU or 4K60 | Gaussian radius 12, two passes; reduce passes first if render time rises. |

Pixelate requires one processing pass regardless of the quality-pass control. Apply BlurGo to a lower-resolution nested scene when the source does not need full-canvas resolution. The published 0.1.0 Windows measurements were collected on an RTX 4070 Ti SUPER and are documented in [the Windows runtime QA report](docs/qa/0.1.0-windows-smoke.md). The [Ubuntu runtime report](docs/qa/0.1.0-ubuntu-smoke.md) and [macOS runtime report](docs/qa/0.1.0-macos-smoke.md) use software OpenGL for functional coverage and are not hardware-performance benchmarks.

## Troubleshooting

- **BlurGo is missing from the filter list:** confirm the plugin package matches the OBS architecture and inspect the OBS log for module-load errors.
- **The image is unchanged:** ensure Effect mix is above 0% and the filter is enabled.
- **GPU usage is high:** reduce Quality passes, apply the filter before expensive downstream filters, or blur a lower-resolution nested scene.
- **The whole scene is not blurred:** use the nested/wrapper-scene workflow above; OBS does not expose the active root scene itself as a normal filter target.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Please report security issues using the private process in [SECURITY.md](SECURITY.md), not a public issue.

## License

BlurGo is licensed under the GNU General Public License, version 2 or later. See [LICENSE](LICENSE).
