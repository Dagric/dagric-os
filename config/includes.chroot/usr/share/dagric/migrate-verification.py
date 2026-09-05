#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a migration verification artifact from migration copy events."""
import argparse
import csv
import datetime as dt
import html
import json
import os
import pathlib
import sys


def _bytes_human(num):
    units = [(1 << 40, "TB"), (1 << 30, "GB"), (1 << 20, "MB"), (1 << 10, "KB")]
    for scale, unit in units:
        if num >= scale:
            return f"{num / scale:.2f} {unit}"
    return f"{num} B"


def _read_events(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh, delimiter="\t"))


def _ensure_parent(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def build_html(report):
    rows = []
    rows.append('<!doctype html><meta charset="utf-8"><title>Dagric Migration Verification</title>')
    rows.append('<style>body{max-width:980px;margin:3rem auto;padding:0 1.5rem;font:16px system-ui;color:#e8edf5;background:#121821}section{background:#1c2633;padding:1rem 1.25rem;margin:1rem 0;border-radius:12px}li{margin:.55rem 0}table{width:100%;border-collapse:collapse}th,td{padding:.3rem .4rem;text-align:left;border-bottom:1px solid #29404f;font-size:.95rem}code{word-break:break-all}</style>')
    rows.append("<h1>Dagric Migration Verification</h1>")
    rows.append(f"<p>Windows profile: {html.escape(report['windows_user'])}<br>Windows device: {html.escape(report['windows_device'])}<br>Copy timestamp: {html.escape(report['created_utc'])}</p>")

    totals = report['totals']
    rows.append("<section><h2>Totals</h2>")
    rows.append("<ul>")
    rows.append(f"<li>Selected items: {totals['selected_categories']} ({', '.join(sorted(report['selection'])) if report['selection'] else 'none'})</li>")
    rows.append(f"<li>Candidate bytes estimated: {totals['estimated_bytes_human']}" )
    rows.append(f"<li>Copied files: {totals['files_transferred']}</li>")
    rows.append(f"<li>Copied bytes: {totals['bytes_transferred_human']}</li>")
    rows.append(f"<li>Copy operations: {totals['operations']}, failures: {totals['failed_operations']}</li>")
    rows.append(f"<li>Source read-write safety: {'Windows was read-only' if report['safety'].get('windows_read_only') else 'Check required'}</li>")
    rows.append("</ul></section>")

    rows.append("<section><h2>Per-source copy report</h2><table><thead><tr><th>Category</th><th>Source</th><th>Destination</th><th>Copied files</th><th>Copied bytes</th><th>Status</th></tr></thead><tbody>")
    for item in report['copies']:
        status = html.escape(item['status'])
        if item['status'] == "failed":
            status = f"<strong>{status}</strong>"
        rows.append("<tr>" +
                    f"<td>{html.escape(item['category'])}</td>" +
                    f"<td><code>{html.escape(item['source'])}</code></td>" +
                    f"<td><code>{html.escape(item['destination'])}</code></td>" +
                    f"<td>{item['files_transferred']}</td>" +
                    f"<td>{item['bytes_transferred_human']}</td>" +
                    f"<td>{status}</td>" +
                    "</tr>")
    rows.append("</tbody></table></section>")

    notes = report.get('notes') or []
    if notes:
        rows.append('<section><h2>Verification notes</h2><ul>')
        rows.extend(f"<li>{html.escape(note)}</li>" for note in notes)
        rows.append("</ul></section>")

    checksum = report.get('checksums') or {}
    if checksum.get('enabled'):
        rows.append('<section><h2>Checksums</h2>')
        rows.append(f"<p>Checked {checksum['count']} files into {html.escape(checksum['manifest'])}.")
        if checksum.get('truncated'):
            rows.append("<p>Note: manifest was limited to the largest practical set.</p>")
        rows.append('</section>')

    if report.get('companion'):
        rows.append('<section><h2>Windows companion bundle</h2>')
        rows.append(f"<p>Included: {html.escape(report['companion'].get('path', ''))} from format {html.escape(str(report['companion'].get('format', 'unknown')))}</p>")
        rows.append('</section>')

    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('events_file')
    parser.add_argument('home_dir')
    parser.add_argument('windows_user')
    parser.add_argument('windows_device')
    parser.add_argument('windows_mount')
    parser.add_argument('choices')
    parser.add_argument('verification_json')
    parser.add_argument('verification_html')
    parser.add_argument('--checksum-file', default='')
    parser.add_argument('--companion', default='')
    args = parser.parse_args()

    events = _read_events(args.events_file)
    if args.checksum_file:
        _ensure_parent(args.checksum_file)
        with open(args.checksum_file, 'w', encoding='utf-8') as fh:
            fh.write('')

    copies = []
    copied_files = 0
    copied_bytes = 0
    ops = 0
    failed_ops = 0
    errors = 0
    notes = []
    checksums = []

    for row in events:
        if not row:
            continue
        kind = row[0]
        if kind == 'copy':
            if len(row) < 7:
                continue
            _, category, src, dst, files, bytes, status, failure_lines = row[:8]
            files_n = int(files or 0)
            bytes_n = int(bytes or 0)
            copied_files += files_n
            copied_bytes += bytes_n
            ops += 1
            if status == 'failed':
                failed_ops += 1
            if failure_lines:
                errors += 1
                notes.append(f"{category}: {failure_lines}")
            copies.append({
                'category': category,
                'source': src,
                'destination': dst,
                'files_transferred': files_n,
                'bytes_transferred': bytes_n,
                'bytes_transferred_human': _bytes_human(bytes_n),
                'status': status,
            })
        elif kind == 'checksum':
            if len(row) >= 4:
                _ignore, path, sha, src = row[:4]
                checksums.append({'path': path, 'sha256': sha, 'source': src})

    selection = [item for item in args.choices.split(' ') if item]

    report = {
        'format': 'dagric-migration-verification',
        'version': 1,
        'created_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'windows_user': args.windows_user,
        'windows_device': args.windows_device,
        'windows_mount': args.windows_mount,
        'home_dir': args.home_dir,
        'selection': selection,
        'safety': {
            'windows_read_only': True,
            'existing_files_untouched': True,
        },
        'copies': copies,
        'totals': {
            'selected_categories': len(selection),
            'operations': ops,
            'failed_operations': failed_ops,
            'files_transferred': copied_files,
            'bytes_transferred': copied_bytes,
            'bytes_transferred_human': _bytes_human(copied_bytes),
            'estimated_bytes_human': _bytes_human(sum(item['bytes_transferred'] for item in copies)),
        },
        'checksums': {
            'enabled': bool(checksums),
            'count': len(checksums),
            'manifest': args.checksum_file,
            'truncated': False,
        },
        'notes': notes[:20],
    }

    if args.companion:
        report['companion'] = {'path': args.companion, 'format': os.path.splitext(args.companion)[1].strip('.') or 'json'}

    # Write artifacts
    for path, content in ((args.verification_json, json.dumps(report, indent=2)), (args.verification_html, build_html(report))):
        _ensure_parent(path)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
            fh.write("\n")

    print("VERIFICATION_JSON=%s" % args.verification_json)
    print("VERIFICATION_HTML=%s" % args.verification_html)


if __name__ == '__main__':
    main()
