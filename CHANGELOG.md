# Changelog

All notable changes to BlurGo are documented here. The format is based on Keep a Changelog, and versions follow Semantic Versioning.

## [Unreleased]

### Planned

- Real-world GPU profiling on representative NVIDIA, AMD, and Intel hardware.
- Signed Windows installer after the alpha test cycle.

## [0.1.0] - 2026-09-01

### Added

- Native OBS video-filter plugin for individual sources and nested scenes.
- GPU Gaussian, box, and pixelate effects.
- Radius, quality-pass, pixel-block, and effect-mix controls.
- English and Russian localization.
- Render-target color-space negotiation and safe bypass behavior.
- Dependency-free settings validation tests.
- Cross-platform OBS plugin-template build, packaging, and draft-release workflows.
- Product brief, architecture record, contributor guide, security policy, and release checklist.
- Windows 11/D3D11 on-device smoke validation for image-source and nested-scene rendering.
- Reproducible OBS WebSocket runtime harness for render, lifecycle, transparency, persistence, and basic performance evidence.
- Headless Ubuntu OBS runtime validation that installs and exercises the packaged plugin under Xvfb.
- Hosted macOS OBS runtime validation that installs and exercises the packaged plugin in a real OBS process.
- Privacy-preserving Windows Game Capture QA that selects an authorized title, waits for the capture hook, exercises every mode, and records per-mode OBS Stats.

### Fixed

- Non-finite settings from external control now fall back to safe defaults instead of reaching GPU shaders.
- Shader identifiers now avoid GLSL reserved words, allowing the effects to compile on OpenGL as well as Direct3D.
- Zero-mix and zero-radius blur settings now use OBS's direct filter bypass instead of spending GPU time on invisible passes.
- Filter creation now fails safely when a required shader parameter is missing.
- Formatting workflows explicitly trust only the required OBS Homebrew formulae, preserving CI compatibility with Homebrew 6 tap security.
- Formatting workflows call the shared formatter driver directly and no longer depend on runner symlink materialization.
- Tagged releases now require a version matching `buildspec.json` and combine versioned release notes with generated package checksums.
- Binary packages now include the GPL license, README, contributor guide, and security policy in platform-appropriate locations.
- The OBS runtime harness can configure disposable video profiles, run long scene-switch stress tests, select display/window capture targets, and discard private capture frames after numeric validation.
- Runtime alpha validation accepts near-transparent pixels produced by wide blur kernels while still rejecting lost or flattened alpha channels.
- Windows QA now covers OBS 31.1.1 and 32.2.2, SDR through 4K60, P010/Rec. 2100 PQ, and a 30-minute memory-stability run.
- GitHub workflows now use the Node 24-based checkout action, removing the hosted-runner Node 20 deprecation warning.
- Explicitly required capture checks now fail instead of allowing an unsupported, unmatched, or black-frame `skipped` result to masquerade as a successful QA run.

### Known limitations

- Representative real-game capture, forced GPU-loss recovery, and maintainer sign-off remain before public binary release.
- Region masks and animated transitions are intentionally outside the first alpha scope.
