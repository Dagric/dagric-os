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
SENSITIVE_UNTRACKED_EXPORT = re.compile(
    r"(^|/)(?:[^/]*(?:password|credential|cookie|login)[^/]*\.(?:csv|json|txt|db|sqlite)|"
    r"Cookies|Local State|Bookmarks|Preferences)$|/(?:Sessions|Network)/",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    (re.compile(rb"(?<![A-Za-z0-9])sk_[0-9a-fA-F]{32,}(?![A-Za-z0-9])"), "ElevenLabs-style API key"),
    (re.compile(rb"(?<![A-Za-z0-9])sk-proj-[A-Za-z0-9_-]{20,}"), "OpenAI API key"),
    (re.compile(rb"(?<![A-Za-z0-9])sk_(?:live|test)_[A-Za-z0-9]{16,}"), "Stripe secret key"),
    (re.compile(rb"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile(rb"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"), "AWS access key"),
)
SECRET_SCAN_SUFFIXES = {
    "", ".conf", ".css", ".desktop", ".env", ".html", ".ini", ".js",
    ".json", ".md", ".mjs", ".policy", ".ps1", ".py", ".qml", ".service",
    ".sh", ".toml", ".txt", ".xml", ".yaml", ".yml",
}
PUBLIC_TEXT_SUFFIXES = {
    ".css", ".desktop", ".html", ".js", ".json", ".md", ".qml", ".sh", ".yaml", ".yml"
}
PUBLIC_COPY_ROOTS = (
    ROOT / "site",
    ROOT / ".github",
    INCLUDES / "etc/calamares",
    INCLUDES / "usr/share/applications",
    INCLUDES / "usr/share/dagric",
    INCLUDES / "usr/share/wallpapers",
)
PUBLIC_COPY_FILES = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "CODE_OF_CONDUCT.md",
    ROOT / "SECURITY.md",
    ROOT / "SUPPORT.md",
)
PUBLIC_CREDIT_PATTERNS = (
    (re.compile(r"\bDGR Operations\b", re.IGNORECASE), "obsolete organization name"),
    (
        re.compile(r"\bImpressions\s+Direct\s+360\s+LLC\b", re.IGNORECASE),
        "inaccurate spaced legal entity name",
    ),
    (
        re.compile(
            r"\b(?:made|written|created|edited|generated)\s+(?:by|with)\s+"
            r"(?:ChatGPT|OpenAI(?:\s+ImageGen)?|Claude|Codex|Gemini)\b",
            re.IGNORECASE,
        ),
        "internal tool credit",
    ),
    (re.compile(r"\bwith\s+OpenAI\s+ImageGen\b", re.IGNORECASE), "internal tool credit"),
    (
        re.compile(
            r'"(?:reviewed|audited|generated|created|written)By"\s*:\s*"'
            r'(?:ChatGPT|OpenAI|Codex|Claude|Gemini)',
            re.IGNORECASE,
        ),
        "internal tool credit",
    ),
    (re.compile(r"\bas an AI\b", re.IGNORECASE), "assistant boilerplate"),
)
SITE_COMMENT = re.compile(r"<!--.*?-->|/\*.*?\*/", re.DOTALL)


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


def repository_files() -> list[str]:
    """Tracked and non-ignored untracked paths, without ever printing contents."""
    if not GIT:
        raise RuntimeError("git is required for repository security checks")
    result = subprocess.run(
        [
            GIT, "-c", f"safe.directory={ROOT}", "ls-files", "-z",
            "--cached", "--others", "--exclude-standard",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        item.decode("utf-8", "surrogateescape").replace("\\", "/")
        for item in result.stdout.split(b"\0") if item
    ]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_json(errors: list[str]) -> int:
    files: set[pathlib.Path] = {ROOT / "firebase.json"}
    for base in (ROOT / "config", ROOT / "site", ROOT / "test"):
        files.update(base.rglob("*.json"))
    for path in (ROOT / "promo/package.json", ROOT / "promo/package-lock.json", ROOT / "promo/social-batch.json"):
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


def public_copy_files() -> list[pathlib.Path]:
    files = {path for path in PUBLIC_COPY_FILES if path.is_file()}
    for base in PUBLIC_COPY_ROOTS:
        if not base.is_dir():
            continue
        files.update(
            path for path in base.rglob("*")
            if path.is_file() and path.suffix.lower() in PUBLIC_TEXT_SUFFIXES
        )
    return sorted(files)


def check_public_copy(errors: list[str]) -> int:
    checked = 0
    for path in public_copy_files():
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fail(errors, f"{path.relative_to(ROOT)}: cannot read public text: {exc}")
            continue
        checked += 1
        for number, line in enumerate(source.splitlines(), 1):
            for pattern, label in PUBLIC_CREDIT_PATTERNS:
                if pattern.search(line):
                    fail(errors, f"{path.relative_to(ROOT)}:{number}: {label} in public copy")

        if path.is_relative_to(ROOT / "site") and path.suffix.lower() in {".css", ".html", ".js"}:
            for comment in SITE_COMMENT.finditer(source):
                if len(comment.group(0)) <= 320:
                    continue
                number = source.count("\n", 0, comment.start()) + 1
                fail(
                    errors,
                    f"{path.relative_to(ROOT)}:{number}: source comment is {len(comment.group(0))} "
                    "characters; move durable rationale to documentation",
                )
    return checked


def check_repository(errors: list[str]) -> int:
    tracked = tracked_files()
    tracked_set = set(tracked)
    for name in tracked:
        if SENSITIVE_NAME.search(name):
            fail(errors, f"tracked sensitive-looking path: {name}")
    for name in repository_files():
        if name in tracked_set:
            continue
        if SENSITIVE_NAME.search(name) or SENSITIVE_UNTRACKED_EXPORT.search(name):
            fail(errors, f"untracked sensitive-looking path: {name}")
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


def check_secret_material(errors: list[str]) -> int:
    checked = 0
    for name in repository_files():
        path = ROOT / name
        if path.suffix.lower() not in SECRET_SCAN_SUFFIXES:
            continue
        try:
            if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                continue
            raw = path.read_bytes()
        except OSError as exc:
            fail(errors, f"{name}: cannot read while scanning for credentials: {exc}")
            continue
        if b"\0" in raw:
            continue
        checked += 1
        for pattern, label in SECRET_PATTERNS:
            match = pattern.search(raw)
            if match:
                # Report location and token class only. Echoing the matching
                # bytes would leak the credential into CI logs a second time.
                line = raw.count(b"\n", 0, match.start()) + 1
                fail(errors, f"{name}:{line}: possible {label}; remove and rotate it")
    return checked


def check_dependency_floor(errors: list[str]) -> int:
    package_path = ROOT / "promo/package.json"
    lock_path = ROOT / "promo/package-lock.json"
    if not package_path.is_file() or not lock_path.is_file():
        fail(errors, "promo dependency manifests are missing")
        return 0
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(errors, f"could not inspect promo dependency versions: {exc}")
        return 0

    minimum = (4, 0, 520)
    dependencies = package.get("dependencies", {})
    locked = lock.get("packages", {})
    checked = 0
    for dependency in ("remotion", "@remotion/cli"):
        declared = dependencies.get(dependency)
        resolved = locked.get(f"node_modules/{dependency}", {}).get("version")
        checked += 1
        if not isinstance(declared, str) or not re.fullmatch(r"\d+\.\d+\.\d+", declared):
            fail(errors, f"promo/package.json: {dependency} must use an exact version")
            continue
        version = tuple(int(part) for part in declared.split("."))
        if version < minimum:
            fail(errors, f"promo/package.json: {dependency} {declared} is below security floor 4.0.520")
        if resolved != declared:
            fail(errors, f"promo/package-lock.json: {dependency} resolves to {resolved!r}, expected {declared}")
    return checked


def check_security_contracts(errors: list[str]) -> int:
    checked = 0

    ai = (INCLUDES / "usr/bin/dagric-ai").read_text(encoding="utf-8")
    ollama_release = (INCLUDES / "usr/lib/dagric/ollama-release").read_text(encoding="utf-8")
    if "ollama.com/install.sh" in ai or re.search(r"curl[^\n|]*\|\s*(?:ba)?sh\b", ai):
        fail(errors, "dagric-ai must not execute a mutable remote installer")
    if not re.search(r'^OLLAMA_SHA256="[0-9a-f]{64}"$', ollama_release, re.MULTILINE):
        fail(errors, "ollama-release must pin a 64-character SHA-256 digest")
    ai_manual = (INCLUDES / "usr/share/dagric/manual/tool-dagric-ai.html").read_text(encoding="utf-8")
    if re.search(r"pipes? a downloaded script|curl\s*\|\s*(?:ba)?sh", ai_manual, re.IGNORECASE):
        fail(errors, "Local AI manual must describe the pinned archive flow, not curl-to-shell")
    if "prompts and inference stay" not in ai_manual:
        fail(errors, "Local AI manual must scope its privacy claim to prompts and inference")
    checked += 3

    store = (INCLUDES / "usr/bin/dagric-store").read_text(encoding="utf-8")
    if 'sudo apt install firefox"' in store or 'sudo apt install kvantum"' in store:
        fail(errors, "dagric-store must use Debian package names firefox-esr and qt-style-kvantum")
    checked += 1

    marketing_paths = (
        ROOT / "promo/social-batch.json",
        ROOT / "promo/remaster-social-audio.py",
        ROOT / "promo/campaign-200/campaign.json",
        ROOT / "promo/campaign-200/master-schedule.csv",
        ROOT / "promo/campaign-200/buffer-queue.csv",
        ROOT / "promo/campaign-200/later-queue.csv",
        ROOT / "promo/campaign-200/publer-queue.csv",
    )
    unscoped_machine_price = re.compile(
        r"\$39\s+once\s+for\s+one\s+machine|"
        r"one[- ]time.{0,50}purchase\s+for\s+one\s+machine|"
        r"thirty-nine dollars once for one machine",
        re.IGNORECASE,
    )
    for marketing_path in marketing_paths:
        if not marketing_path.is_file():
            fail(errors, f"missing marketing entitlement surface: {marketing_path.relative_to(ROOT)}")
            continue
        marketing = marketing_path.read_text(encoding="utf-8")
        if unscoped_machine_price.search(marketing):
            fail(
                errors,
                f"{marketing_path.relative_to(ROOT)} uses an unscoped one-machine software-sale claim",
            )
    for canonical in marketing_paths[:2]:
        marketing = canonical.read_text(encoding="utf-8").casefold()
        if "component licence rights remain unchanged" not in marketing:
            fail(
                errors,
                f"{canonical.relative_to(ROOT)} must preserve component rights beside Pro pricing",
            )
    checked += len(marketing_paths)

    pro = (INCLUDES / "usr/bin/dagric-upgrade-to-pro").read_text(encoding="utf-8")
    if "session_id=$SID" in pro:
        fail(errors, "dagric-upgrade-to-pro must not expose its bearer session in a URL or process arguments")
    if "Authorization: Bearer %s" not in pro or not re.search(r'PRO_ASSETS_SHA256="[0-9a-f]{64}"', pro):
        fail(errors, "dagric-upgrade-to-pro must authenticate privately and pin the Pro asset digest")
    checked += 1

    boot = (ROOT / "tools/boot-test.sh").read_text(encoding="utf-8")
    validation = boot.find('case "$MODE" in')
    deletion = boot.find('rm -rf "$OUT"')
    if validation < 0 or deletion < 0 or validation > deletion:
        fail(errors, "boot-test.sh must validate MODE before deriving and deleting its output path")
    if "mktemp -u" in boot:
        fail(errors, "boot-test.sh must not use a predictable, unreserved monitor socket")
    checked += 1

    migration = (INCLUDES / "usr/share/dagric/migrate-browser.py").read_text(encoding="utf-8")
    if "atexit.register(cleanup_private_temp_dirs)" not in migration:
        fail(errors, "migrate-browser.py must remove temporary copies of browser credential stores")
    if "os.fchmod(fd, 0o600)" not in migration:
        fail(errors, "migrate-browser.py must force browser-history and password outputs to mode 0600")
    checked += 1

    for relative in ("test/boot-test.ps1", "test/install-test.ps1"):
        harness = (ROOT / relative).read_text(encoding="utf-8")
        if "-p 127.0.0.1:6080:6080" not in harness:
            fail(errors, f"{relative} must bind the unauthenticated noVNC console to loopback")
        if "--privileged" in harness:
            fail(errors, f"{relative} must not run the long-lived VM container privileged")
        checked += 1
    for relative in ("test/enable-kvm.ps1", "test/enable-kvm.sh"):
        kvm_helper = (ROOT / relative).read_text(encoding="utf-8")
        if not re.search(r'alpine@sha256:[0-9a-f]{64}', kvm_helper):
            fail(errors, f"{relative} must pin its privileged helper image by digest")
        if "/lib/modules:/lib/modules:ro" not in kvm_helper:
            fail(errors, f"{relative} must mount host kernel modules read-only")
        if "--network=none" not in kvm_helper:
            fail(errors, f"{relative} privileged helper must have networking disabled")
        if re.search(r'(?<![:/])\balpine\b(?!@sha256:)', kvm_helper):
            fail(errors, f"{relative} must not run a floating Alpine image tag")
        if "/dev:/hostdev" in kvm_helper:
            fail(errors, f"{relative} must pass only /dev/kvm, not mount the host /dev tree")
        checked += 1

    vm_dockerfile = (ROOT / "test/Dockerfile").read_text(encoding="utf-8")
    if not re.search(r'^FROM\s+debian:trixie@sha256:[0-9a-f]{64}\s*$', vm_dockerfile, re.MULTILINE):
        fail(errors, "test/Dockerfile must pin its Debian base image by digest")
    if "vncdotool==1.3.0" not in vm_dockerfile:
        fail(errors, "test/Dockerfile must pin the vncdotool version")
    checked += 1

    return checked


def main() -> int:
    errors: list[str] = []
    counts = {
        "JSON documents": check_json(errors),
        "Python sources": check_python(errors),
        "Polkit policies": check_polkit(errors),
        "pinned action references": check_workflows(errors),
        "public copy files": check_public_copy(errors),
        "tracked paths": check_repository(errors),
        "repository text files secret-scanned": check_secret_material(errors),
        "dependency security pins": check_dependency_floor(errors),
        "security contracts": check_security_contracts(errors),
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
