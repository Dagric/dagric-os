#!/usr/bin/env python3
"""Create auditable ElevenLabs narration without storing credentials in the repo.

The API key is read only from the ELEVENLABS_API_KEY environment variable.  The
script deliberately does not read .env files, print request headers, or write the
key to its JSON sidecar manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_BASE = "https://api.elevenlabs.io/v1"


class PipelineError(RuntimeError):
    """A safe, user-actionable request failure."""


def api_key() -> str:
    value = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not value:
        raise PipelineError(
            "ELEVENLABS_API_KEY is not set. Add a newly issued key to your "
            "user/CI environment, then run this command again."
        )
    return value


def safe_error_body(error: urllib.error.HTTPError) -> str:
    try:
        body = error.read().decode("utf-8", errors="replace")
    except OSError:
        return "No response details were returned."
    try:
        parsed = json.loads(body)
        detail = parsed.get("detail", parsed.get("message", body))
        if isinstance(detail, dict):
            detail = detail.get("message", json.dumps(detail, ensure_ascii=False))
        body = str(detail)
    except json.JSONDecodeError:
        pass
    return " ".join(body.split())[:360] or "No response details were returned."


def request(
    endpoint: str,
    *,
    accept: str,
    payload: dict[str, Any] | None = None,
) -> bytes:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"xi-api-key": api_key(), "Accept": accept}
    if data is not None:
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(
        f"{API_BASE}{endpoint}", data=data, headers=headers, method="POST" if data is not None else "GET"
    )
    try:
        with urllib.request.urlopen(call, timeout=90) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise PipelineError(f"ElevenLabs returned HTTP {error.code}: {safe_error_body(error)}") from error
    except urllib.error.URLError as error:
        raise PipelineError(f"Could not reach ElevenLabs: {error.reason}") from error


def write_bytes_atomically(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", suffix=".part", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def list_voices(_: argparse.Namespace) -> int:
    response = json.loads(request("/voices", accept="application/json"))
    voices = response.get("voices", [])
    if not voices:
        raise PipelineError("ElevenLabs returned no voices for this account.")
    print("VOICE ID\tNAME\tCATEGORY\tLABELS")
    for voice in voices:
        labels = voice.get("labels") or {}
        label_text = ", ".join(f"{name}={value}" for name, value in sorted(labels.items()))
        print(
            "\t".join(
                [
                    str(voice.get("voice_id", "")),
                    str(voice.get("name", "")),
                    str(voice.get("category", "")),
                    label_text,
                ]
            )
        )
    print(f"Listed {len(voices)} available ElevenLabs voices.")
    return 0


def input_text(args: argparse.Namespace) -> tuple[str, str]:
    if args.text is not None:
        result = args.text.strip()
        source = "command line text"
    else:
        path = args.text_file.resolve()
        if not path.is_file():
            raise PipelineError(f"Narration text file does not exist: {path}")
        result = path.read_text(encoding="utf-8").strip()
        source = str(path)
    if not result:
        raise PipelineError("Narration text is empty.")
    if len(result) > 10_000:
        raise PipelineError("Narration exceeds 10,000 characters; split it into shorter approved takes.")
    return result, source


def synthesize(args: argparse.Namespace) -> int:
    text, source = input_text(args)
    if not 0.7 <= args.speed <= 1.2:
        raise PipelineError("--speed must be between 0.7 and 1.2.")
    for name, value in {
        "--stability": args.stability,
        "--similarity-boost": args.similarity_boost,
        "--style": args.style,
    }.items():
        if not 0.0 <= value <= 1.0:
            raise PipelineError(f"{name} must be between 0 and 1.")
    output = args.output.resolve()
    if output.suffix.lower() != ".mp3":
        raise PipelineError("--output must use the .mp3 extension.")

    payload = {
        "text": text,
        "model_id": args.model_id,
        "voice_settings": {
            "stability": args.stability,
            "similarity_boost": args.similarity_boost,
            "style": args.style,
            "use_speaker_boost": not args.no_speaker_boost,
            "speed": args.speed,
        },
    }
    query = urllib.parse.urlencode({"output_format": args.output_format})
    audio = request(
        f"/text-to-speech/{urllib.parse.quote(args.voice_id, safe='')}?{query}",
        accept="audio/mpeg",
        payload=payload,
    )
    if not audio:
        raise PipelineError("ElevenLabs returned an empty audio response.")
    write_bytes_atomically(output, audio)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "generator": "promo/elevenlabs_tts.py",
        "provider": "ElevenLabs",
        "model": args.model_id,
        "voiceId": args.voice_id,
        "outputFormat": args.output_format,
        "voiceSettings": payload["voice_settings"],
        "sourceText": source,
        "characters": len(text),
        "audioFile": str(output),
        "audioSha256": digest(audio),
        "syntheticVoiceDisclosure": True,
    }
    manifest_path = output.with_suffix(".json")
    write_bytes_atomically(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    print(f"Created {output.name} ({len(audio):,} bytes)")
    print(f"Wrote audit manifest {manifest_path.name}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Create Dagric narration with ElevenLabs without storing an API key in the repository.")
    subcommands = result.add_subparsers(dest="command", required=True)

    voices = subcommands.add_parser("voices", help="List voices available to the configured ElevenLabs account.")
    voices.set_defaults(handler=list_voices)

    synth = subcommands.add_parser("synthesize", help="Generate one MP3 narration take and an audit sidecar.")
    text = synth.add_mutually_exclusive_group(required=True)
    text.add_argument("--text", help="Approved narration text.")
    text.add_argument("--text-file", type=Path, help="UTF-8 text file containing approved narration.")
    synth.add_argument("--voice-id", required=True, help="Voice ID returned by the voices command.")
    synth.add_argument("--output", type=Path, required=True, help="MP3 output path; binary output stays ignored by Git.")
    synth.add_argument("--model-id", default="eleven_multilingual_v2", help="ElevenLabs speech model (default: eleven_multilingual_v2).")
    synth.add_argument("--output-format", default="mp3_44100_128", help="ElevenLabs output format (default: mp3_44100_128).")
    synth.add_argument("--stability", type=float, default=0.45, help="Voice stability, 0 to 1 (default: 0.45).")
    synth.add_argument("--similarity-boost", type=float, default=0.78, help="Voice similarity boost, 0 to 1 (default: 0.78).")
    synth.add_argument("--style", type=float, default=0.0, help="Style exaggeration, 0 to 1 (default: 0).")
    synth.add_argument("--speed", type=float, default=1.0, help="Speaking speed, 0.7 to 1.2 (default: 1.0).")
    synth.add_argument("--no-speaker-boost", action="store_true", help="Disable the model's speaker boost for this take.")
    synth.set_defaults(handler=synthesize)
    return result


def main() -> int:
    try:
        args = parser().parse_args()
        return args.handler(args)
    except PipelineError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
