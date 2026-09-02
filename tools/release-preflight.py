"""Validate BlurGo release metadata and enforce the manual tag gate."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-(?:beta|rc)[0-9]*)?$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
HASH = re.compile(r"^[0-9a-f]{64}$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_buildspec(root: Path) -> dict[str, object]:
    return json.loads(read_text(root / "buildspec.json"))


def locale_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";", "[")) or "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())
    return keys


def external_action_refs(root: Path) -> list[tuple[Path, int, str, str]]:
    references: list[tuple[Path, int, str, str]] = []
    candidates = list((root / ".github" / "workflows").glob("*.y*ml"))
    candidates.extend((root / ".github" / "actions").glob("**/*.y*ml"))
    for path in candidates:
        for line_number, line in enumerate(read_text(path).splitlines(), 1):
            match = re.match(r"^\s*uses:\s+([^\s#]+)", line)
            if match is None:
                continue
            target = match.group(1)
            if target.startswith(("./", "docker://")):
                continue
            if "@" not in target:
                references.append((path, line_number, target, ""))
                continue
            action, ref = target.rsplit("@", 1)
            references.append((path, line_number, action, ref))
    return references


def dependency_hash_errors(buildspec: dict[str, object]) -> list[str]:
    errors: list[str] = []
    dependencies = buildspec.get("dependencies")
    if not isinstance(dependencies, dict):
        return ["buildspec.json: dependencies must be an object"]
    for dependency_name, dependency in dependencies.items():
        if not isinstance(dependency, dict):
            errors.append(f"buildspec.json: dependency {dependency_name!r} must be an object")
            continue
        for group_name in ("hashes", "debugSymbols"):
            hashes = dependency.get(group_name, {})
            if not isinstance(hashes, dict):
                errors.append(
                    f"buildspec.json: {dependency_name}.{group_name} must be an object"
                )
                continue
            for platform, digest in hashes.items():
                if not isinstance(digest, str) or HASH.fullmatch(digest) is None:
                    errors.append(
                        f"buildspec.json: {dependency_name}.{group_name}.{platform} "
                        "must be a lowercase SHA-256"
                    )
    return errors


def standard_errors(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        buildspec = load_buildspec(root)
    except (OSError, json.JSONDecodeError) as error:
        return [f"buildspec.json could not be read: {error}"]

    version = buildspec.get("version")
    if not isinstance(version, str) or SEMVER.fullmatch(version) is None:
        errors.append("buildspec.json: version must be a supported SemVer release identifier")
        version = "INVALID"

    required_paths = (
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "LICENSE",
        "CMakeLists.txt",
        "data/blurgo-blur.effect",
        "data/blurgo-composite.effect",
        "data/locale/en-US.ini",
        "data/locale/ru-RU.ini",
        "docs/product-brief.md",
        "docs/architecture.md",
        "docs/release-checklist.md",
        f"docs/release-notes/{version}.md",
        f"docs/qa/{version}-gate-status.md",
        f"docs/qa/{version}-manual-signoff.md",
        "tests/blurgo-settings-test.c",
        "tests/obs-smoke-test.py",
        "tests/release-preflight-test.py",
        "tools/obs-smoke.py",
        "tools/release-preflight.py",
        "tools/requirements-qa.txt",
        ".github/dependabot.yml",
        ".github/workflows/push.yaml",
        ".github/workflows/pr-pull.yaml",
        ".github/workflows/build-project.yaml",
    )
    for relative_path in required_paths:
        if not (root / relative_path).is_file():
            errors.append(f"missing required release file: {relative_path}")

    changelog_path = root / "CHANGELOG.md"
    if changelog_path.is_file():
        changelog = read_text(changelog_path)
        release_heading = rf"^## \[{re.escape(version)}\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$"
        if re.search(release_heading, changelog, re.MULTILINE) is None:
            errors.append(f"CHANGELOG.md: missing dated [{version}] release heading")

    readme_path = root / "README.md"
    release_notes_path = root / "docs" / "release-notes" / f"{version}.md"
    dependencies = buildspec.get("dependencies", {})
    obs_dependency = dependencies.get("obs-studio", {}) if isinstance(dependencies, dict) else {}
    obs_version = obs_dependency.get("version") if isinstance(obs_dependency, dict) else None
    if isinstance(obs_version, str):
        readme_requirement = f"OBS Studio {obs_version} or newer"
        notes_requirement = f"Minimum OBS Studio version: {obs_version}."
        if readme_path.is_file() and readme_requirement not in read_text(readme_path):
            errors.append("README.md: minimum OBS version does not match buildspec.json")
        if release_notes_path.is_file() and notes_requirement not in read_text(release_notes_path):
            errors.append("release notes: minimum OBS version does not match buildspec.json")

    locale_paths = [root / "data" / "locale" / name for name in ("en-US.ini", "ru-RU.ini")]
    if all(path.is_file() for path in locale_paths):
        english_keys = locale_keys(locale_paths[0])
        russian_keys = locale_keys(locale_paths[1])
        if english_keys != russian_keys:
            errors.append(
                "locale key mismatch: "
                f"missing from ru-RU={sorted(english_keys - russian_keys)}, "
                f"missing from en-US={sorted(russian_keys - english_keys)}"
            )

    requirements_path = root / "tools" / "requirements-qa.txt"
    if requirements_path.is_file():
        for line_number, raw_line in enumerate(read_text(requirements_path).splitlines(), 1):
            requirement = raw_line.strip()
            if requirement and not requirement.startswith("#") and "==" not in requirement:
                errors.append(
                    f"tools/requirements-qa.txt:{line_number}: dependency must be exactly pinned"
                )

    for path, line_number, action, ref in external_action_refs(root):
        if FULL_SHA.fullmatch(ref) is None:
            relative_path = path.relative_to(root).as_posix()
            location = f"{relative_path}:{line_number}"
            errors.append(
                f"{location}: external action {action!r} must use an immutable 40-character SHA"
            )

    pr_workflow_path = root / ".github" / "workflows" / "pr-pull.yaml"
    if pr_workflow_path.is_file() and "secrets: inherit" in read_text(pr_workflow_path):
        errors.append("pr-pull.yaml: pull-request workflows must not inherit repository secrets")

    build_workflow_path = root / ".github" / "workflows" / "build-project.yaml"
    if build_workflow_path.is_file():
        build_workflow = read_text(build_workflow_path)
        pull_request_case = build_workflow.partition("pull_request)")[2].partition(";;")[0]
        if "codesign:true" in pull_request_case:
            errors.append("build-project.yaml: pull-request builds must not enable code signing")

    push_workflow_path = root / ".github" / "workflows" / "push.yaml"
    if push_workflow_path.is_file():
        push_workflow = read_text(push_workflow_path)
        workflow_header = push_workflow.partition("jobs:")[0]
        if re.search(r"permissions:\s*\n\s*contents:\s*read", workflow_header) is None:
            errors.append("push.yaml: top-level contents permission must be read-only")
        release_job = push_workflow.partition("create-release:")[2]
        if re.search(r"permissions:\s*\n\s*contents:\s*write", release_job) is None:
            errors.append(
                "push.yaml: release job must explicitly request contents write permission"
            )

    errors.extend(dependency_hash_errors(buildspec))
    return errors


def value_after_prefix(lines: list[str], prefix: str) -> str | None:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return None


def tag_errors(root: Path, tag: str) -> list[str]:
    errors: list[str] = []
    try:
        buildspec = load_buildspec(root)
    except (OSError, json.JSONDecodeError) as error:
        return [f"buildspec.json could not be read: {error}"]
    version = buildspec.get("version")
    if tag != version:
        errors.append(f"tag {tag!r} does not match buildspec version {version!r}")
    if not isinstance(version, str):
        return errors

    gate_path = root / "docs" / "qa" / f"{version}-gate-status.md"
    if not gate_path.is_file():
        errors.append(f"missing release gate status: {gate_path.relative_to(root).as_posix()}")
    else:
        gate = read_text(gate_path)
        if "Decision: **ready to tag**" not in gate:
            errors.append("release gate decision is not 'ready to tag'")
        allowed_unchecked = f"Public `{version}` tag and GitHub Release."
        unchecked = [
            line[6:].strip()
            for line in gate.splitlines()
            if line.startswith("- [ ] ") and line[6:].strip() != allowed_unchecked
        ]
        if unchecked:
            errors.append("release gate still has unchecked requirements: " + "; ".join(unchecked))

    manual_path = root / "docs" / "qa" / f"{version}-manual-signoff.md"
    if not manual_path.is_file():
        errors.append(f"missing manual sign-off: {manual_path.relative_to(root).as_posix()}")
        return errors

    manual = read_text(manual_path)
    lines = manual.splitlines()
    unchecked_count = sum(1 for line in lines if line.startswith("- [ ] "))
    if unchecked_count:
        errors.append(f"manual sign-off still has {unchecked_count} unchecked item(s)")

    required_fields = (
        "- Date:",
        "- Tester:",
        "- BlurGo commit/package SHA-256:",
        "- OBS Studio version:",
        "- Operating system/build:",
        "- GPU/driver:",
        "- Graphics backend:",
        "- Canvas/output/FPS and SDR/HDR format:",
        "- Source/scene used:",
        "Original:",
        "Gaussian:",
        "Box:",
        "Pixelate:",
        "Source workflow:",
        "Nested-scene workflow:",
        "Settings/restart notes:",
        "OBS log path or private attachment:",
        "Maintainer/name:",
        "Decision date:",
    )
    missing_values = [field for field in required_fields if not value_after_prefix(lines, field)]
    if missing_values:
        errors.append("manual sign-off has empty required fields: " + ", ".join(missing_values))

    package_evidence = value_after_prefix(lines, "- BlurGo commit/package SHA-256:") or ""
    if re.search(r"\b[0-9a-fA-F]{40,64}\b", package_evidence) is None:
        errors.append("manual sign-off must record a commit or package hash")
    if value_after_prefix(lines, "Decision:") != "`approve`":
        errors.append("manual sign-off decision is not exactly `approve`")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        help="Also enforce completed manual QA and an exact tag/buildspec version match",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors = standard_errors(ROOT)
    if args.tag:
        errors.extend(tag_errors(ROOT, args.tag))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    mode = f"tag {args.tag}" if args.tag else "repository"
    print(f"BlurGo release preflight passed for {mode}.")


if __name__ == "__main__":
    main()
