#!/usr/bin/env python3
"""
Quick comparison of 3 prompt variants for the same profile/score.
Generates one interpretation per variant and prints them for comparison.
"""
import os
import json
import random
from pathlib import Path
from jinja2 import Template
from openai import OpenAI

BASE_DIR = Path(__file__).parent.parent

# Load data
with open(BASE_DIR / "data/instruments_extended.json") as f:
    INSTRUMENTS = json.load(f)

with open(BASE_DIR / "data/user_profiles_v2.json") as f:
    USER_PROFILES = json.load(f)

with open(BASE_DIR / "data/questionnaire_items.json") as f:
    QUESTIONNAIRE_ITEMS = json.load(f)

# Load templates
TEMPLATES = {}
for variant_id in ["minimal", "profile", "answers"]:
    template_path = BASE_DIR / "prompts" / f"variant_{variant_id}.jinja2"
    with open(template_path) as f:
        TEMPLATES[variant_id] = Template(f.read())

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def simulate_answers(instrument_code: str, target_score: int) -> list[dict]:
    """Generate simulated answers that sum to target_score."""
    items = QUESTIONNAIRE_ITEMS[instrument_code]["items"]
    response_options = QUESTIONNAIRE_ITEMS[instrument_code]["response_options"]
    num_items = len(items)

    random.seed(42)  # For reproducibility

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


def generate_interpretation(variant_id: str, profile: dict, instrument_code: str, score: int, level_label: str) -> str:
    """Generate a single interpretation."""
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

    if variant_id in ["profile", "answers"]:
        context.update({
            "work_type": profile["work_type"],
            "is_leader": profile["is_leader"],
            "subtopics": profile["subtopics"],
        })

    if variant_id == "answers":
        context["answers"] = simulate_answers(instrument_code, score)

    prompt = template.render(**context)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.7
    )

    return response.choices[0].message.content


def main():
    # Test case: Ania, PHQ-9, score 12 (moderate)
    profile = USER_PROFILES[0]  # Ania
    instrument = "PHQ-9"
    score = 12
    level_label = "Umiarkowane objawy depresji"

    print("=" * 80)
    print(f"PORÓWNANIE WARIANTÓW PROMPTÓW")
    print(f"Profil: {profile['name']}, {profile['age']} lat, {profile['gender']}")
    print(f"Praca: {profile['work_type']}, lider: {profile['is_leader']}")
    print(f"Instrument: {instrument}, wynik: {score}/27 ({level_label})")
    print("=" * 80)

    for variant_id in ["minimal", "profile", "answers"]:
        print(f"\n{'='*80}")
        print(f"WARIANT: {variant_id.upper()}")
        print("=" * 80)

        if variant_id == "minimal":
            print("(tylko: imię, wiek, płeć + wynik)")
        elif variant_id == "profile":
            print("(+ work_type, is_leader, ~15 subtopics)")
        else:
            print("(+ wszystko powyżej + odpowiedzi na pytania)")

        print("-" * 80)

        interpretation = generate_interpretation(
            variant_id=variant_id,
            profile=profile,
            instrument_code=instrument,
            score=score,
            level_label=level_label
        )

        print(interpretation)
        print()


if __name__ == "__main__":
    main()
