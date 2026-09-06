# Performance guidance

[Documentation](README.md) · [Quick start](../README.md#quick-start)


GPU cost grows with source resolution and quality passes. The following are conservative starting points, not guarantees; validate them with OBS Stats on the actual scene and capture backend.

| GPU / workload | Starting point |
| --- | --- |
| Entry-level or integrated GPU, 1080p60 | Gaussian/Box radius 8-12, one pass; prefer Pixelate when it fits the look. |
| Mid-tier GPU, 1080p60-1440p60 | Gaussian radius 12, two passes. |
| High-tier GPU or 4K60 | Gaussian radius 12, two passes; reduce passes first if render time rises. |

Pixelate requires one processing pass regardless of the quality-pass control. Apply BlurGo to a lower-resolution nested scene when the source does not need full-canvas resolution. The published 0.1.0 Windows measurements were collected on an RTX 4070 Ti SUPER and are documented in [the Windows runtime QA report](qa/0.1.0-windows-smoke.md). The [Ubuntu runtime report](qa/0.1.0-ubuntu-smoke.md) and [macOS runtime report](qa/0.1.0-macos-smoke.md) use software OpenGL for functional coverage and are not hardware-performance benchmarks.
