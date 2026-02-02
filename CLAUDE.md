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
- `prompts/variant_*.jinja2` - V2 prompt templates (5 variants: structural, clinical, personalized, few-shot, chain-of-thought)
- `data/instruments_extended.json` - Clinical instruments with subscales and scoring metadata

### Prompt Variants
| Variant | Template | Approach | Instruments |
|---------|----------|----------|-------------|
| structural | variant_a_structural.jinja2 | Safe baseline, clear format | All |
| clinical | variant_b_clinical.jinja2 | Clinical methodology-aware | All |
| personalized | variant_c_personalized.jinja2 | User profile adapted | All |
| fewshot | variant_d_fewshot.jinja2 | Few-shot examples (recommended) | All |
| cot | variant_e_cot.jinja2 | Chain-of-Thought reasoning | All |
| kasia_phq9 | variant_kasia_phq9.jinja2 | Kasia's clinical guidelines | PHQ-9 only |
| kasia_gad7 | variant_kasia_gad7.jinja2 | Kasia's clinical guidelines | GAD-7 only |

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
