#!/bin/sh
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# Dagric OS — cut a release without publishing a checksum for a file nobody can
# download.
#
# WHY THIS EXISTS, AND WHAT IT IS REPLACING.
#
# On 2026-08-05 the live site published
#   533126a5baff2fd7ae2f17f400da0bc8891bf04089a64f8dd8df78c8f1a7e270
# for dagric-os-1.0-amd64.iso, and the file R2 actually served hashed to
#   dabdc0b395fcfaade4c4705ce2be343f366b709572e1f8d1bbdbccd93c220261
# Both verified twice, the second time with a byte count equal to R2's own
# Content-Length so a truncated stream could not have faked it.
#
# download.html tells every customer to run
#     gpg --verify SHA256SUMS.sig SHA256SUMS
#     sha256sum -c SHA256SUMS
# so following the published instructions printed FAILED. On a distribution
# sold on privacy and verifiability, that does not read as "stale metadata", it
# reads as a tampered download.
#
# Nothing was broken in the tooling. tools/verify-published.sh already downloads
# the real ISO and compares it against the signed hash — it would have caught
# this in one run. It was simply never run: the only references to it anywhere
# in the tree are inside its own header comment. release.ps1 ends by PRINTING
# "Publish the ISOs together with SHA256SUMS so buyers can verify", which is a
# reminder, and a reminder is not a mechanism. The checksums were regenerated
# 2026-07-28 and the ISO was replaced on R2 2026-08-02, and nothing connected
# the two events.
#
# So this script makes the order structural instead of remembered:
#
#     sign      hash the local ISOs and sign the manifest      (always safe)
#     stage     copy only to an isolated candidate prefix      (GATED)
#     promote   copy the signed candidate to live R2 keys      (GATED)
#     publish   copy the manifest into site/ and deploy        (GATED)
#
# `publish` refuses to run unless the bytes R2 is serving RIGHT NOW already hash
# to the value about to be published. Upload first, publish second — and if you
# get it the wrong way round, this stops you instead of your customers finding
# out.
#
# R2 credentials remain environment-only. `tools/upload-to-r2.sh` can write
# only an isolated candidate prefix; `tools/promote-r2-release.sh` is the sole
# audited path from that prefix to the customer-facing keys.
set -e

cd "$(dirname "$0")/.."
OUT=out
SITE=site
KEYID=6CE37402BA0A0EF8
KEY_FINGERPRINT=3A079F85DE74375DD65557096CE37402BA0A0EF8
MODE=${1:-}

