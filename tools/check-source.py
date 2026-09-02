#!/usr/bin/env python3
"""Fast, dependency-free source and security sanity checks for Dagric OS.

This deliberately checks properties that are easy to lose silently and cheap to
prove before an ISO build: parseable source data, safe Polkit defaults, immutable
GitHub Action references, no committed private keys, and no merge debris.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]
INCLUDES = ROOT / "config/includes.chroot"
POLICIES = INCLUDES / "usr/share/polkit-1/actions"
WORKFLOWS = ROOT / ".github/workflows"
GIT = shutil.which("git") or shutil.which("git.exe")
PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
SENSITIVE_NAME = re.compile(
    r"(^|/)(?:\.env(?:\..*)?|\.secrets?(?:/|$)|id_(?:rsa|dsa|ecdsa|ed25519)$|"
    r"credentials(?:\.[^/]*)?|[^/]+\.(?:p12|pfx|key|pem))$",
    re.IGNORECASE,
)


def tracked_files() -> list[str]:
    if not GIT:
        raise RuntimeError("git is required for repository security checks")
    result = subprocess.run(
        [GIT, "-c", f"safe.directory={ROOT}", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_json(errors: list[str]) -> int:
    files: set[pathlib.Path] = {ROOT / "firebase.json"}
    for base in (ROOT / "config", ROOT / "site", ROOT / "test"):
        files.update(base.rglob("*.json"))
    for path in (ROOT / "promo/package.json", ROOT / "promo/social-batch.json"):
        if path.exists():
            files.add(path)
    checked = 0
    for path in sorted(files):
        if not path.is_file():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            fail(errors, f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        checked += 1
    return checked


def check_python(errors: list[str]) -> int:
    checked = 0
    for base in (ROOT / "config", ROOT / "infra", ROOT / "test", ROOT / "tools"):
        for path in base.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                raw = path.read_bytes()
            except OSError as exc:
                fail(errors, f"{path.relative_to(ROOT)}: cannot read source: {exc}")
                continue
            is_python = path.suffix == ".py" or raw.startswith((b"#!/usr/bin/python", b"#!/usr/bin/env python"))
            if not is_python:
                continue
            try:
                source = raw.decode("utf-8")
                compile(source, str(path.relative_to(ROOT)), "exec")
            except (UnicodeError, SyntaxError) as exc:
                fail(errors, f"{path.relative_to(ROOT)}: invalid Python: {exc}")
            checked += 1
    return checked


def check_polkit(errors: list[str]) -> int:
    checked = 0
    for path in sorted(POLICIES.glob("*.policy")):
        checked += 1
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            fail(errors, f"{path.relative_to(ROOT)}: invalid Polkit XML: {exc}")
            continue
        actions = root.findall("./action")
        if not actions:
            fail(errors, f"{path.relative_to(ROOT)}: contains no Polkit action")
        for action in actions:
            action_id = action.get("id", "<missing id>")
            defaults = action.find("./defaults")
            if defaults is None:
                fail(errors, f"{path.relative_to(ROOT)}: {action_id} has no defaults")
                continue
            for name in ("allow_any", "allow_inactive"):
                value = defaults.findtext(name)
                if value != "no":
                    fail(errors, f"{path.relative_to(ROOT)}: {action_id} must set {name}=no, found {value!r}")
            active = defaults.findtext("allow_active")
            if active not in {"auth_admin", "auth_admin_keep"}:
                fail(errors, f"{path.relative_to(ROOT)}: {action_id} has unsafe allow_active={active!r}")
            annotations = {
                node.get("key"): (node.text or "").strip()
                for node in action.findall("./annotate")
            }
            target = annotations.get("org.freedesktop.policykit.exec.path", "")
            if not target.startswith("/"):
                fail(errors, f"{path.relative_to(ROOT)}: {action_id} has no absolute exec.path")
            elif not (INCLUDES / target.lstrip("/")).is_file():
                fail(errors, f"{path.relative_to(ROOT)}: {action_id} targets missing {target}")
    if checked == 0:
        fail(errors, "no Polkit policy files were found")
    return checked


def check_workflows(errors: list[str]) -> int:
    checked = 0
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"\s*(?:-\s*)?uses:\s*([^#\s]+)", line)
            if not match:
                continue
            checked += 1
            reference = match.group(1)
            if reference.startswith("./") or reference.startswith("docker://"):
                continue
            if not PINNED_ACTION.fullmatch(reference):
                fail(errors, f"{path.relative_to(ROOT)}:{number}: action is not pinned to a 40-character commit: {reference}")
    return checked


def check_repository(errors: list[str]) -> int:
    tracked = tracked_files()
    for name in tracked:
        if SENSITIVE_NAME.search(name):
            fail(errors, f"tracked sensitive-looking path: {name}")
    # Conflict markers only count at the start of a line. Searching for bare
    # runs of '=' produces hundreds of false positives from deliberate visual
    # separators in shell output, QML, documentation, and translation strings.
    merge_result = subprocess.run(
        [
            GIT, "-c", f"safe.directory={ROOT}", "grep", "--cached", "-I", "-n", "-E",
            r"^(<<<<<<< |>>>>>>> |=======$)",
            "--", ":(exclude)tools/check-source.py",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if merge_result.returncode == 0 and merge_result.stdout.strip():
        fail(errors, f"unresolved merge markers:\n{merge_result.stdout.strip()}")
    elif merge_result.returncode not in (0, 1):
        fail(errors, "git grep failed while checking merge markers")
    key_result = subprocess.run(
        [GIT, "-c", f"safe.directory={ROOT}", "grep", "--cached", "-I", "-n", "-E", r"BEGIN ([A-Z0-9 ]+ )?PRIVATE KEY"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if key_result.returncode == 0 and key_result.stdout.strip():
        fail(errors, f"private key material appears to be tracked:\n{key_result.stdout.strip()}")
    elif key_result.returncode not in (0, 1):
        fail(errors, "git grep failed while checking for private keys")
    return len(tracked)


def main() -> int:
    errors: list[str] = []
    counts = {
        "JSON documents": check_json(errors),
        "Python sources": check_python(errors),
        "Polkit policies": check_polkit(errors),
        "pinned action references": check_workflows(errors),
        "tracked paths": check_repository(errors),
    }
    if errors:
        print("source-check: FAILED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    summary = ", ".join(f"{value} {name}" for name, value in counts.items())
    print(f"source-check: passed ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
