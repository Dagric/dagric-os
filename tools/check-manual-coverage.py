#!/usr/bin/env python3
"""Prove that every visible Dagric OS launcher has an offline manual route."""

from __future__ import annotations

import argparse
import html
import re
import sys
from urllib.parse import unquote
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "config/includes.chroot/usr/share/dagric/manual"
MAP = MANUAL / "application-map.tsv"
SOURCE_DESKTOPS = ROOT / "config/includes.chroot/usr/share/applications"
AUDIT_DESKTOPS = (
    ROOT / "out/audit-desktop/free/usr/share/applications",
    ROOT / "out/audit-desktop/pro/usr/share/applications",
)


def read_map(path: Path) -> tuple[dict[str, str], list[str]]:
    routes: dict[str, str] = {}
    errors: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 2 or not all(fields):
            errors.append(f"{path}:{number}: expected DESKTOP<TAB>PAGE")
            continue
        desktop, page = fields
        if desktop in routes:
            errors.append(f"{path}:{number}: duplicate launcher {desktop}")
        routes[desktop] = page
    return routes, errors


def desktop_entry(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    in_entry = False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return values
    for raw in lines:
        line = raw.strip()
        if line == "[Desktop Entry]":
            in_entry = True
            continue
        if in_entry and line.startswith("["):
            break
        if not in_entry or not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if "[" not in key:
            values.setdefault(key, value.strip())
    return values


def is_visible_application(path: Path) -> bool:
    entry = desktop_entry(path)
    yes = {"1", "true", "yes"}
    return (
        entry.get("Type", "Application") == "Application"
        and entry.get("NoDisplay", "").lower() not in yes
        and entry.get("Hidden", "").lower() not in yes
    )


def check_group_counts(index: str) -> list[str]:
    """Keep the no-JavaScript sidebar honest before the image build hook runs."""
    errors: list[str] = []
    sidebar = dict(re.findall(
        r'data-goto="(g-[a-z]+)"[^>]*>.*?<span class="count">(\d+)</span>',
        index,
    ))
    sections = {
        name: len(re.findall(r'<a class="card"\s', body))
        for name, body in re.findall(
            r'<section\b[^>]*id="(g-[a-z]+)"[^>]*>(.*?)</section>',
            index,
            re.DOTALL,
        )
    }
    for name in sorted(sidebar.keys() | sections.keys()):
        if name not in sections:
            errors.append(f"manual sidebar {name}: section is missing")
        elif name not in sidebar:
            errors.append(f"manual section {name}: sidebar count is missing")
        elif int(sidebar[name]) != sections[name]:
            errors.append(
                f"manual sidebar {name}: says {sidebar[name]}; "
                f"section contains {sections[name]} cards"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--desktop-dir",
        action="append",
        type=Path,
        default=[],
        help="additional installed /usr/share/applications directory to audit",
    )
    args = parser.parse_args()

    if not MAP.is_file():
        print(f"ERROR: missing coverage map: {MAP}", file=sys.stderr)
        return 1

    routes, errors = read_map(MAP)
    index_path = MANUAL / "index.html"
    index = index_path.read_text(encoding="utf-8")
    errors.extend(check_group_counts(index))
    linked_pages = {html.unescape(href) for href in re.findall(r'href="([^"]+\.html)"', index)}

    page_names = {path.name for path in MANUAL.glob("*.html") if path.name != "index.html"}
    card_pages = {
        html.unescape(href)
        for href in re.findall(r'<a class="card" href="([^"]+\.html)"', index)
    }
    missing_cards = sorted(page_names - card_pages)
    dead_cards = sorted(card_pages - page_names)
    if missing_cards:
        errors.append("manual pages without index cards: " + ", ".join(missing_cards))
    if dead_cards:
        errors.append("index cards pointing at missing pages: " + ", ".join(dead_cards))

    static_count = re.search(r'id="count"[^>]*>(\d+) pages<', index)
    if not static_count or int(static_count.group(1)) != len(page_names):
        shown = static_count.group(1) if static_count else "missing"
        errors.append(f"static page counter says {shown}; manual contains {len(page_names)} pages")

    for page in sorted(MANUAL.glob("*.html")):
        page_text = page.read_text(encoding="utf-8")
        for raw_ref in re.findall(r'(?:href|src)="([^"]+)"', page_text):
            ref = html.unescape(raw_ref)
            if not ref or ref.startswith(("#", "http://", "https://", "mailto:", "data:")):
                continue
            target_name = unquote(ref.split("#", 1)[0])
            target = (page.parent / target_name).resolve()
            if not target.exists():
                errors.append(f"{page.name}: broken offline reference: {ref}")

    for desktop, page in sorted(routes.items()):
        target = MANUAL / page
        if not target.is_file():
            errors.append(f"{desktop}: mapped page does not exist: {page}")
        elif page not in linked_pages:
            errors.append(f"{desktop}: {page} is not linked from manual/index.html")

    directories = [SOURCE_DESKTOPS]
    directories.extend(path for path in AUDIT_DESKTOPS if path.is_dir())
    directories.extend(args.desktop_dir)
    audited = 0
    visible_names: set[str] = set()
    seen_dirs: set[Path] = set()
    for directory in directories:
        directory = directory.resolve()
        if directory in seen_dirs:
            continue
        seen_dirs.add(directory)
        if not directory.is_dir():
            errors.append(f"desktop directory does not exist: {directory}")
            continue
        visible = [path for path in directory.glob("*.desktop") if is_visible_application(path)]
        audited += len(visible)
        for path in visible:
            visible_names.add(path.name)
            if path.name not in routes:
                errors.append(f"{directory}: visible launcher has no manual route: {path.name}")

    if errors:
        print("manual-coverage: FAILED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "manual-coverage: OK — "
        f"{len(routes)} launcher routes, {len(set(routes.values()))} guide pages, "
        f"{audited} visible entries checked across {len(seen_dirs)} inventories "
        f"({len(visible_names)} unique launchers)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