usage() {
    cat >&2 <<'EOF'
usage: sh tools/release.sh sign      hash out/*.iso and sign out/SHA256SUMS
       sh tools/release.sh gate      re-run gate and refresh authorization only
       sh tools/release.sh physical  validate candidate-bound physical evidence
       sh tools/release.sh publish   verify R2 matches, then copy into site/
       sh tools/release.sh check     verify only, change nothing

Commercial sign/publish also require DAGRIC_RELEASE_TAG and the protected
COMMERCIAL_RELEASE_APPROVAL_JSON human legal/trademark attestation. Live
promotion and publication additionally require PHYSICAL_RELEASE_EVIDENCE_JSON.
Between
sign and publish, stage with tools/upload-to-r2.sh and then run the separate,
explicit tools/promote-r2-release.sh command. The staging helper cannot write
customer-facing R2 keys.
EOF
    exit 2
}

# ---------------------------------------------------------------------------
list_isos() {
    # Named ISOs only. live-image-amd64.hybrid.iso is live-build's own output
    # name and is the same filename for both editions, which is how a free
    # image once got overwritten by a Pro one carrying the free name.
    find "$OUT" -maxdepth 1 -name 'dagric-os-*-amd64.iso' -type f 2>/dev/null | sort
}

# THE MANIFEST MUST COVER EVERY EDITION THE SITE ACTUALLY OFFERS.
#
# do_sign hashes whatever dagric-os-*-amd64.iso happens to be in out/ at that
# moment, and nothing downstream noticed if one was missing. That is not
# theoretical: during tonight's rebuild the Pro image sat in out/prev/ while the
# free one was in out/, and `sign` at that instant would have written a one-line
# manifest — then `publish` would have dropped the Pro line out of
# site/SHA256SUMS entirely.
#
# /download links the free image directly and streams Pro through the gate
# worker, and tells buyers of BOTH to run `sha256sum -c SHA256SUMS`. An ISO
# absent from the file customers are told to verify against is indistinguishable
# from an unofficial build. Sign after the LAST build; this enforces it rather
# than asking.
PRODUCT_VERSION=$(python3 -c \
    'import json; print(json.load(open("site/manifest/release.json"))["version"])')
PRODUCT_VERSION_RE=$(printf '%s' "$PRODUCT_VERSION" | sed 's/[.]/\\./g')
REQUIRED_ISOS="dagric-os-$PRODUCT_VERSION-amd64.iso dagric-os-pro-$PRODUCT_VERSION-amd64.iso"

require_all_editions() {
    _m=$1
    _missing=
    for _want in $REQUIRED_ISOS; do
        awk -v n="$_want" '$2==n{f=1} END{exit !f}' "$_m" || _missing="$_missing $_want"
    done
    [ -z "$_missing" ] && return 0
    echo "release: the manifest does not cover every ISO the site offers." >&2
    for _w in $_missing; do echo "  missing: $_w" >&2; done
    echo "  Build that edition, or move it back into $OUT/, and re-run 'sign'." >&2
    return 1
}

# Build/source/legal gate shared by the last safe point before upload (`sign`)
# and the last safe point before site promotion (`publish`). It reads the
# package inventory from each immutable ISO rather than trusting package-list
# source, then binds both artifacts to the tag, exact source map and a qualified
# human review of the Firefox configuration or verified absence and game artwork.
commercial_gate() {
    [ -n "${DAGRIC_RELEASE_TAG:-}" ] || {
        echo "release: DAGRIC_RELEASE_TAG is required for a commercial release." >&2
        return 1
    }
    [ -n "${COMMERCIAL_RELEASE_APPROVAL_JSON:-}" ] || {
        echo "release: COMMERCIAL_RELEASE_APPROVAL_JSON is required." >&2
        echo "         A qualified human legal/trademark reviewer must approve" >&2
        echo "         this exact commit; an AI or engineering note is not approval." >&2
        return 1
    }
    command -v xorriso >/dev/null 2>&1 || {
        echo "release: xorriso is required to inspect candidate package manifests." >&2
        return 1
    }
    _record_commit=$(git rev-parse HEAD 2>/dev/null) || {
        echo "release: cannot determine the release-record Git commit." >&2
        return 1
    }
    _tag_commit=$(git rev-parse "refs/tags/$DAGRIC_RELEASE_TAG^{commit}" 2>/dev/null) || {
        echo "release: $DAGRIC_RELEASE_TAG is not an existing release tag." >&2
        return 1
    }
    [ "$_tag_commit" = "$_record_commit" ] || {
        echo "release: $DAGRIC_RELEASE_TAG does not point at record $_record_commit." >&2
        return 1
    }
    [ -z "$(git status --porcelain --untracked-files=all)" ] || {
        echo "release: commercial candidate checkout is dirty." >&2
        return 1
    }
    _commit=$(python3 -c \
        'import json; print(json.load(open("site/manifest/release.json"))["source"]["commit"])')
    git cat-file -e "$_commit^{commit}" 2>/dev/null || {
        echo "release: recorded build-source commit does not exist locally." >&2
        return 1
    }
    git merge-base --is-ancestor "$_commit" "$_record_commit" || {
        echo "release: build-source commit is not an ancestor of the release tag." >&2
        return 1
    }
    _bad_delta=$(git diff --name-only "$_commit..$_record_commit" | \
        grep -Ev '^(site/manifest/(release\.json|source-index-[0-9.]+\.json|dagric-os(-pro)?-[0-9.]+\.packages)|docs/RELEASE-[A-Za-z0-9._-]+\.md)$' || true)
    if [ -n "$_bad_delta" ]; then
        echo "release: release-record commit changes build-affecting files:" >&2
        printf '%s\n' "$_bad_delta" >&2
        return 1
    fi

    # Development and quality jobs may report partial translations, but the
    # commercial artifact must not advertise a locale whose catalog silently
    # falls back to English for fuzzy or untranslated messages.
    python3 tools/check-release-locales.py || return 1

    _gate_dir="$OUT/release-gate"
    mkdir -p "$_gate_dir"
    rm -f "$_gate_dir/COMMERCIAL-RELEASE-AUTHORIZATION.json"
    for _edition in free pro; do
        case "$_edition" in
            free)
                _iso="$OUT/dagric-os-$PRODUCT_VERSION-amd64.iso"
                _manifest="$_gate_dir/dagric-os-$PRODUCT_VERSION.packages"
                ;;
            pro)
                _iso="$OUT/dagric-os-pro-$PRODUCT_VERSION-amd64.iso"
                _manifest="$_gate_dir/dagric-os-pro-$PRODUCT_VERSION.packages"
                ;;
        esac
        [ -f "$_iso" ] || { echo "release: missing $_iso" >&2; return 1; }
        rm -f "$_manifest"
        xorriso -osirrox on -indev "$_iso" \
            -extract /live/filesystem.packages "$_manifest" >/dev/null 2>&1 || {
            echo "release: cannot extract filesystem.packages from $_iso" >&2
            return 1
        }
        _provenance="$OUT/SOURCE_COMMIT-$_edition"
        [ -f "$_provenance" ] || _provenance="$OUT/SOURCE_COMMIT"
        [ -f "$_provenance" ] || {
            echo "release: missing source provenance for $_edition" >&2
            return 1
        }
        python3 tools/check-commercial-release.py edition \
            --edition "$_edition" \
            --iso "$_iso" \
            --package-manifest "$_manifest" \
            --package-sections "$OUT/PACKAGE_SECTIONS-$_edition.tsv" \
            --provenance "$_provenance" \
            --checksums "$OUT/SHA256SUMS" \
            --candidate-commit "$_commit" \
            --release-tag "$DAGRIC_RELEASE_TAG" || return 1
    done

    _free_provenance="$OUT/SOURCE_COMMIT-free"
    [ -f "$_free_provenance" ] || _free_provenance="$OUT/SOURCE_COMMIT"
    _pro_provenance="$OUT/SOURCE_COMMIT-pro"
    [ -f "$_pro_provenance" ] || _pro_provenance="$OUT/SOURCE_COMMIT"
    python3 tools/check-commercial-release.py promotion \
        --checksums "$OUT/SHA256SUMS" \
        --free-manifest "$_gate_dir/dagric-os-$PRODUCT_VERSION.packages" \
        --pro-manifest "$_gate_dir/dagric-os-pro-$PRODUCT_VERSION.packages" \
        --free-package-sections "$OUT/PACKAGE_SECTIONS-free.tsv" \
        --pro-package-sections "$OUT/PACKAGE_SECTIONS-pro.tsv" \
        --free-iso "$OUT/dagric-os-$PRODUCT_VERSION-amd64.iso" \
        --pro-iso "$OUT/dagric-os-pro-$PRODUCT_VERSION-amd64.iso" \
        --free-provenance "$_free_provenance" \
        --pro-provenance "$_pro_provenance" \
        --candidate-commit "$_commit" \
        --release-tag "$DAGRIC_RELEASE_TAG" \
        --authorization-output \
            "$_gate_dir/COMMERCIAL-RELEASE-AUTHORIZATION.json" || return 1
}

physical_gate() {
    [ -n "${DAGRIC_RELEASE_TAG:-}" ] || {
        echo "release: DAGRIC_RELEASE_TAG is required for physical qualification." >&2
        return 1
    }
    [ -n "${PHYSICAL_RELEASE_EVIDENCE_JSON:-}" ] || {
        echo "release: PHYSICAL_RELEASE_EVIDENCE_JSON is required before live promotion." >&2
        echo "         VM evidence cannot substitute for physical qualification." >&2
        return 1
    }
    _commit=$(python3 -c \
        'import json; print(json.load(open("site/manifest/release.json"))["source"]["commit"])')
    _physical_output=$(python3 tools/check-physical-release.py check \
        --candidate-commit "$_commit" \
        --release-tag "$DAGRIC_RELEASE_TAG") || return 1
    printf '%s\n' "$_physical_output"
    _physical_digest=$(printf '%s\n' "$_physical_output" | \
        sed -n 's/.*evidence=\([0-9a-f]\{64\}\).*/\1/p')
    [ -n "$_physical_digest" ] || {
        echo "release: physical evidence gate returned no digest." >&2
        return 1
    }
    mkdir -p "$OUT/release-gate"
    printf '%s  PHYSICAL_RELEASE_EVIDENCE_JSON\n' "$_physical_digest" \
        > "$OUT/release-gate/PHYSICAL-RELEASE-EVIDENCE.sha256"
}

