# Documentation

## Use BlurGo

| Guide | Contents |
| --- | --- |
| [Download and quick start](../README.md#download) | Packages, installation, controls, and troubleshooting |
| [Performance](performance.md) | Starting settings and how to interpret measurements |
| [Release notes: 0.1.0](release-notes/0.1.0.md) | Compatibility, limitations, and rollback |
| [Changelog](../CHANGELOG.md) | Changes by version |

## Develop and maintain

| Guide | Contents |
| --- | --- |
| [Development](development.md) | Prerequisites, build presets, tests, and formatting |
| [Contributing](../CONTRIBUTING.md) | Contribution workflow and rendering rules |
| [Architecture](architecture.md) | Modules, render lifecycle, and extension points |
| [Product scope](product-brief.md) | Current scope and explicit exclusions |
| [Native GPU filter decision](decisions/0001-native-gpu-filter.md) | Why the plugin uses native libobs rendering |
| [Runtime testing](testing.md) | Reproduce OBS checks in a disposable profile |
| [Release checklist](release-checklist.md) | Reusable checklist for the next release |

## Release evidence

The [0.1.0 release status](qa/0.1.0-gate-status.md) links the platform reports, package inspection, and recorded acceptance. These documents describe specific historical test environments; they are not a claim that every GPU or capture source has been tested. Candidate hashes identify the tested candidate, while release assets have their own published checksums.

## What belongs in Git

Keep information that helps someone use, reproduce, debug, or maintain the plugin:

- User guides, architecture decisions, known limitations, and release notes.
- Reproducible test scripts and concise, redacted release evidence.
- Relevant platform/GPU versions, test settings, commit IDs, and package hashes.
- Small, deliberately selected screenshots of generated test patterns, with provenance.

Keep working material in ignored `artifacts/` or `.local/`:

- Raw OBS logs, crash dumps, recordings, generated reports, and temporary screenshots.
- Portable OBS installations, scene collections, profile exports, and downloaded packages.
- Personal paths, machine/account names, credentials, signing keys, and WebSocket passwords.
- Task transcripts, agent instructions, private approval conversations, and scratch plans.

Before attaching logs or screenshots to an issue, review them for stream keys, private URLs, window titles, and personal information. A `.gitignore` rule does not remove files already tracked or erase earlier commits. Use [SECURITY.md](../SECURITY.md) for suspected credential exposure.
