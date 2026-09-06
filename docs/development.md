# Development

[Documentation](README.md) · [Contributing](../CONTRIBUTING.md)

## Get the source

```bash
git clone https://github.com/Oceannin/BLURGO.git
cd BLURGO
```

BlurGo is a C17 libobs plugin with OBS `.effect` shaders. There is no JavaScript package manager or application `.env` file. Dependency versions and hashes live in `buildspec.json`; configure and build presets live in `CMakePresets.json`.

## Configure, build, and test


The repository follows the official OBS plugin template. Windows and macOS configuration downloads the pinned OBS build dependencies. Ubuntu uses the installed OBS development files.

### Windows x64

Prerequisites: Visual Studio 2022 with Desktop development with C++, Git, Windows SDK 10.0.22621, and CMake 3.30.5.

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

Prerequisites: CMake 3.28.3, Ninja, pkg-config, build-essential, and OBS development files discoverable by CMake as `libobs`.

For a fresh Ubuntu environment, the repository's build helper installs its dependencies and builds the plugin. It requires zsh and sudo access, adds the OBS Project PPA, and installs system packages; review [the setup script](../.github/scripts/utils.zsh/setup_ubuntu) before using it:

```bash
zsh .github/scripts/build-ubuntu --target ubuntu-x86_64 --config RelWithDebInfo
```

Once the dependencies are installed, use the presets directly:

```bash
cmake --preset ubuntu-x86_64
cmake --build --preset ubuntu-x86_64
ctest --test-dir build_x86_64 --output-on-failure
```

Build output is staged under the preset's `rundir` directory and packaged by GitHub Actions.

Validate version metadata, locale parity, dependency hashes, release files, workflow permissions, and immutable action pins with the dependency-free preflight:

```bash
python3 tools/release-preflight.py
```

The tagged release workflow additionally runs `python3 tools/release-preflight.py --tag <version>`. That mode rejects a tag until the versioned gate status records `ready to tag` (or an already published alpha) and every required field and checkbox in the manual sign-off is complete.


## Python checks

Python 3.10+ is needed for the QA tools, not for the plugin itself. Run the existing regression suites without connecting to OBS:

```bash
python3 tests/release-preflight-test.py
python3 tests/obs-smoke-test.py
```

On Windows, use `python` if `python3` is unavailable. For actual render checks, follow [Runtime testing](testing.md).

## Formatting and packaging

CI runs the shared formatting workflow for C/C++ and CMake. With zsh 5.8+, clang-format 19.1.1, and gersemi 0.12.0+ installed, the local entry points are:

```bash
FORMATTER_NAME=clang zsh build-aux/.run-format.zsh --check --fail-error
FORMATTER_NAME=gersemi zsh build-aux/.run-format.zsh --check --fail-error
```

See [.clang-format](../.clang-format), [.gersemirc](../.gersemirc), and the [format workflow](../.github/workflows/check-format.yaml) for the repository's settings. CI packages platform builds; a version tag invokes the gated draft-release workflow. Ordinary builds do not require signing credentials. Optional macOS signing uses `CODESIGN_IDENT` and `CODESIGN_TEAM` from the environment; keep certificates and secrets outside Git.

## Project structure


```text
src/                         OBS module, filter lifecycle, and validated settings
data/                        GPU effects and translations
tests/                       Dependency-free settings tests
tools/                       Reproducible OBS runtime QA harness
docs/                        User/developer guides, architecture, and release evidence
cmake/, build-aux/           Official OBS plugin-template build infrastructure
.github/                     Cross-platform build, format, package, and release workflows
```


## Build troubleshooting

- Configure on the platform matching the preset; CMake hides presets for other operating systems.
- Dependency downloads need network access. Check the configure log and the pinned URLs in `buildspec.json` if a download fails.
- Use the selected build configuration (`RelWithDebInfo`) when running CTest on Windows and macOS.
- Consult [release preparation](release-checklist.md) before preparing a distributable package.