do_sign() {
    _isos=$(list_isos)
    [ -n "$_isos" ] || { echo "release: no out/dagric-os-*-amd64.iso — build first" >&2; exit 1; }

    # A receipt authorizes only the exact already-promoted checksum/signature
    # pair. Starting a new signing pass revokes any previous local receipt.
    rm -f "$OUT/release-gate/R2-LIVE-PROMOTION.json"

    : > "$OUT/SHA256SUMS.tmp"
    for _i in $_isos; do
        printf '  hashing %s\n' "$(basename "$_i")" >&2
        # Two spaces: the format `sha256sum -c` expects. One space is the
        # "text mode" form and older coreutils reject the file outright.
        printf '%s  %s\n' "$(sha256sum "$_i" | cut -d' ' -f1)" "$(basename "$_i")" \
            >> "$OUT/SHA256SUMS.tmp"
    done
    mv "$OUT/SHA256SUMS.tmp" "$OUT/SHA256SUMS"

    # Prove the manifest verifies against the files it was just made from,
    # before it is signed. A manifest that cannot pass its own check locally
    # will not start passing once a signature is wrapped around it.
    ( cd "$OUT" && sha256sum -c SHA256SUMS >/dev/null ) || {
        echo "release: the manifest does not verify against its own files" >&2; exit 1; }

    require_all_editions "$OUT/SHA256SUMS" || exit 1

    # No upload instruction is printed unless the built artifacts, exact source
    # map and human legal/trademark attestation all match this candidate.
    commercial_gate || exit 1

    rm -f "$OUT/SHA256SUMS.sig"
    gpg --batch --yes --local-user "$KEYID" \
        --output "$OUT/SHA256SUMS.sig" --detach-sign "$OUT/SHA256SUMS"
    gpg --batch --verify "$OUT/SHA256SUMS.sig" "$OUT/SHA256SUMS" 2>/dev/null || {
        echo "release: the signature does not verify — refusing to continue" >&2; exit 1; }

    echo
    sed 's/^/  /' "$OUT/SHA256SUMS"
    echo
    echo "  signed with $KEYID"
    echo
    echo "  NEXT: stage both ISOs, SHA256SUMS, SHA256SUMS.sig and"
    echo "        out/release-gate/COMMERCIAL-RELEASE-AUTHORIZATION.json with"
    echo "        sh tools/upload-to-r2.sh <file>"
    echo "  Then, after reviewing the exact tag and authorization record, run"
    echo "        DAGRIC_PROMOTE_TO_LIVE=YES sh tools/promote-r2-release.sh"
    echo "        sh tools/release.sh publish"
    echo "  Staging cannot replace live downloads; promotion is explicit and signature-last."
}

