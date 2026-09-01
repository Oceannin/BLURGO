# Architecture

## Overview

BlurGo is a native libobs source filter. OBS treats both ordinary visual sources and nested scenes as renderable sources, so one filter implementation covers both workflows.

```text
OBS target source
      |
      v
input texrender (source color space)
      |
      +--> Pixelate ----------+
      |                       |
      +--> horizontal blur --> vertical blur -- repeat 1..4 times
                                      |
                                      v
                          composite with original
                                      |
                                      v
                              OBS filter output
```

## Modules

- `src/plugin-main.c`: module registration and metadata.
- `src/blurgo-filter.c`: OBS lifecycle, properties, graphics resources, render passes, and bypass behavior.
- `src/blurgo-settings.*`: dependency-free defaults, bounds, and mode-to-shader mapping.
- `data/blurgo-blur.effect`: Gaussian, box, and pixelate GPU techniques.
- `data/blurgo-composite.effect`: effect/original mixing while preserving alpha.
- `tests/blurgo-settings-test.c`: portable configuration contract tests.

## Rendering lifecycle

1. `create` allocates effects and texrenders inside the OBS graphics context.
2. `update` copies OBS settings into a normalized internal structure.
3. `video_render` negotiates the target color space and recreates render targets if the format changes.
4. The target is captured once, processed through bounded GPU passes, and composited with the original.
5. Missing targets, zero dimensions, capture failures, or render failures call OBS's safe filter-bypass path.
6. Zero-mix and zero-radius blur settings bypass the full render pipeline before allocating per-frame GPU work.
7. `destroy` releases every GPU object inside the graphics context.

## Performance model

Gaussian and box modes use two full-frame render passes per configured quality pass, plus capture and composite. Pixelate uses one processing pass, plus capture and composite. GPU cost is therefore proportional to pixel count and pass count, not blur radius.

## Extension points

- New full-frame modes add a bounded effect technique and enum entry.
- Region masks should be a separate composite concern, not embedded in every blur shader.
- Downsampling can be introduced behind a quality policy while keeping output dimensions unchanged.
- Hotkeys and frontend automation would require enabling the OBS frontend API; the rendering plugin does not currently depend on it.
