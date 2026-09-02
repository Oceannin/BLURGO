# Contributing to BlurGo

Thanks for helping make BlurGo dependable for live production.

## Before you start

- Search existing issues before opening a new one.
- Keep changes focused and backwards-compatible where practical.
- Use Conventional Commits, for example `feat: add mask feathering` or `fix: preserve alpha at image edges`.
- Do not add a dependency when libobs or the standard library already solves the problem.

## Development workflow

1. Create a branch such as `feature/mask-regions` or `fix/hdr-composite`.
2. Configure and build with the preset for your operating system.
3. Run CTest and the manual checks in `docs/release-checklist.md`.
4. Run `python3 tools/release-preflight.py` to validate repository and release contracts.
5. Run the repository format workflow or the matching local format scripts.
6. Update `CHANGELOG.md` and user documentation when behavior changes.

## Pull requests

Include the user-visible problem and solution, tested OBS/platform/GPU details, before/after screenshots for rendering changes, relevant OBS logs, and performance measurements for shader changes.

Pull requests must build on every supported CI platform. A rendering change is not considered verified until it has been exercised inside OBS on at least one supported GPU.

## Rendering rules

- GPU objects are created and destroyed inside the OBS graphics context.
- Clamp texture addressing unless an effect explicitly documents another edge policy.
- Preserve premultiplied alpha.
- On failure, bypass the filter instead of emitting an empty frame or crashing OBS.
- Keep shader loops bounded and portable across Direct3D 11, Metal, and OpenGL.

## Reporting bugs

Include reproduction steps, the scene/source topology, exact settings, OBS version, operating system, GPU/driver, graphics backend, and an OBS log file.
