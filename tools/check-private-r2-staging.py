#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prove a dedicated R2 candidate bucket has no public access path."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


LIVE_BUCKETS = {"dagric-downloads", "dagric-pro"}
NAME_RE = re.compile(r"[a-z0-9][a-z0-9.-]{1,62}[a-z0-9]")


class StagingError(ValueError):
    """The candidate bucket identity or privacy state is unsafe/unknown."""


def api_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise StagingError("Cloudflare privacy API request failed") from exc
    if not isinstance(value, dict) or value.get("success") is not True:
        raise StagingError("Cloudflare privacy API did not return success")
    result = value.get("result")
    if not isinstance(result, dict):
        raise StagingError("Cloudflare privacy API response has no result object")
    return result


def validate_states(
    managed: dict[str, object],
    custom: dict[str, object],
    *,
    require_no_custom_domains: bool = True,
) -> None:
    if managed.get("enabled") is not False:
        raise StagingError("candidate bucket r2.dev public access is not disabled")
    domains = custom.get("domains")
    if not isinstance(domains, list):
        raise StagingError("candidate bucket custom-domain inventory is missing")
    if require_no_custom_domains and domains:
        raise StagingError("candidate bucket must have no custom domains attached")
    if not require_no_custom_domains:
        for record in domains:
            if not isinstance(record, dict) or record.get("enabled") is not False:
                raise StagingError("live Free bucket still has an enabled custom domain")


def check(account: str, bucket: str, token: str, *, live_hold: bool = False) -> None:
    if not re.fullmatch(r"[0-9a-f]{32}", account):
        raise StagingError("R2 account ID must be 32 lowercase hexadecimal characters")
    if not NAME_RE.fullmatch(bucket):
        raise StagingError("candidate staging bucket name is invalid")
    if live_hold and bucket != "dagric-downloads":
        raise StagingError("live-hold API check is limited to dagric-downloads")
    if not live_hold and bucket in LIVE_BUCKETS:
        raise StagingError("candidate staging bucket must differ from both live buckets")
    if not token:
        raise StagingError("CLOUDFLARE_R2_AUDIT_TOKEN is required")

    account_part = urllib.parse.quote(account, safe="")
    bucket_part = urllib.parse.quote(bucket, safe="")
    base = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_part}/r2/buckets/{bucket_part}/domains"
    )
    managed = api_json(base + "/managed", token)
    custom = api_json(base + "/custom", token)
    validate_states(managed, custom, require_no_custom_domains=not live_hold)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument(
        "--live-hold",
        action="store_true",
        help="prove all direct public access to the live Free bucket is disabled",
    )
    parser.add_argument(
        "--token-env", default="CLOUDFLARE_R2_AUDIT_TOKEN", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    try:
        check(
            args.account,
            args.bucket,
            os.environ.get(args.token_env, ""),
            live_hold=args.live_hold,
        )
    except StagingError as exc:
        print(f"r2-staging: BLOCKED: {exc}", file=sys.stderr)
        return 1
    if args.live_hold:
        print("r2-staging: live Free bucket has no enabled public domain")
    else:
        print(
            "r2-staging: dedicated candidate bucket exists with r2.dev disabled "
            "and no custom domains"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
