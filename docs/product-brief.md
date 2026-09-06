# Product scope

BlurGo adds full-source GPU blur to OBS Studio. The same filter handles ordinary sources and a complete composition exposed as a nested Scene source.

## Included in 0.1.0

- Gaussian, Box, and Pixelate modes with live radius/block-size, pass, and mix controls.
- Source and nested-scene workflows in the standard OBS filter stack.
- English and Russian controls.
- Windows x64, macOS Universal, and Ubuntu x86_64 packages. See [release notes](release-notes/0.1.0.md) for tested environments and limitations.

## Outside the first alpha

Region masks, object tracking, OCR, background segmentation, animated transitions, automatic scene switching, and hotkeys. BlurGo is not a standalone application or a privacy/redaction guarantee; render failures intentionally bypass the effect.

## Technical constraints

The build baseline is OBS Studio 31.1.1. Rendering uses portable OBS effects without vendor-specific GPU SDKs. The project is GPL-2.0-or-later. See [architecture](architecture.md) and the [native filter decision](decisions/0001-native-gpu-filter.md).
