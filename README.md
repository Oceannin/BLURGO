# BlurGo for OBS

BlurGo is an open-source, GPU-accelerated blur filter for OBS Studio. Add the filter to one source, or add it to a scene to process the complete composited scene.

> Status: development build for `0.1.0`. The rendering core is ready for contributor testing; production streams should keep a tested OBS scene collection backup.

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
- Windows x64 is the primary alpha test platform. The project also carries the official OBS template presets for macOS Universal and Ubuntu 24.04 x86_64.

## Install a release

1. Download the package for your operating system from the GitHub Releases page.
2. Close OBS Studio.
3. Run the installer or extract the portable package into the matching OBS installation.
4. Start OBS and check **Help → Log Files → View Current Log** for a `BlurGo` load entry.

No public binary is published until the first alpha tag has passed the release checklist.

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

## Project structure

```text
src/                         OBS module, filter lifecycle, and validated settings
data/                        GPU effects and translations
tests/                       Dependency-free settings tests
docs/                        Architecture, product brief, decisions, and release QA
cmake/, build-aux/           Official OBS plugin-template build infrastructure
.github/                     Cross-platform build, format, package, and release workflows
```

## Performance guidance

GPU cost grows with source resolution and quality passes. Start with a 12 px radius and two passes. For a 4K source, reduce passes before reducing visual radius. Pixelate requires one processing pass regardless of the quality-pass control.

## Troubleshooting

- **BlurGo is missing from the filter list:** confirm the plugin package matches the OBS architecture and inspect the OBS log for module-load errors.
- **The image is unchanged:** ensure Effect mix is above 0% and the filter is enabled.
- **GPU usage is high:** reduce Quality passes, apply the filter before expensive downstream filters, or blur a lower-resolution nested scene.
- **The whole scene is not blurred:** use the nested/wrapper-scene workflow above; OBS does not expose the active root scene itself as a normal filter target.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Please report security issues using the private process in [SECURITY.md](SECURITY.md), not a public issue.

## License

BlurGo is licensed under the GNU General Public License, version 2 or later. See [LICENSE](LICENSE).
