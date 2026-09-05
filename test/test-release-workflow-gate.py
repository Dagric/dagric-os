#!/usr/bin/env python3
"""Static ordering checks for the commercial release workflow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
RELEASE_SH = (ROOT / "tools/release.sh").read_text(encoding="utf-8")
STAGE_SH = (ROOT / "tools/upload-to-r2.sh").read_text(encoding="utf-8")
PROMOTE_SH = (ROOT / "tools/promote-r2-release.sh").read_text(encoding="utf-8")


def before(first: str, second: str) -> None:
    left = WORKFLOW.find(first)
    right = WORKFLOW.find(second)
    assert left >= 0, f"missing workflow marker: {first}"
    assert right >= 0, f"missing workflow marker: {second}"
    assert left < right, f"{first!r} must precede {second!r}"


def main() -> int:
    before("Hard-gate the built commercial candidate", "Upload gated candidate to R2 staging")
    before("check-commercial-release.py edition", 'aws s3 cp "out/$ISO"')
    before("check-release-locales.py --root candidate-source", 'aws s3 cp "out/$ISO"')
    before("--authorization-output out/COMMERCIAL-RELEASE-AUTHORIZATION.json", 'aws s3 cp "out/$ISO"')
    before("Hard-gate release and promotion records", "Stage gated release records")
    before("check-physical-release.py check", "Create draft GitHub Release")
    before("check-commercial-release.py promotion", "Create draft GitHub Release")
    before("Verify candidate-specific staged ISO identities", "Create draft GitHub Release")
    assert "environment: commercial-release" in WORKFLOW
    assert "COMMERCIAL_RELEASE_APPROVAL_JSON" in WORKFLOW
    assert "PHYSICAL_RELEASE_EVIDENCE_JSON" in WORKFLOW
    assert "PHYSICAL-RELEASE-EVIDENCE.sha256" in WORKFLOW
    assert "draft: true" in WORKFLOW
    assert "git -C candidate-source checkout --quiet --detach \"$SOURCE_COMMIT\"" in WORKFLOW
    assert "DAGRIC_SOURCE_COMMIT=\"$SOURCE_COMMIT\"" in WORKFLOW
    assert "source-commit=$SOURCE_COMMIT" in WORKFLOW
    assert 'PREFIX="staging/$CANDIDATE_RELEASE_TAG/$SOURCE_COMMIT"' in WORKFLOW
    assert "R2_STAGING_BUCKET" in WORKFLOW
    assert "CLOUDFLARE_R2_AUDIT_TOKEN" in WORKFLOW
    assert "s3://dagric-downloads/$PREFIX" not in WORKFLOW
    assert "s3://dagric-pro/$PREFIX" not in WORKFLOW
    assert "PACKAGE_SECTIONS-$EDITION.tsv" in WORKFLOW
    assert "--free-package-sections out/PACKAGE_SECTIONS-free.tsv" in WORKFLOW
    assert "--pro-package-sections out/PACKAGE_SECTIONS-pro.tsv" in WORKFLOW
    assert "s3://dagric-downloads/dagric-os-1.0-amd64.iso" not in WORKFLOW

    sign_gate = RELEASE_SH.find("commercial_gate || exit 1")
    signing = RELEASE_SH.find('gpg --batch --yes --local-user "$KEYID"')
    assert 0 <= sign_gate < signing, "manual upload authorization must follow the gate"
    publish = RELEASE_SH.find("do_publish()")
    publish_gate = RELEASE_SH.find("commercial_gate || exit 1", publish)
    receipt_gate = RELEASE_SH.find("require_promotion_receipt || exit 1", publish)
    site_write = RELEASE_SH.find('cp "$OUT/SHA256SUMS"', publish)
    assert (
        publish < publish_gate < receipt_gate < site_write
    ), "manual publication must repeat the gate and require live-promotion proof"

    stage_gate = STAGE_SH.find("sh tools/release.sh gate")
    stage_upload = STAGE_SH.find("rclone copyto")
    assert 0 <= stage_gate < stage_upload, "manual staging must re-run the full gate"
    assert 'PREFIX="staging/$DAGRIC_RELEASE_TAG/$SOURCE_COMMIT"' in STAGE_SH
    assert 'if [ "$#" -ne 1 ]' in STAGE_SH
    assert 'R2:$BUCKET/$NAME' not in STAGE_SH
    assert "BUCKET=$DAGRIC_STAGING_BUCKET" in STAGE_SH
    assert "dagric-downloads|dagric-pro" in STAGE_SH
    assert STAGE_SH.count('cmp -s "$FILE" "$EXPECTED"') == 2
    assert "check-private-r2-staging.py" in STAGE_SH
    assert "COMMERCIAL-RELEASE-AUTHORIZATION.json" in STAGE_SH
    assert "R2_PUBLIC_HOST" not in STAGE_SH

    promote_gate = PROMOTE_SH.find("sh tools/release.sh gate")
    signature_check = PROMOTE_SH.find("gpg --batch --status-fd")
    live_marker = PROMOTE_SH.find("# These are the only live writes in the script.")
    live_free = PROMOTE_SH.find('"R2:dagric-downloads/$FREE_ISO"', live_marker)
    live_pro = PROMOTE_SH.find('"R2:dagric-pro/$PRO_ISO"', live_marker)
    live_sums = PROMOTE_SH.find("R2:dagric-downloads/SHA256SUMS\n", live_marker)
    live_sig = PROMOTE_SH.find("R2:dagric-downloads/SHA256SUMS.sig\n", live_marker)
    final_live_check = PROMOTE_SH.find(
        'require_remote_hash R2:dagric-downloads/SHA256SUMS.sig', live_sig
    )
    receipt_write = PROMOTE_SH.find('RECEIPT=out/release-gate/R2-LIVE-PROMOTION.json')
    assert PROMOTE_SH.find('DAGRIC_PROMOTE_TO_LIVE:-}') >= 0
    assert "R2:$STAGING_BUCKET/$PREFIX/$FREE_ISO" in PROMOTE_SH
    assert "R2:dagric-downloads/$PREFIX" not in PROMOTE_SH
    assert "R2:dagric-pro/$PREFIX" not in PROMOTE_SH
    assert "3A079F85DE74375DD65557096CE37402BA0A0EF8" in PROMOTE_SH
    assert '*"$KEY_FINGERPRINT"' not in PROMOTE_SH
    assert 0 <= promote_gate < signature_check < live_free
    assert live_free < live_pro < live_sums < live_sig, "signature must promote last"
    assert live_sig < final_live_check < receipt_write, "receipt requires live readback"
    first_hold = PROMOTE_SH.find("sh tools/check-release-hold.sh")
    second_hold = PROMOTE_SH.find("sh tools/check-release-hold.sh", first_hold + 1)
    assert signature_check < first_hold < live_free < second_hold < receipt_write
    assert '*"$KEYID"' not in RELEASE_SH
    assert "physical_gate || exit 1" in RELEASE_SH
    assert "PHYSICAL_RELEASE_EVIDENCE_JSON" in RELEASE_SH
    assert "sh tools/release.sh physical" in PROMOTE_SH
    assert '"physical_evidence_sha256"' in PROMOTE_SH
    assert 'receipt.get("physical_evidence_sha256")' in RELEASE_SH

    print("release-workflow-gate tests: workflow, staging and promotion controls passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
