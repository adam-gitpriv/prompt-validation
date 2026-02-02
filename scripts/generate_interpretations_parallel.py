#!/usr/bin/env python3
"""
Parallel interpretation generation using asyncio.
Generates all interpretations concurrently for maximum speed.

Usage:
    python scripts/generate_interpretations_parallel.py              # Generate all
    python scripts/generate_interpretations_parallel.py --dry-run    # Test mode (3 samples)
    python scripts/generate_interpretations_parallel.py --concurrency=30  # Limit concurrency
"""
import os
import json
import asyncio
import random
import time
from pathlib import Path
from jinja2 import Template
from openai import AsyncOpenAI
from supabase import create_client

# Config
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
MODEL = "gpt-5.1"
DEFAULT_CONCURRENCY = 50  # Max concurrent requests

BASE_DIR = Path(__file__).parent.parent

# Load data
with open(BASE_DIR / "data/instruments_extended.json") as f:
    INSTRUMENTS = json.load(f)

with open(BASE_DIR / "data/user_profiles_v2.json") as f:
    USER_PROFILES = json.load(f)

with open(BASE_DIR / "data/questionnaire_items.json") as f:
    QUESTIONNAIRE_ITEMS = json.load(f)

# Prompt variants
PROMPT_VARIANTS = [
    {"id": "minimal", "template": "variant_minimal.jinja2", "instruments": ["PHQ-9", "GAD-7"]},
    {"id": "profile", "template": "variant_profile.jinja2", "instruments": ["PHQ-9", "GAD-7"]},
    {"id": "answers", "template": "variant_answers.jinja2", "instruments": ["PHQ-9", "GAD-7"]},
    {"id": "kasia_phq9", "template": "variant_kasia_phq9.jinja2", "instruments": ["PHQ-9"]},
    {"id": "kasia_gad7", "template": "variant_kasia_gad7.jinja2", "instruments": ["GAD-7"]},
]

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

# Load templates
TEMPLATES = {}
for variant in PROMPT_VARIANTS:
    template_path = BASE_DIR / "prompts" / variant["template"]
    with open(template_path) as f:
        TEMPLATES[variant["id"]] = Template(f.read())

# Clients
openai_client = None
supabase_client = None


def get_supabase():
    global supabase_client
    if supabase_client is None:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase_client


def get_openai():
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return openai_client


def simulate_answers(instrument_code: str, target_score: int) -> list[dict]:
    """Generate simulated answers for a questionnaire that sum to target_score."""
    items = QUESTIONNAIRE_ITEMS[instrument_code]["items"]
    response_options = QUESTIONNAIRE_ITEMS[instrument_code]["response_options"]
    num_items = len(items)

    base_value = target_score // num_items
    values = [min(base_value, 3) for _ in range(num_items)]
    current_sum = sum(values)

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

    while current_sum > target_score:
        for i in indices:
            if values[i] > 0 and current_sum > target_score:
                reduce = min(values[i], current_sum - target_score)
                values[i] -= reduce
                current_sum -= reduce

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


def build_prompt(instrument_code: str, score: int, level_label: str, variant_id: str, profile: dict) -> str:
    """Build prompt from template."""
    instrument = INSTRUMENTS[instrument_code]
    template = TEMPLATES[variant_id]

    context = {
        "instrument": instrument_code,
        "score": score,
        "max_score": instrument["scoring"]["max_score"],
        "level_label": level_label,
        "user_name": profile["name"],
        "user_age": profile["age"],
        "user_gender": profile["gender"],
    }

    if variant_id in ["kasia_phq9", "kasia_gad7"]:
        context["work_type"] = profile["work_type"]

    if variant_id in ["profile", "answers"]:
        context.update({
            "work_type": profile["work_type"],
            "is_leader": profile["is_leader"],
            "subtopics": profile["subtopics"],
        })

    if variant_id == "answers":
        context["answers"] = simulate_answers(instrument_code, score)

    return template.render(**context)


