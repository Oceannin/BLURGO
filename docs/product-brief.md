# Product brief

## Problem

Streamers need reliable real-time blur without fragile browser overlays, duplicated scene captures, or vendor-specific GPU dependencies. Existing options often make scene-wide setup awkward or expose too little control.

## Primary users

- Live streamers who must hide private or sensitive visual content.
- Production operators who need a repeatable scene-level look.
- OBS plugin contributors who need a maintainable blur foundation.

## Core job

Apply a predictable GPU blur to one visual source or to a complete composited scene, tune it without leaving OBS, and preserve stream stability if the effect cannot render.

## First alpha scope

- Native OBS effect filter.
- Gaussian, box, and pixelate modes.
- Radius/block size, quality passes, and mix controls.
- Source and nested-scene use.
- English and Russian UI.
- Windows x64 primary support with portable macOS/Linux build infrastructure.

## Out of scope for the first alpha

- Region masks, object tracking, and OCR-driven privacy detection.
- Background segmentation.
- Per-scene automatic switching and hotkeys.
- A standalone application or browser overlay.
- Installer signing and macOS notarization.

## Success criteria

- OBS loads and unloads the plugin without errors.
- All modes render at 1080p60 without visual corruption on supported hardware.
- Filter removal, source deletion, scene switching, and OBS shutdown do not crash.
- Invalid or unavailable GPU resources bypass safely.
- Settings survive OBS restart and stay within documented bounds.
- Release artifacts build reproducibly in CI.

## Constraints

- OBS Studio 31.1.1 is the pinned build baseline.
- Rendering must remain compatible with OBS graphics backends; no CUDA-only or Direct3D-only path.
- The plugin is GPL-2.0-or-later to remain compatible with OBS Studio and the official plugin template.