do_gate() {
    [ -f "$OUT/SHA256SUMS" ] || {
        echo "release: no $OUT/SHA256SUMS — run 'sign' first" >&2
        exit 1
    }
    require_all_editions "$OUT/SHA256SUMS" || exit 1
    commercial_gate || exit 1
    echo "release: commercial candidate gate passed; authorization refreshed at"
    echo "         $OUT/release-gate/COMMERCIAL-RELEASE-AUTHORIZATION.json"
}

# ---------------------------------------------------------------------------
# The gate. Compares the hash about to be published against the bytes a
# customer would actually receive, for every ISO that is publicly reachable.
#
# Pro is intentionally exempt: it streams from a PRIVATE bucket through
# infra/gate-worker.js and returns 404 on the public r2.dev host by design.
# There is no unauthenticated way to fetch it, so there is nothing to compare;
# that is stated rather than silently skipped.
check_live() {
    _sums=$1
    _url_base=$(grep -oE "https://[^\"]*/dagric-os-$PRODUCT_VERSION_RE-amd64\.iso" "$SITE/download.html" \
                | head -1 | sed "s|/dagric-os-$PRODUCT_VERSION-amd64.iso$||")
    [ -n "$_url_base" ] || { echo "release: no ISO URL in $SITE/download.html" >&2; exit 1; }

    _bad=0
    _checked=0
    while read -r _hash _name; do
        [ -n "$_name" ] || continue
        case "$_name" in
            *-pro-*)
                echo "  $_name"
                echo "    skipped: served from the private bucket via the gate worker,"
                echo "    not publicly fetchable, so it cannot be checked from here."
                continue ;;
        esac

        _checked=$((_checked + 1))
        _u="$_url_base/$_name"
        printf '  %s\n' "$_name"
        printf '    fetching %s\n' "$_u"

        _len=$(curl -fsSI "$_u" 2>/dev/null | tr -d '\r' \
               | awk 'tolower($1)=="content-length:"{print $2}' | tail -1)
        if [ -z "$_len" ]; then
            echo "    NOT REACHABLE — nothing is being served at that URL." >&2
            _bad=1; continue
        fi

        # Count the bytes as well as hashing them. A truncated transfer
        # produces a wrong hash that looks exactly like a real mismatch, and
        # that false alarm is worth more than one extra pipe.
        _tmp=$(mktemp) || exit 1
        _got=$(curl -fsS "$_u" 2>/dev/null | tee "$_tmp" | wc -c | tr -d ' ')
        _live=$(sha256sum "$_tmp" | cut -d' ' -f1)
        rm -f "$_tmp"

        if [ "$_got" != "$_len" ]; then
            echo "    TRANSFER INCOMPLETE — $_got of $_len bytes; result unusable." >&2
            _bad=1; continue
        fi
        if [ "$_live" = "$_hash" ]; then
            echo "    MATCHES the signed manifest ($_got bytes)"
        else
            echo "    MISMATCH" >&2
            echo "      manifest says: $_hash" >&2
            echo "      R2 serves:     $_live" >&2
            echo "      A customer running the command printed on /download would" >&2
            echo "      see FAILED. Upload the built ISO, then publish." >&2
            _bad=1
        fi
    done < "$_sums"
    # A GATE THAT SKIPPED EVERY LINE IS NOT A GATE THAT PASSED. The loop body is
    # the only thing that can set _bad, and Pro lines `continue` past it, so a
    # manifest containing nothing publicly fetchable returned 0 having compared
    # zero bytes — and then printed that everything matched. That is precisely
    # the defect class this whole script was written to stop, reproduced inside
    # it. `done < "$_sums"` is a redirect and not a pipe, so the loop runs in
    # this shell and _checked survives, the same reason _bad already works.
    if [ "$_checked" -eq 0 ]; then
        echo "    NOTHING WAS CHECKED — the manifest holds no publicly" >&2
        echo "    fetchable ISO, so this compared nothing. Refusing to call" >&2
        echo "    that a pass." >&2
        return 1
    fi
    return $_bad
}

