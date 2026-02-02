#!/usr/bin/env python3
"""
Generate interpretations using OpenAI GPT-5.
Creates ~270 interpretations (3 instruments x 5 levels x 6 variants x ~3 profiles).
"""
import os
import json
import time
from pathlib import Path
from jinja2 import Template
from openai import OpenAI
from supabase import create_client

# Config
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
MODEL = "gpt-4o"  # Using gpt-4o as fallback if gpt-5 not available

BASE_DIR = Path(__file__).parent.parent

# Load data
with open(BASE_DIR / "data/instruments.json") as f:
    INSTRUMENTS = json.load(f)

with open(BASE_DIR / "data/user_profiles.json") as f:
    USER_PROFILES = json.load(f)

with open(BASE_DIR / "data/prompt_variants.json") as f:
    PROMPT_VARIANTS = json.load(f)

with open(BASE_DIR / "prompts/base.jinja2") as f:
    PROMPT_TEMPLATE = Template(f.read())

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_representative_scores(instrument_code: str) -> list[dict]:
    """Get one representative score per level for an instrument."""
    instrument = INSTRUMENTS[instrument_code]
    scores = []
    for range_info in instrument["scoring"]["ranges"]:
        mid_score = (range_info["min"] + range_info["max"]) // 2
        scores.append({
            "score": mid_score,
            "level": range_info["level"],
            "label": range_info["label"]
        })
    return scores


def generate_interpretation(
    instrument_code: str,
    score: int,
    level: str,
    level_label: str,
    variant: dict,
    profile: dict
) -> str:
    """Generate a single interpretation using GPT."""
    instrument = INSTRUMENTS[instrument_code]

    prompt = PROMPT_TEMPLATE.render(
        instrument_name=instrument["name"],
        instrument_code=instrument_code,
        score=score,
        max_score=instrument["scoring"]["max_score"],
        level_label=level_label,
        include_age=variant["include_age"],
        include_gender=variant["include_gender"],
        include_work=variant["include_work"],
        include_interests=variant["include_interests"],
        age=profile["age"],
        gender=profile["gender"],
        work=profile["work"],
        interests=profile["interests"]
    )

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )

    return response.choices[0].message.content


def main(dry_run: bool = False, limit: int = None):
    """Generate all interpretations."""
    generated = 0
    errors = 0

    # Select subset of profiles for variety (3 profiles)
    selected_profiles = USER_PROFILES[:3]

    total = len(INSTRUMENTS) * 5 * len(PROMPT_VARIANTS) * len(selected_profiles)  # ~270

    print(f"Generating ~{total} interpretations...")
    if dry_run:
        print("(DRY RUN - only generating 3 samples)")
        limit = 3

    for instrument_code in INSTRUMENTS:
        scores = get_representative_scores(instrument_code)

        for score_info in scores:
            for variant in PROMPT_VARIANTS:
                for profile in selected_profiles:
                    if limit and generated >= limit:
                        print(f"\n✅ Generated {generated} interpretations (limit reached)")
                        return

                    try:
                        interpretation = generate_interpretation(
                            instrument_code=instrument_code,
                            score=score_info["score"],
                            level=score_info["level"],
                            level_label=score_info["label"],
                            variant=variant,
                            profile=profile
                        )

                        # Save to Supabase
                        record = {
                            "instrument_code": instrument_code,
                            "score": score_info["score"],
                            "level": score_info["level"],
                            "prompt_variant": variant["id"],
                            "user_profile_id": profile["id"],
                            "interpretation_text": interpretation,
                            "model": MODEL
                        }

                        if not dry_run:
                            supabase.table("interpretations").insert(record).execute()

                        generated += 1
                        print(f"[{generated}/{total}] {instrument_code} | {variant['id']} | score={score_info['score']}")

                        # Rate limiting
                        time.sleep(0.5)

                    except Exception as e:
                        errors += 1
                        print(f"ERROR: {e}")
                        if errors > 5:
                            print("Too many errors, stopping.")
                            return

    print(f"\n✅ Done! Generated {generated} interpretations, {errors} errors.")


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
