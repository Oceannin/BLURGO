# ADR 0001: Build BlurGo as a native GPU source filter

## Status

Accepted — 2026-09-01

## Context

The product must blur a single source or a complete scene reliably during live production. Lua/Python scripts can manage OBS objects but do not provide a robust, portable path for custom multi-pass GPU effects. Browser overlays add capture and scene-composition complexity. Vendor SDKs exclude unsupported GPUs.

## Decision

Implement BlurGo as a C17 libobs source-filter plugin using OBS `.effect` shaders and texrender objects. Use the official OBS plugin template for dependency pinning, packaging, and cross-platform CI. Treat a nested scene as the scene-wide filter target.

## Consequences

- The filter runs in OBS's native render pipeline with no browser or scripting runtime.
- One implementation works for ordinary sources and nested scenes.
- Shader code must remain portable across OBS graphics backends.
- Native crashes are possible if lifecycle rules are violated, so graphics-context ownership and safe bypasses are mandatory.
- Users need a compiled package that matches their OBS platform and architecture.