# ---------------------------------------------------------------------------
# THERE ARE TWO PUBLICLY REACHABLE MANIFESTS AND THEY CAN DISAGREE.
#
# This is what actually went wrong on 2026-08-02, and it is not what
# verify-published.sh reported. That tool said "the image was copied to the
# bucket and SHA256SUMS + .sig were not". Checked against the bucket with real
# credentials, the opposite is true: R2 holds dagric-os-1.0-amd64.iso at
# 23:08:36 and SHA256SUMS and SHA256SUMS.sig at 23:09:17-18, one minute later.
# The bucket side of that release was done correctly and completely.
#
# What never happened was the SITE redeploy. download.html links SHA256SUMS
# RELATIVELY, so a customer fetches dagric.com/SHA256SUMS — the copy in site/,
# which still carried the 2026-07-28 hashes. R2's copy has been correct the
# whole time and nothing points at it.
#
# So the release has three artefacts, not two, and the third is invisible:
#   1. the ISOs on R2
#   2. SHA256SUMS + .sig ON R2, publicly readable beside them
#   3. SHA256SUMS + .sig on the site, which is the pair customers actually use
# The site deliberately deleted its inline #sha256sums block because two copies
# of a checksum drift and the drifting one is always the one the customer reads.
# That reasoning applies to this pair too, and nothing was enforcing it.
#
# Needs no credentials: the bucket is public, so the manifest beside the ISO can
# just be fetched.
check_r2_manifest() {
    _sums=$1
    _base=$2
    _r2m=$(curl -fsS "$_base/SHA256SUMS" 2>/dev/null) || {
        echo "  no SHA256SUMS beside the ISO on R2 — nothing to disagree with"
        return 0
    }
    if [ "$_r2m" = "$(cat "$_sums")" ]; then
        echo "  the manifest beside the ISO on R2 is identical"
        return 0
    fi
    echo "  THE TWO PUBLISHED MANIFESTS DISAGREE." >&2
    echo "    about to publish to the site:" >&2
    sed 's/^/      /' "$_sums" >&2
    echo "    already sitting beside the ISO on R2:" >&2
    printf '%s\n' "$_r2m" | sed 's/^/      /' >&2
    echo "    Upload this manifest to the bucket as well, so the copy next to" >&2
    echo "    the download agrees with the copy customers are sent to." >&2
    return 1
}

