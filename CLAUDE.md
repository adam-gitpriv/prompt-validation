# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prompt validation tool for mental health diagnostic interpretations at Mindgram. Tests how different prompt variants affect LLM-generated clinical questionnaire interpretations through blind A/B testing by human evaluators.

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Reset database (clear all interpretations and evaluations)
python scripts/reset_database.py

# Generate interpretations (test mode - 3 samples, no DB)
python scripts/generate_interpretations.py --dry-run

# Generate all interpretations (64 total)
python scripts/generate_interpretations.py

# Run evaluation UI locally
streamlit run app/streamlit_app.py

# Analyze evaluation results
python scripts/analysis.py

# Setup/verify database schema
python scripts/setup_supabase.py
```

## Experiment Workflow

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Clear previous data
python scripts/reset_database.py

# 3. Generate 64 interpretations (~20 min with rate limiting)
python scripts/generate_interpretations.py

# 4. Run evaluation UI
streamlit run app/streamlit_app.py
```

## Architecture

### Generation Pipeline
`User Profiles × Instruments × Score Levels` → Jinja2 template rendering → GPT-4.1 API → Supabase storage

### Evaluation Flow
Blind A/B pairs (same instrument/score, different variants) → Evaluator rates winner + 1-5 scale → Analysis computes win rates

### Key Components
- `app/streamlit_app.py` - Blind A/B evaluation UI
- `scripts/generate_interpretations.py` - LLM interpretation generation with rate limiting
- `scripts/reset_database.py` - Clear all interpretations and evaluations for fresh experiment
- `scripts/compare_variants.py` - Quick comparison of all variants for same profile/score
- `scripts/analysis.py` - Win rate and head-to-head analysis
- `scripts/test_templates.py` - Template rendering tests (no API required)
- `prompts/variant_*.jinja2` - 5 prompt templates (3 data-richness + 2 Kasia clinical)
- `data/instruments_extended.json` - Clinical instruments with subscales and scoring metadata
- `data/user_profiles_v2.json` - 4 diverse user profiles with subtopics
- `data/questionnaire_items.json` - PHQ-9 and GAD-7 question items

### Prompt Variants (5 total)
| Variant | Template | Instruments | User Data | Input Data |
|---------|----------|-------------|-----------|------------|
| minimal | variant_minimal.jinja2 | PHQ-9, GAD-7 | name, age, gender | score + level only |
| profile | variant_profile.jinja2 | PHQ-9, GAD-7 | + work_type, is_leader, ~15 subtopics | score + level only |
| answers | variant_answers.jinja2 | PHQ-9, GAD-7 | + work_type, is_leader, ~15 subtopics | score + individual answers |
| kasia_phq9 | variant_kasia_phq9.jinja2 | PHQ-9 only | name, age, gender, work_type | score + level (clinical guidelines) |
| kasia_gad7 | variant_kasia_gad7.jinja2 | GAD-7 only | name, age, gender, work_type | score + level (clinical guidelines) |

### Variant Characteristics
- **minimal**: Generic interpretation, no work/life context, universal recommendations
- **profile**: Personalized to work type and interests, references Mindgram content
- **answers**: Identifies specific problem areas from questionnaire responses, most targeted
- **kasia_***: Clinical guidelines from psychologist, structured format, work-aware but no subtopics

### Research Questions
1. **minimal vs profile** → Does full user context (work, subtopics) improve interpretations?
2. **profile vs answers** → Do individual question answers improve quality?
3. **minimal vs answers** → Full comparison: minimum vs maximum information
4. **kasia vs others** → Do Kasia's clinical guidelines produce better interpretations?
5. **kasia vs profile** → Clinical structure vs rich personalization (same user data level)

### Test Cases
- **4 profiles**: Ania (28, marketing), Tomek (38, IT leader), Magda (42, nurse), Marek (50, warehouse leader)
- **2 instruments**: PHQ-9, GAD-7
- **2 score levels**: moderate, severe
- **4 variants per instrument**: minimal, profile, answers + kasia (instrument-specific)
- **Total**: 4 profiles × 2 instruments × 2 scores × 4 variants = 64 interpretations

### Database (Supabase)
- `interpretations` - Generated text with variant, instrument, score, user profile
- `evaluations` - Ratings, preferences, evaluator feedback

## Environment Variables

Required (set in ~/.zshrc or Streamlit Cloud secrets):
- `OPENAI_API_KEY` - GPT-4.1 API access
- `SUPABASE_URL` - PostgreSQL endpoint
- `SUPABASE_KEY` - Database auth

## Deployment

Production: https://prompt-validation-jb7ey4wgzuvhbforapp4mqf.streamlit.app/

Auto-deploys from `main` branch via Streamlit Cloud.