async def generate_single(
    semaphore: asyncio.Semaphore,
    task_info: dict,
    progress: dict
) -> dict:
    """Generate a single interpretation with rate limiting."""
    async with semaphore:
        instrument_code = task_info["instrument_code"]
        score_info = task_info["score_info"]
        variant = task_info["variant"]
        profile = task_info["profile"]

        prompt = build_prompt(
            instrument_code=instrument_code,
            score=score_info["score"],
            level_label=score_info["label"],
            variant_id=variant["id"],
            profile=profile
        )

        try:
            response = await get_openai().chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=16000,
                temperature=0.7
            )

            interpretation = response.choices[0].message.content

            if not interpretation or not interpretation.strip():
                progress["errors"] += 1
                return {"success": False, "error": "Empty response", **task_info}

            progress["completed"] += 1
            print(f"[{progress['completed']}/{progress['total']}] {instrument_code} | {variant['id']} | score={score_info['score']} | profile={profile['id']}")

            return {
                "success": True,
                "record": {
                    "instrument_code": instrument_code,
                    "score": score_info["score"],
                    "level": score_info["level"],
                    "prompt_variant": variant["id"],
                    "user_profile_id": profile["id"],
                    "interpretation_text": interpretation,
                    "model": MODEL
                }
            }

        except Exception as e:
            progress["errors"] += 1
            print(f"ERROR: {instrument_code}/{variant['id']}/profile={profile['id']}: {e}")
            return {"success": False, "error": str(e), **task_info}


def get_existing_keys() -> set:
    """Get set of existing (instrument, score, variant, profile) tuples with non-empty text."""
    result = get_supabase().table("interpretations").select(
        "instrument_code, score, prompt_variant, user_profile_id, interpretation_text"
    ).execute()

    existing = set()
    empty_ids_to_delete = []

    for r in result.data:
        key = (r["instrument_code"], r["score"], r["prompt_variant"], r["user_profile_id"])
        text = r.get("interpretation_text")
        if text and text.strip():
            existing.add(key)

    return existing


def delete_empty_records():
    """Delete any records with empty interpretation_text."""
    result = get_supabase().table("interpretations").select("id, interpretation_text").execute()
    empty_ids = [r["id"] for r in result.data if not r.get("interpretation_text") or not r["interpretation_text"].strip()]

    if empty_ids:
        for i in range(0, len(empty_ids), 10):
            get_supabase().table("interpretations").delete().in_("id", empty_ids[i:i+10]).execute()
        print(f"Deleted {len(empty_ids)} empty records")


async def main(dry_run: bool = False, concurrency: int = DEFAULT_CONCURRENCY, limit: int = None):
    """Generate all interpretations in parallel."""
    start_time = time.time()

    # Clean up empty records first
    delete_empty_records()

    # Get existing interpretations
    existing = get_existing_keys()
    print(f"Found {len(existing)} existing interpretations")

    # Build task list
    tasks_to_run = []

    for instrument_code, scores in TEST_SCORES.items():
        for score_info in scores:
            for variant in PROMPT_VARIANTS:
                if instrument_code not in variant["instruments"]:
                    continue
                for profile in USER_PROFILES:
                    key = (instrument_code, score_info["score"], variant["id"], profile["id"])
                    if key in existing:
                        continue
                    tasks_to_run.append({
                        "instrument_code": instrument_code,
                        "score_info": score_info,
                        "variant": variant,
                        "profile": profile
                    })

    total = len(tasks_to_run)
    print(f"Need to generate {total} interpretations")

    if total == 0:
        print("✅ All interpretations already exist!")
        return

    if dry_run:
        tasks_to_run = tasks_to_run[:3]
        total = len(tasks_to_run)
        print(f"(DRY RUN - only generating {total} samples)")

    if limit:
        tasks_to_run = tasks_to_run[:limit]
        total = len(tasks_to_run)

    print(f"Using concurrency: {concurrency}")
    print(f"Starting parallel generation...")
    print("-" * 50)

    # Progress tracking
    progress = {"completed": 0, "errors": 0, "total": total}

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(concurrency)

    # Run all tasks concurrently
    results = await asyncio.gather(*[
        generate_single(semaphore, task, progress)
        for task in tasks_to_run
    ])

    # Insert successful results
    successful = [r["record"] for r in results if r.get("success")]

    if successful and not dry_run:
        # Insert in batches of 20
        for i in range(0, len(successful), 20):
            batch = successful[i:i+20]
            get_supabase().table("interpretations").insert(batch).execute()
        print(f"Inserted {len(successful)} records to database")

    elapsed = time.time() - start_time
    print("-" * 50)
    print(f"✅ Done in {elapsed:.1f}s!")
    print(f"   Generated: {progress['completed']}")
    print(f"   Errors: {progress['errors']}")
    print(f"   Speed: {progress['completed']/elapsed:.1f} interpretations/second")


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv

    # Parse concurrency
    concurrency = DEFAULT_CONCURRENCY
    for arg in sys.argv:
        if arg.startswith("--concurrency="):
            concurrency = int(arg.split("=")[1])

    # Parse limit
    limit = None
    for arg in sys.argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=")[1])

    asyncio.run(main(dry_run=dry_run, concurrency=concurrency, limit=limit))
