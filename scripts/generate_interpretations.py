#!/usr/bin/env python3
"""
Generate interpretations using OpenAI GPT-4o.
V3 - New prompt variants for testing:
  - minimal: basic user data + score only
  - profile: full user profile with subtopics + score
  - answers: full profile + individual question answers
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
with open(BASE_DIR / "data/instruments_extended.json") as f:
    INSTRUMENTS = json.load(f)

with open(BASE_DIR / "data/user_profiles_v2.json") as f:
    USER_PROFILES = json.load(f)

with open(BASE_DIR / "data/questionnaire_items.json") as f:
    QUESTIONNAIRE_ITEMS = json.load(f)

# V3 prompt variants - focused on comparing data richness
PROMPT_VARIANTS = [
    {"id": "minimal", "template": "variant_minimal.jinja2", "instruments": ["PHQ-9", "GAD-7"]},
    {"id": "profile", "template": "variant_profile.jinja2", "instruments": ["PHQ-9", "GAD-7"]},
    {"id": "answers", "template": "variant_answers.jinja2", "instruments": ["PHQ-9", "GAD-7"]},
]

# Test cases: 2 score levels per instrument (moderate and severe)
TEST_SCORES = {
    "PHQ-9": [
        {"score": 12, "level": "moderate", "label": "Umiarkowane objawy depresji"},
        {"score": 20, "level": "severe", "label": "Ciężkie objawy depresji"},
    ],
    "GAD-7": [
        {"score": 10, "level": "moderate", "label": "Umiarkowany lęk"},
        {"score": 17, "level": "severe", "label": "Ciężki lęk"},
    ],
}

# Load all templates
TEMPLATES = {}
for variant in PROMPT_VARIANTS:
    template_path = BASE_DIR / "prompts" / variant["template"]
    with open(template_path) as f:
        TEMPLATES[variant["id"]] = Template(f.read())

# Initialize clients lazily (only when needed)
openai_client = None
supabase_client = None


def get_openai_client():
    """Lazy initialization of OpenAI client."""
    global openai_client
    if openai_client is None:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return openai_client


def get_supabase_client():
    """Lazy initialization of Supabase client."""
    global supabase_client
    if supabase_client is None:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase_client


def simulate_answers(instrument_code: str, target_score: int) -> list[dict]:
    """
    Generate simulated answers for a questionnaire that sum to target_score.
    Returns list of answer dicts with question text, response value and label.
    """
    items = QUESTIONNAIRE_ITEMS[instrument_code]["items"]
    response_options = QUESTIONNAIRE_ITEMS[instrument_code]["response_options"]
    num_items = len(items)

    # Distribute target_score across items
    # Strategy: start with even distribution, then adjust randomly
    base_value = target_score // num_items
    remainder = target_score % num_items

    # Initialize with base values
    values = [min(base_value, 3) for _ in range(num_items)]
    current_sum = sum(values)

    # Add remainder to random items
    indices = list(range(num_items))
    random.shuffle(indices)

    for i in indices:
        if current_sum >= target_score:
            break
        max_add = min(3 - values[i], target_score - current_sum)
        if max_add > 0:
            add = random.randint(1, max_add)
            values[i] += add
            current_sum += add

    # If we overshot, reduce some values
    while current_sum > target_score:
        for i in indices:
            if values[i] > 0 and current_sum > target_score:
                reduce = min(values[i], current_sum - target_score)
                values[i] -= reduce
                current_sum -= reduce

    # Build answer list
    answers = []
    for i, item in enumerate(items):
        response_value = values[i]
        response_label = response_options[response_value]["label"]
        answers.append({
            "number": item["number"],
            "question": item["text_pl"],
            "response_value": response_value,
            "response_label": response_label,
        })

    return answers


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

    # Base context for all variants
    context = {
        "instrument": instrument_code,
        "score": score,
        "max_score": instrument["scoring"]["max_score"],
        "level_label": level_label,
        "user_name": profile["name"],
        "user_age": profile["age"],
        "user_gender": profile["gender"],
    }

    # Add profile data for 'profile' and 'answers' variants
    if variant_id in ["profile", "answers"]:
        context.update({
            "work_type": profile["work_type"],
            "is_leader": profile["is_leader"],
            "subtopics": profile["subtopics"],
        })

    # Add simulated answers for 'answers' variant
    if variant_id == "answers":
        answers = simulate_answers(instrument_code, score)
        context["answers"] = answers

    prompt = template.render(**context)

    response = get_openai_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.7
    )

    return response.choices[0].message.content


def check_existing(instrument_code: str, score: int, variant_id: str, profile_id: int) -> bool:
    """Check if interpretation already exists."""
    result = get_supabase_client().table("interpretations").select("id").eq(
        "instrument_code", instrument_code
    ).eq("score", score).eq("prompt_variant", variant_id).eq(
        "user_profile_id", profile_id
    ).execute()
    return len(result.data) > 0


def main(dry_run: bool = False, limit: int = None, skip_existing: bool = True):
    """Generate all interpretations for V3 experiment."""
    generated = 0
    skipped = 0
    errors = 0

    # Calculate total
    # 4 profiles × 2 instruments × 2 scores × 3 variants = 48
    total = len(USER_PROFILES) * len(TEST_SCORES) * 2 * len(PROMPT_VARIANTS)

    print(f"Generating {total} interpretations...")
    print(f"Instruments: {list(TEST_SCORES.keys())}")
    print(f"Variants: {[v['id'] for v in PROMPT_VARIANTS]}")
    print(f"Profiles: {len(USER_PROFILES)}")
    print(f"Scores per instrument: 2 (moderate, severe)")

    if dry_run:
        print("(DRY RUN - only generating 3 samples)")
        limit = 3

    for instrument_code, scores in TEST_SCORES.items():
        for score_info in scores:
            for variant in PROMPT_VARIANTS:
                for profile in USER_PROFILES:
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

                        # Build record with V3 profile data
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
                            get_supabase_client().table("interpretations").insert(record).execute()
                        else:
                            print(f"\n--- Sample ({variant['id']}) ---")
                            print(f"Profile: {profile['name']}, {profile['age']}y, {profile['work_type']}")
                            print(f"Leader: {profile['is_leader']}, Work: {profile['work_type']}")
                            print(f"Subtopics: {profile['subtopics'][:3]}...")
                            print(f"Score: {score_info['score']} ({score_info['label']})")
                            print(interpretation[:500] + "..." if len(interpretation) > 500 else interpretation)
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
