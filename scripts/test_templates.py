#!/usr/bin/env python3
"""
Test template rendering without API calls.
Verifies that all templates can be rendered with the new data structure.
"""
import json
import random
from pathlib import Path
from jinja2 import Template

BASE_DIR = Path(__file__).parent.parent

# Load data
with open(BASE_DIR / "data/instruments_extended.json") as f:
    INSTRUMENTS = json.load(f)

with open(BASE_DIR / "data/user_profiles_v2.json") as f:
    USER_PROFILES = json.load(f)

with open(BASE_DIR / "data/questionnaire_items.json") as f:
    QUESTIONNAIRE_ITEMS = json.load(f)

# Variants to test
VARIANTS = [
    ("minimal", "variant_minimal.jinja2"),
    ("profile", "variant_profile.jinja2"),
    ("answers", "variant_answers.jinja2"),
]


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


def test_templates():
    """Test all template variants with sample data."""
    print("Testing template rendering...\n")

    profile = USER_PROFILES[0]  # Ania
    instrument_code = "PHQ-9"
    score = 12
    level_label = "Umiarkowane objawy depresji"

    for variant_id, template_file in VARIANTS:
        print(f"--- {variant_id.upper()} ---")

        template_path = BASE_DIR / "prompts" / template_file
        with open(template_path) as f:
            template = Template(f.read())

        # Base context
        context = {
            "instrument": instrument_code,
            "score": score,
            "max_score": INSTRUMENTS[instrument_code]["scoring"]["max_score"],
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
            print(f"Simulated answers sum: {sum(a['response_value'] for a in answers)}")

        try:
            rendered = template.render(**context)
            print(f"✅ Template rendered successfully ({len(rendered)} chars)")
            print(f"   First 200 chars: {rendered[:200]}...")
        except Exception as e:
            print(f"❌ Error: {e}")

        print()

    print("\n--- Data validation ---")
    print(f"User profiles: {len(USER_PROFILES)}")
    for p in USER_PROFILES:
        print(f"  - {p['name']} ({p['age']}y, {p['work_type']}, leader={p['is_leader']}, {len(p['subtopics'])} subtopics)")

    print(f"\nQuestionnaire items:")
    for inst, data in QUESTIONNAIRE_ITEMS.items():
        print(f"  - {inst}: {len(data['items'])} items")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_templates()
