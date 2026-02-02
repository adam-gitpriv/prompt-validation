# Prompt Validation - Diagnostyka Mindgram

Narzędzie do walidacji promptów generujących interpretacje wyników diagnostycznych w aplikacji Mindgram.

## Cel projektu (V3)

Zbadać **dwa kluczowe pytania**:
1. Czy **pełny kontekst użytkownika** (praca, stanowisko, subtematy) poprawia jakość interpretacji?
2. Czy **odpowiedzi na pytania** (nie tylko wynik liczbowy) dają lepsze interpretacje?

Ewaluatorzy oceniają interpretacje w teście blind A/B (48 par do oceny).

---

## Architektura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OpenAI API    │────▶│    Supabase     │◀────│   Streamlit UI  │
│   (GPT-4o)      │     │   (PostgreSQL)  │     │   (Ewaluacja)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Struktura projektu

```
prompt-validation/
├── data/
│   ├── instruments_extended.json # Instrumenty kliniczne (PHQ-9, GAD-7, etc.)
│   ├── user_profiles_v2.json     # 4 profile użytkowników z subtematami
│   └── questionnaire_items.json  # Pytania PHQ-9 i GAD-7
├── prompts/
│   ├── variant_minimal.jinja2    # Minimalny kontekst (imię, wiek, płeć)
│   ├── variant_profile.jinja2    # Pełny profil z subtematami
│   ├── variant_answers.jinja2    # Pełny profil + odpowiedzi na pytania
│   ├── variant_kasia_phq9.jinja2 # Referencja: prompt Kasi dla PHQ-9
│   └── variant_kasia_gad7.jinja2 # Referencja: prompt Kasi dla GAD-7
├── scripts/
│   ├── generate_interpretations.py # Generuje interpretacje przez GPT
│   ├── test_templates.py           # Test szablonów (bez API)
│   ├── analysis.py                 # Analiza wyników ewaluacji
│   └── setup_supabase.py           # Generuje SQL do utworzenia tabel
├── app/
│   └── streamlit_app.py    # Aplikacja do ewaluacji blind A/B
├── venv/                   # Virtual environment Python
└── requirements.txt        # Zależności Python
```

---

## Warianty promptów (V3)

| Wariant | Dane użytkownika | Dane wejściowe | Cel testu |
|---------|------------------|----------------|-----------|
| **minimal** | imię, wiek, płeć | wynik + poziom | Baseline |
| **profile** | + praca, lider, ~15 subtematów | wynik + poziom | Czy kontekst pomaga? |
| **answers** | + praca, lider, ~15 subtematów | wynik + odpowiedzi na pytania | Czy odpowiedzi pomagają? |

### Kluczowe porównania (48 par)

1. **minimal vs profile** → Czy pełny profil użytkownika poprawia jakość?
2. **profile vs answers** → Czy odpowiedzi na pytania dają lepsze interpretacje?
3. **minimal vs answers** → Pełne porównanie: minimum vs maksimum informacji

---

## Profile użytkowników

| ID | Imię | Wiek | Stanowisko | Typ pracy | Lider | Subtematów |
|----|------|------|------------|-----------|-------|------------|
| 1 | Ania | 28 | marketing manager | umysłowa | nie | 15 |
| 2 | Tomek | 38 | kierownik IT | umysłowa | tak | 15 |
| 3 | Magda | 42 | pielęgniarka | fizyczna | nie | 15 |
| 4 | Marek | 50 | brygadzista magazynu | fizyczna | tak | 16 |

---

## Przypadki testowe

| Instrument | Poziom | Wynik |
|------------|--------|-------|
| PHQ-9 | moderate | 12 |
| PHQ-9 | severe | 20 |
| GAD-7 | moderate | 10 |
| GAD-7 | severe | 17 |

**Kalkulacja:** 4 profile × 2 instrumenty × 2 poziomy × 3 warianty = **48 interpretacji**

---

## Baza danych (Supabase)

### Tabela: `interpretations`

| Kolumna | Typ | Opis |
|---------|-----|------|
| id | UUID | Primary key |
| instrument_code | TEXT | PHQ-9, GAD-7 |
| score | INTEGER | Wynik testu |
| level | TEXT | moderate, severe |
| prompt_variant | TEXT | minimal, profile, answers |
| user_profile_id | INTEGER | ID profilu (1-4) |
| interpretation_text | TEXT | Wygenerowana interpretacja |
| model | TEXT | Model LLM (gpt-4o) |
| created_at | TIMESTAMPTZ | Data utworzenia |

### Tabela: `evaluations`

| Kolumna | Typ | Opis |
|---------|-----|------|
| id | UUID | Primary key |
| interpretation_id | UUID | FK do interpretations (zwycięzca) |
| preferred_over | UUID | FK do przegranej interpretacji |
| evaluator_name | TEXT | Imię/nick ewaluatora |
| rating | INTEGER | 1-5 (jak bardzo lepsza) |
| feedback | TEXT | Opcjonalny komentarz |
| created_at | TIMESTAMPTZ | Data oceny |

---

## Komendy

### Aktywacja środowiska

```bash
cd /Users/adamplona/AI/features/diagnostics/prompt-validation
source venv/bin/activate
```

### Test szablonów (bez API)

```bash
python scripts/test_templates.py
```

### Generacja interpretacji

```bash
# Dry-run (3 próbki, bez zapisu do DB)
python scripts/generate_interpretations.py --dry-run

# Pełna generacja (48 interpretacji)
python scripts/generate_interpretations.py
```

### Uruchomienie aplikacji Streamlit

```bash
streamlit run app/streamlit_app.py
```

### Analiza wyników

```bash
python scripts/analysis.py
```

---

## Zmienne środowiskowe

Zapisane w `~/.zshrc`:

```bash
export OPENAI_API_KEY="sk-proj-..."
export SUPABASE_URL="https://crhulfzhwybxpkoxkxmr.supabase.co"
export SUPABASE_KEY="sb_secret_..."
```

---

## Deploy na Streamlit Cloud

**URL:** https://prompt-validation-jb7ey4wgzuvhbforapp4mqf.streamlit.app/

Auto-deploy z brancha `main` po każdym pushu.

---

## Kontakt

Projekt dla Mindgram - walidacja promptów diagnostycznych.
Właściciel: Adam Plona (adam@mindgram.com)
