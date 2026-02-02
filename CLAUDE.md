# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prompt validation tool for mental health diagnostic interpretations at Mindgram. Tests how different prompt variants affect LLM-generated clinical questionnaire interpretations through blind A/B testing by human evaluators.

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Generate interpretations (test mode - 3 samples, no DB)
python scripts/generate_interpretations.py --dry-run

# Generate all interpretations
python scripts/generate_interpretations.py

# Run evaluation UI locally
streamlit run app/streamlit_app.py

# Analyze evaluation results
python scripts/analysis.py

# Setup/verify database schema
python scripts/setup_supabase.py
```

## Architecture

### Generation Pipeline
`User Profiles × Instruments × Score Levels` → Jinja2 template rendering → GPT-4o API → Supabase storage

### Evaluation Flow
Blind A/B pairs (same instrument/score, different variants) → Evaluator rates winner + 1-5 scale → Analysis computes win rates

### Key Components
- `app/streamlit_app.py` - Blind A/B evaluation UI
- `scripts/generate_interpretations.py` - LLM interpretation generation with rate limiting
- `scripts/analysis.py` - Win rate and head-to-head analysis
- `scripts/test_templates.py` - Template rendering tests (no API required)
- `prompts/variant_*.jinja2` - V3 prompt templates (3 variants testing data richness)
- `data/instruments_extended.json` - Clinical instruments with subscales and scoring metadata
- `data/user_profiles_v2.json` - 4 diverse user profiles with subtopics
- `data/questionnaire_items.json` - PHQ-9 and GAD-7 question items

### V3 Prompt Variants (Current)
| Variant | Template | User Data | Input Data |
|---------|----------|-----------|------------|
| minimal | variant_minimal.jinja2 | name, age, gender | score + level only |
| profile | variant_profile.jinja2 | + work_type, is_leader, ~15 subtopics | score + level only |
| answers | variant_answers.jinja2 | + work_type, is_leader, ~15 subtopics | score + individual answers |

### Research Questions
1. **minimal vs profile** → Does full user context (work, subtopics) improve interpretations?
2. **profile vs answers** → Do individual question answers improve quality?
3. **minimal vs answers** → Full comparison: minimum vs maximum information

### Test Cases
- **4 profiles**: Ania (28, marketing), Tomek (38, IT leader), Magda (42, nurse), Marek (50, warehouse leader)
- **2 instruments**: PHQ-9, GAD-7
- **2 score levels**: moderate, severe
- **Total**: 4 × 2 × 2 × 3 = 48 interpretations → 48 evaluation pairs

### Legacy Variants (Reference)
| Variant | Template | Notes |
|---------|----------|-------|
| kasia_phq9 | variant_kasia_phq9.jinja2 | Kasia's clinical guidelines for PHQ-9 |
| kasia_gad7 | variant_kasia_gad7.jinja2 | Kasia's clinical guidelines for GAD-7 |

### Database (Supabase)
- `interpretations` - Generated text with variant, instrument, score, user profile
- `evaluations` - Ratings, preferences, evaluator feedback

## Environment Variables

Required (set in ~/.zshrc or Streamlit Cloud secrets):
- `OPENAI_API_KEY` - GPT-4o API access
- `SUPABASE_URL` - PostgreSQL endpoint
- `SUPABASE_KEY` - Database auth

## Deployment

Production: https://prompt-validation-jb7ey4wgzuvhbforapp4mqf.streamlit.app/

Auto-deploys from `main` branch via Streamlit Cloud.
