#!/usr/bin/env python3
"""
Generate interpretations using OpenAI GPT-4o.
Creates ~270 interpretations (3 instruments x 5 levels x 6 variants x 3 profiles).
Uses 6 separate prompt templates as per the plan.
"""
import os
import json
import time
import random
from pathlib import Path
from jinja2 import Template
from openai import OpenAI
from supabase import create_client

# Config
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
MODEL = "gpt-4o"

BASE_DIR = Path(__file__).parent.parent

# Load data
with open(BASE_DIR / "data/instruments.json") as f:
    INSTRUMENTS = json.load(f)

with open(BASE_DIR / "data/user_profiles.json") as f:
    USER_PROFILES = json.load(f)

# Prompt variants mapping to template files
PROMPT_VARIANTS = [
    {"id": "basic", "template": "basic.jinja2"},
    {"id": "with_work", "template": "with_work.jinja2"},
    {"id": "with_interests", "template": "with_interests.jinja2"},
    {"id": "with_history", "template": "with_history.jinja2"},
    {"id": "with_support", "template": "with_support.jinja2"},
    {"id": "full", "template": "full.jinja2"},
]

# Load all templates
TEMPLATES = {}
for variant in PROMPT_VARIANTS:
    template_path = BASE_DIR / "prompts" / variant["template"]
    with open(template_path) as f:
        TEMPLATES[variant["id"]] = Template(f.read())

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


def generate_history_data(instrument_code: str, current_score: int) -> dict:
    """Generate simulated history data for with_history variant."""
    instrument = INSTRUMENTS[instrument_code]
    max_score = instrument["scoring"]["max_score"]

    # Random previous score
    delta = random.randint(-5, 5)
    previous_score = max(0, min(max_score, current_score + delta))

    if previous_score < current_score:
        trend = "pogorszenie"
    elif previous_score > current_score:
        trend = "poprawa"
    else:
        trend = "stabilny"

    return {
        "previous_score": previous_score,
        "previous_date": "2 tygodnie temu",
        "trend": trend
    }


def generate_support_data() -> dict:
    """Generate simulated support activity data for with_support variant."""
    has_chat = random.choice([True, False])
    has_sessions = random.choice([True, False])

    programs = ["Zarządzanie stresem", "Mindfulness", "Sen i regeneracja", "Odporność psychiczna"]
    active_programs = random.sample(programs, k=random.randint(0, 2)) if random.random() > 0.5 else []

    return {
        "has_chat_history": has_chat,
        "last_chat_date": "3 dni temu" if has_chat else None,
        "has_sessions": has_sessions,
        "sessions_count": random.randint(2, 8) if has_sessions else 0,
        "active_programs": active_programs
    }


def generate_interpretation(
    instrument_code: str,
    score: int,
    level: str,
    level_label: str,
    variant_id: str,
    profile: dict
) -> str:
    """Generate a single interpretation using GPT."""
    instrument = INSTRUMENTS[instrument_code]
    template = TEMPLATES[variant_id]

    # Base context
    context = {
        "instrument_name": instrument["name"],
        "instrument_code": instrument_code,
        "score": score,
        "max_score": instrument["scoring"]["max_score"],
        "level_label": level_label,
        "age": profile["age"],
        "gender": profile["gender"],
        "work": profile["work"],
        "interests": profile["interests"],
    }

    # Add history data for with_history and full variants
    if variant_id in ["with_history", "full"]:
        history = generate_history_data(instrument_code, score)
        context.update(history)

    # Add support data for with_support and full variants
    if variant_id in ["with_support", "full"]:
        support = generate_support_data()
        context.update(support)

    prompt = template.render(**context)

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )

    return response.choices[0].message.content


def check_existing(instrument_code: str, score: int, variant_id: str, profile_id: int) -> bool:
    """Check if interpretation already exists."""
    result = supabase.table("interpretations").select("id").eq(
        "instrument_code", instrument_code
    ).eq("score", score).eq("prompt_variant", variant_id).eq(
        "user_profile_id", profile_id
    ).execute()
    return len(result.data) > 0


def main(dry_run: bool = False, limit: int = None, skip_existing: bool = True):
    """Generate all interpretations."""
    generated = 0
    skipped = 0
    errors = 0

    # Select subset of profiles for variety (3 profiles)
    selected_profiles = USER_PROFILES[:3]

    total_combinations = (
        len(INSTRUMENTS) *
        sum(len(inst["scoring"]["ranges"]) for inst in INSTRUMENTS.values()) *
        len(PROMPT_VARIANTS) *
        len(selected_profiles)
    )

    # Approximate total
    total = len(INSTRUMENTS) * 5 * len(PROMPT_VARIANTS) * len(selected_profiles)

    print(f"Generating ~{total} interpretations...")
    print(f"Instruments: {list(INSTRUMENTS.keys())}")
    print(f"Variants: {[v['id'] for v in PROMPT_VARIANTS]}")
    print(f"Profiles: {len(selected_profiles)}")

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
                        print(f"   Skipped {skipped} existing")
                        return

                    # Check if already exists
                    if skip_existing and check_existing(
                        instrument_code, score_info["score"],
                        variant["id"], profile["id"]
                    ):
                        skipped += 1
                        continue

                    try:
                        interpretation = generate_interpretation(
                            instrument_code=instrument_code,
                            score=score_info["score"],
                            level=score_info["level"],
                            level_label=score_info["label"],
                            variant_id=variant["id"],
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
                        else:
                            print(f"\n--- Sample ({variant['id']}) ---")
                            print(f"Profile: {profile['gender']}, {profile['age']}y, {profile['work']}")
                            print(f"Score: {score_info['score']} ({score_info['label']})")
                            print(interpretation)
                            print("-" * 50)

                        generated += 1
                        print(f"[{generated}/{total}] {instrument_code} | {variant['id']} | score={score_info['score']} | profile={profile['id']}")

                        # Rate limiting
                        time.sleep(0.3)

                    except Exception as e:
                        errors += 1
                        print(f"ERROR: {e}")
                        if errors > 10:
                            print("Too many errors, stopping.")
                            return

    print(f"\n✅ Done! Generated {generated} interpretations, skipped {skipped}, {errors} errors.")


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    no_skip = "--no-skip" in sys.argv

    # Parse limit
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])

    main(dry_run=dry_run, limit=limit, skip_existing=not no_skip)