# THE SIGNATURE THIS SCRIPT SHIPS WAS NEVER CHECKED BEFORE IT SHIPPED IT.
#
# do_sign verifies the detached signature it has just made, which proves the key
# works and proves nothing about the pair `publish` copies into site/ minutes or
# days later. Between the two, the ordinary thing happens: someone rebuilds. The
# build even says so —
#
#   NOTE: out/SHA256SUMS has changed. Before deploying the site, copy it to
#         site/ and RE-SIGN it — site/SHA256SUMS.sig covers the previous
#         contents and will fail gpg --verify until it is regenerated.
#
# — and that note is the only thing standing between a rebuild and a site whose
# published signature covers a manifest that no longer exists. Every other
# failure this script guards is loud: a hash mismatch prints FAILED. A stale
# signature is quieter and worse, because `sha256sum -c SHA256SUMS` still passes
# and only the customers who follow the security advice — the ones who most
# need to trust the answer — see BAD signature. On a distribution that asks
# people to verify before booting, that is the one check that must not be a note
# in a build log.
#
# The fingerprint is compared, not just the exit status. `gpg --verify` returns 0
# for a good signature from ANY key in the keyring, so on a machine that has ever
# imported someone else's key it answers a question nobody asked.
check_signature() {
    _sums=$1
    _sig=$_sums.sig
    if [ ! -f "$_sig" ]; then
        echo "  NO SIGNATURE at $_sig — /download tells buyers to run" >&2
        echo "  'gpg --verify SHA256SUMS.sig SHA256SUMS'. Run 'sign' first." >&2
        return 1
    fi
    # `find -newer` and not `test -ot`: -ot is a widely-implemented extension,
    # not POSIX, and this tree is /bin/sh throughout.
    if [ -n "$(find "$_sums" -newer "$_sig" 2>/dev/null)" ]; then
        echo "  THE SIGNATURE IS OLDER THAN THE MANIFEST — something rebuilt or" >&2
        echo "  regenerated $_sums after it was signed. Re-run 'sign'." >&2
        return 1
    fi
    _st=$(mktemp) || return 1
    if ! gpg --batch --status-fd 3 --verify "$_sig" "$_sums" 3>"$_st" >/dev/null 2>&1; then
        rm -f "$_st"
        echo "  THE SIGNATURE DOES NOT VERIFY against $_sums." >&2
        echo "  Every buyer who follows the verification instructions on" >&2
        echo "  /download would see BAD signature. Re-run 'sign'." >&2
        return 1
    fi
    _fpr=$(awk '$2=="VALIDSIG"{print $3}' "$_st"); rm -f "$_st"
    case "$_fpr" in
        "$KEY_FINGERPRINT") echo "  signature verifies, made by $KEY_FINGERPRINT" ;;
        "")  echo "  gpg reported no VALIDSIG — refusing to treat that as a pass." >&2
             return 1 ;;
        *)   echo "  SIGNED BY THE WRONG KEY." >&2
             echo "    expected exact fingerprint $KEY_FINGERPRINT" >&2
             echo "    got $_fpr" >&2
             echo "  The published key on /download is $KEYID; a manifest signed" >&2
             echo "  by anything else cannot be verified by a customer." >&2
             return 1 ;;
    esac
    return 0
}

