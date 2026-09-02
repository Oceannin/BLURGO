# Release checklist

## Automated gates

- [ ] `python3 tools/release-preflight.py` passes.
- [ ] Format workflow passes.
- [ ] Windows x64 build and settings tests pass.
- [ ] macOS Universal build and settings tests pass.
- [ ] Ubuntu 24.04 x86_64 build and settings tests pass.
- [ ] Packages and SHA-256 checksums are produced.

## OBS smoke test

Record OBS version, operating system, GPU, driver, and graphics backend for every run.

- [ ] Plugin loads with no warning or error in the OBS log.
- [ ] Gaussian, box, and pixelate render on an image source.
- [ ] All modes render on at least one standard capture source (Window or Display Capture) where available.
- [ ] Nested-scene workflow blurs the complete scene.
- [ ] Radius, passes, block size, and mix controls update live.
- [ ] Settings persist after restarting OBS.
- [ ] Transparent source edges remain visually correct.
- [ ] SDR and HDR/extended-color scenes do not produce black or washed-out frames.
- [ ] Source resize, deletion, filter reorder/removal, scene switch, and OBS shutdown do not crash.

## Performance test

- [ ] Capture baseline GPU frame time without BlurGo.
- [ ] Measure 1080p60 Gaussian at radius 12, two passes.
- [ ] Measure 1440p60 and 4K60 where hardware permits.
- [ ] Confirm no increasing GPU memory use over a 30-minute scene-switch loop.
- [ ] Document recommended settings for low-, mid-, and high-tier GPUs.

## Release hygiene

- [ ] Version matches `buildspec.json`, tag, package metadata, and changelog.
- [ ] README requirements and installation steps match the artifacts.
- [ ] Known issues are documented.
- [ ] Security policy and license ship in source and packages.
- [ ] Draft release notes include compatibility, test matrix, checksums, and rollback guidance.
- [ ] Maintainer promotes the draft only after manual QA sign-off.
- [ ] `python3 tools/release-preflight.py --tag <version>` passes before the tag workflow creates the draft.

## Optional post-alpha qualification

- [ ] Representative Game Capture compatibility is checked with an authorized title.
- [ ] GPU loss/reinitialization is exercised with an approved method on a disposable lab system.
