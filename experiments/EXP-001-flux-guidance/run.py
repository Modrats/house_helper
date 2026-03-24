"""EXP-001: FLUX.2-pro guidance parameter experiment runner.

Usage (from repo root):
    uv run python experiments/EXP-001-flux-guidance/run.py

    # Dry run (no API calls, just prints what would be called):
    uv run python experiments/EXP-001-flux-guidance/run.py --dry-run

    # Run a single room only:
    uv run python experiments/EXP-001-flux-guidance/run.py --room kitchen

Outputs images to:
    experiments/EXP-001-flux-guidance/results/{room}/guidance_{value}.png

After running, open evaluate.html in a browser to score results.
"""
from __future__ import annotations

import argparse
import base64
import os
import random
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from the experiment directory (plain KEY=value, no export needed)
# ---------------------------------------------------------------------------

_ENV_FILE = Path(__file__).resolve().parent / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

import json  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EXP_DIR / "results"

_config = json.loads((EXP_DIR / "config.json").read_text())

GUIDANCE_VALUES: list[int] = _config["guidance_values"]
SEED: int = _config["seed"]
_system_prompt: str = _config.get("system_prompt", "")
ROOMS: dict[str, dict] = {
    name: {
        "photo": REPO_ROOT / room["photo"],
        "prompt": _system_prompt + room["prompt"],
    }
    for name, room in _config["rooms"].items()
}

# Retry config
MAX_RETRIES = 5
BASE_DELAY = 2.0
MAX_DELAY = 120.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# FLUX client (self-contained, no package dependency)
# ---------------------------------------------------------------------------

def call_flux(
    *,
    api_key: str,
    endpoint: str,
    prompt: str,
    image_bytes: bytes,
    guidance: float,
    seed: int,
    dry_run: bool = False,
) -> bytes | None:
    """Call FLUX.2-pro and return raw PNG bytes, or None on dry run."""
    if dry_run:
        print(f"  [DRY RUN] Would POST to {endpoint} guidance={guidance} seed={seed}")
        return None

    import requests  # noqa: PLC0415

    url = f"{endpoint}?api-version=preview"
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    body = {
        "prompt": prompt,
        "model": "FLUX.2-pro",
        "n": 1,
        "width": 1024,
        "height": 1024,
        "guidance": guidance,
        "steps": 50,
        "seed": seed,
        "input_image": b64,
    }

    last_error: str | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json=body,
                timeout=300,
            )

            if resp.ok:
                data = resp.json().get("data", [])
                if not data or "b64_json" not in data[0]:
                    raise RuntimeError(f"Unexpected response shape: {resp.text[:500]}")
                return base64.b64decode(data[0]["b64_json"])

            if resp.status_code in RETRYABLE_STATUS_CODES:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY) + random.uniform(0, 1)
                print(f"  [{resp.status_code}] Retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES + 1})")
                time.sleep(delay)
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                continue

            print(f"  [ERROR] {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()

        except Exception as exc:  # noqa: BLE001
            if attempt < MAX_RETRIES:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                print(f"  [RETRY] {exc} — waiting {delay:.1f}s")
                time.sleep(delay)
                last_error = str(exc)
            else:
                raise RuntimeError(f"FLUX request failed: {exc}") from exc

    raise RuntimeError(f"FLUX request failed after {MAX_RETRIES + 1} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run EXP-001 FLUX guidance experiment")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without calling API")
    parser.add_argument("--room", choices=list(ROOMS), help="Run one room only")
    parser.add_argument("--guidance", type=int, nargs="+", help="Override guidance values (e.g. --guidance 15 30)")
    args = parser.parse_args()

    errors = []
    api_key = os.getenv("FLUX_KEY", "")
    endpoint = os.getenv("FLUX_ENDPOINT", "")

    if not args.dry_run:
        if not api_key:
            errors.append("FLUX_KEY is not set — set it to your Azure AI Foundry API key")
        if not endpoint:
            errors.append("FLUX_ENDPOINT is not set — set it to the FLUX.2-pro endpoint URL")
        if errors:
            print("ERROR: Missing required environment variables:")
            for e in errors:
                print(f"  • {e}")
            print("\nSee sample.env for reference.")
            sys.exit(1)
    guidance_values = args.guidance or GUIDANCE_VALUES
    rooms = {args.room: ROOMS[args.room]} if args.room else ROOMS

    print("=" * 60)
    print("EXP-001: FLUX.2-pro Guidance Parameter Experiment")
    print("=" * 60)
    print(f"Endpoint : {endpoint or '(dry run — not required)'}")
    print(f"Guidance : {guidance_values}")
    print(f"Seed     : {SEED}")
    print(f"Rooms    : {list(rooms)}")
    print(f"Dry run  : {args.dry_run}")
    print("=" * 60)

    total = len(rooms) * len(guidance_values)
    done = 0
    skipped = 0

    for room_name, room_cfg in rooms.items():
        photo_path = room_cfg["photo"]
        prompt = room_cfg["prompt"]

        if not photo_path.exists():
            print(f"\n⚠  SKIP {room_name}: photo not found at {photo_path}")
            skipped += len(guidance_values)
            continue

        image_bytes = photo_path.read_bytes()
        out_dir = RESULTS_DIR / room_name
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n▶ {room_name}  ({photo_path.name}, {len(image_bytes):,} bytes)")
        print(f"   prompt: {prompt[:80]}{'…' if len(prompt) > 80 else ''}")

        for guidance in guidance_values:
            out_path = out_dir / f"guidance_{guidance:02d}.png"

            if out_path.exists():
                print(f"  guidance={guidance:2d}  → already exists, skipping ({out_path.name})")
                done += 1
                continue

            print(f"  guidance={guidance:2d}  → calling API...", end="", flush=True)

            result = call_flux(
                api_key=api_key,
                endpoint=endpoint,
                prompt=prompt,
                image_bytes=image_bytes,
                guidance=guidance,
                seed=SEED,
                dry_run=args.dry_run,
            )

            if result is not None:
                out_path.write_bytes(result)
                print(f" saved {len(result):,} bytes → {out_path.relative_to(REPO_ROOT)}")
            else:
                print()  # newline after dry-run line

            done += 1

    print(f"\n{'=' * 60}")
    print(f"Done: {done}/{total} calls  |  Skipped (missing photos): {skipped}")
    if not args.dry_run and done > skipped:
        evaluate_html = Path(__file__).resolve().parent / "evaluate.html"
        print(f"\nOpen the evaluator:")
        print(f"  {evaluate_html}")


if __name__ == "__main__":
    main()