do_check() {
    _src=$OUT/SHA256SUMS
    [ -f "$_src" ] || { echo "release: no $_src — run 'sign' first" >&2; exit 1; }
    require_all_editions "$_src" || exit 1
    echo "Checking the signature on the manifest about to be published."
    _ok=0
    check_signature "$_src" || _ok=1
    echo
    echo "Comparing the manifest against the bytes R2 is serving right now."
    echo
    check_live "$_src" || _ok=1
    echo
    # Both checks always run. Reporting only the first failure would hide the
    # second, and on 2026-08-02 the second one was the whole story.
    _url_base=$(grep -oE "https://[^\"]*/dagric-os-$PRODUCT_VERSION_RE-amd64\.iso" "$SITE/download.html" \
                | head -1 | sed "s|/dagric-os-$PRODUCT_VERSION-amd64.iso$||")
    check_r2_manifest "$_src" "$_url_base" || _ok=1
    echo
    if [ "$_ok" -eq 0 ]; then
        echo "  the signature is current and made by the published key, every"
        echo "  publicly served ISO matches the manifest, and both published"
        echo "  copies of the manifest agree"
        return 0
    fi
    echo "  DO NOT PUBLISH until the uploads match." >&2
    return 1
}

require_promotion_receipt() {
    _receipt="$OUT/release-gate/R2-LIVE-PROMOTION.json"
    [ -f "$_receipt" ] || {
        echo "release: no verified live-promotion receipt." >&2
        echo "         Run tools/promote-r2-release.sh after offline signing." >&2
        return 1
    }
    RECEIPT="$_receipt" RELEASE_TAG="$DAGRIC_RELEASE_TAG" \
        PRODUCT_VERSION="$PRODUCT_VERSION" python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fail(message):
    raise SystemExit("release: invalid live-promotion receipt: " + message)

try:
    receipt = json.loads(Path(os.environ["RECEIPT"]).read_text(encoding="utf-8"))
    release = json.loads(Path("site/manifest/release.json").read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    fail(str(exc))

if receipt.get("schema") != "dagric-r2-live-promotion-v1":
    fail("wrong schema")
if receipt.get("release_tag") != os.environ["RELEASE_TAG"]:
    fail("wrong release tag")
if receipt.get("candidate_commit") != release.get("source", {}).get("commit"):
    fail("wrong build-source commit")
if receipt.get("authorization_sha256") != digest(
    "out/release-gate/COMMERCIAL-RELEASE-AUTHORIZATION.json"
):
    fail("commercial authorization changed after promotion")
physical_record = Path("out/release-gate/PHYSICAL-RELEASE-EVIDENCE.sha256")
if not physical_record.is_file():
    fail("physical evidence digest is missing")
physical_digest = physical_record.read_text(encoding="utf-8").split()[0]
if receipt.get("physical_evidence_sha256") != physical_digest:
    fail("physical evidence changed after promotion")
if receipt.get("checksums_sha256") != digest("out/SHA256SUMS"):
    fail("SHA256SUMS changed after promotion")
if receipt.get("signature_sha256") != digest("out/SHA256SUMS.sig"):
    fail("signature changed after promotion")

checksums = {}
for line in Path("out/SHA256SUMS").read_text(encoding="utf-8").splitlines():
    parts = line.split()
    if len(parts) != 2:
        fail("malformed SHA256SUMS")
    checksums[parts[1].lstrip("*")] = parts[0]
version = os.environ["PRODUCT_VERSION"]
for edition, filename in (
    ("free", f"dagric-os-{version}-amd64.iso"),
    ("pro", f"dagric-os-pro-{version}-amd64.iso"),
):
    record = receipt.get("artifacts", {}).get(edition, {})
    if record.get("filename") != filename or record.get("sha256") != checksums.get(filename):
        fail(f"{edition} artifact identity changed after promotion")
PY
}

do_publish() {
    [ -f "$OUT/SHA256SUMS" ] && [ -f "$OUT/SHA256SUMS.sig" ] \
        || { echo "release: run 'sign' first" >&2; exit 1; }
    # Live delivery remains disabled during fixed-key replacement and metadata
    # publication, so an unauthenticated fetch cannot be the pre-publish proof.
    # Verify the local signature now; the promotion receipt below is the
    # authenticated readback proof for both held live objects.
    check_signature "$OUT/SHA256SUMS" || exit 1
    # Re-run after the human upload and before changing site/ or promoting a
    # release. This catches a replaced local ISO, stale source map, changed art
    # or revoked/mismatched per-candidate approval.
    commercial_gate || exit 1
    physical_gate || exit 1
    # `publish` cannot be used as an alternate promotion path. The receipt is
    # written only after the dedicated helper has read back both live ISOs and
    # the signature, and it is bound to the authorization just reproduced.
    require_promotion_receipt || exit 1
    sh tools/check-release-hold.sh || exit 1

    cp "$OUT/SHA256SUMS" "$OUT/SHA256SUMS.sig" "$SITE/"
    echo
    echo "  copied SHA256SUMS and SHA256SUMS.sig into $SITE/"

    # PUBLISH WHAT IS ACTUALLY IN THE IMAGE, so the GPL source offer and the
    # reviewer's kit both have something concrete to point at.
    #
    # site/licenses.html offers corresponding source for every GPL package "matching
    # the versions we ship", and /review tells a reviewer they can see the package
    # list — but the only record of which versions those ARE lived in out/manifest,
    # which is generated per build, gitignored, and published nowhere. Debian's pool
    # drops superseded versions at every point release, so within months the offer
    # could not be honoured from the archive alone and nothing had captured the set.
    #
    # The ISO already carries the exact list at /live/filesystem.packages. Lifting it
    # out at publish time costs nothing and makes the offer mechanically honourable
    # for the GPL's three-year window.
    if command -v xorriso >/dev/null 2>&1; then
        mkdir -p "$SITE/manifest"
        for _e in "" "-pro"; do
            _iso="$OUT/dagric-os${_e}-$PRODUCT_VERSION-amd64.iso"
            _dst="$SITE/manifest/dagric-os${_e}-$PRODUCT_VERSION.packages"
            [ -f "$_iso" ] || continue
            if xorriso -osirrox on -indev "$_iso" \
                 -extract /live/filesystem.packages "$_dst" >/dev/null 2>&1; then
                echo "  manifest: $(wc -l < "$_dst") packages -> $_dst"
            else
                echo "  WARNING: could not extract the package manifest from $_iso" >&2
            fi
        done
    else
        echo "  WARNING: xorriso missing — package manifests NOT refreshed." >&2
        echo "           /licenses offers source 'matching the versions we ship'." >&2
        exit 1
    fi

    # THE CHANNEL IS BUILT BEFORE THE SITE GATE AND THE DEPLOY, NOT AFTER.
    #
    # These two lines were printed the other way round, and following them in
    # the printed order guarantees the failure this whole script exists to stop:
    # build-repo.sh writes INTO site/repo, and `firebase deploy --only hosting`
    # uploads site/. Deploy first and you publish the OLD channel and leave the
    # freshly built one sitting on disk — half a release, which is exactly what
    # verify-published.sh was written to catch after it happened.
    #
    # docs/REPOSITORY.md has had the right order all along (build-repo at step 4,
    # deploy at step 6). Three procedures in one repo disagreeing about the order
    # is how the wrong one gets followed.
    echo
    echo "  building the signed APT update channel before checking the site"
    sh packages/build-repo.sh || {
        echo "release: the APT update channel could not be built." >&2
        exit 1
    }

    python3 tools/write-release-proof.py || {
        echo "release: the public release record could not be generated." >&2
        exit 1
    }

    # THE SITE ITSELF IS PART OF THE RELEASE. This gate must run only after
    # every generated thing it links to exists: signed sums, package manifests,
    # the APT repository, and the machine-readable release record. Running it
    # earlier made a clean checkout impossible to release because /security
    # correctly linked to /repo/dagric-repo.gpg.asc before that file was built.
    echo
    sh tools/check-site.sh || {
        echo "release: the site is not ready to deploy (see above)." >&2
        exit 1
    }

    # Re-prove the hold after all metadata generation, immediately before the
    # operator deploys it. Distribution is enabled only after that deploy.
    sh tools/check-release-hold.sh || exit 1

    echo "  now:  firebase deploy --only hosting"
    echo "  then: sh tools/verify-published.sh (proves the LIVE end state, site AND channel)"
}

case "$MODE" in
    sign)    do_sign ;;
    gate)    do_gate ;;
    physical) physical_gate ;;
    publish) do_publish ;;
    check)   do_check ;;
    *)       usage ;;
esac
