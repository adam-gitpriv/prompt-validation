# Prompt Validation - Diagnostyka Mindgram

Narzędzie do walidacji promptów generujących interpretacje wyników diagnostycznych w aplikacji Mindgram.

## Cel projektu

Zbadać, jak **personalizacja promptów** (wiek, płeć, zawód, zainteresowania) wpływa na jakość generowanych interpretacji wyników kwestionariuszy klinicznych. Ewaluatorzy (Kasia + zespół) oceniają interpretacje w teście blind A/B.

---

## Architektura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OpenAI API    │────▶│    Supabase     │◀────│   Streamlit UI  │
│   (GPT-4o)      │     │   (PostgreSQL)  │     │   (Ewaluacja)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

- **OpenAI GPT-4o** - generuje interpretacje na podstawie promptów
- **Supabase** - przechowuje interpretacje i oceny ewaluatorów
- **Streamlit** - UI do blind A/B testów

---

## Struktura projektu

```
prompt-validation/
├── data/
│   ├── instruments.json      # Definicje instrumentów klinicznych
│   ├── user_profiles.json    # 10 profili użytkowników testowych
│   └── prompt_variants.json  # 6 wariantów promptów (A-F)
├── prompts/
│   └── base.jinja2           # Szablon Jinja2 z warunkowymi sekcjami
├── scripts/
│   ├── setup_supabase.py     # Generuje SQL do utworzenia tabel
│   └── generate_interpretations.py  # Generuje interpretacje przez GPT
├── app/
│   └── streamlit_app.py      # Aplikacja do ewaluacji blind A/B
├── venv/                     # Virtual environment Python
├── requirements.txt          # Zależności Python
├── .env.example              # Przykładowe zmienne środowiskowe
└── README.md                 # Ta dokumentacja
```

---

## Instrumenty kliniczne

| Kod | Nazwa | Domena | Poziomy |
|-----|-------|--------|---------|
| **PHQ-9** | Patient Health Questionnaire-9 | Depresja | 5 (0-4, 5-9, 10-14, 15-19, 20-27) |
| **GAD-7** | Generalized Anxiety Disorder-7 | Lęk | 4 (0-4, 5-9, 10-14, 15-21) |
| **MAST** | Michigan Alcohol Screening Test | Alkohol | 3 (0-2, 3-5, 6-22) |

Szczegóły w `data/instruments.json`.

---

## Warianty promptów

| ID | Nazwa | Zawiera w prompcie |
|----|-------|-------------------|
| **A** | base | Tylko wynik testu |
| **B** | age_gender | + wiek, płeć |
| **C** | work | + wiek, płeć, zawód |
| **D** | interests | + wiek, płeć, zainteresowania |
| **E** | work_interests | + wiek, płeć, zawód, zainteresowania |
| **F** | full_context | Wszystko (= E, alias) |

Logika wariantów w `prompts/base.jinja2` (Jinja2 z `{% if include_X %}`).

---

## Baza danych (Supabase)

### Tabela: `interpretations`

| Kolumna | Typ | Opis |
|---------|-----|------|
| id | UUID | Primary key |
| instrument_code | TEXT | PHQ-9, GAD-7, MAST |
| score | INTEGER | Wynik testu |
| level | TEXT | minimal, mild, moderate, severe, etc. |
| prompt_variant | TEXT | A, B, C, D, E, F |
| user_profile_id | INTEGER | ID profilu z user_profiles.json |
| interpretation_text | TEXT | Wygenerowana interpretacja |
| model | TEXT | Model LLM (gpt-4o) |
| created_at | TIMESTAMPTZ | Data utworzenia |

### Tabela: `evaluations`

| Kolumna | Typ | Opis |
|---------|-----|------|
| id | UUID | Primary key |
| interpretation_id | UUID | FK do interpretations |
| evaluator_name | TEXT | Imię/nick ewaluatora |
| rating | INTEGER | 1-5 (jak bardzo lepsza) |
| preferred_over | UUID | FK do przegranej interpretacji |
| feedback | TEXT | Opcjonalny komentarz |
| created_at | TIMESTAMPTZ | Data oceny |

---

## Zmienne środowiskowe

Zapisane w `~/.zshrc`:

```bash
export OPENAI_API_KEY="sk-proj-..."
export SUPABASE_URL="https://crhulfzhwybxpkoxkxmr.supabase.co"
export SUPABASE_KEY="sb_secret_..."
```

Po zmianach: `source ~/.zshrc`

---

## Komendy

### 1. Aktywacja środowiska

```bash
cd /Users/adamplona/AI/features/diagnostics/prompt-validation
source venv/bin/activate
```

### 2. Uruchomienie aplikacji Streamlit

```bash
source venv/bin/activate
streamlit run app/streamlit_app.py
```

Otwórz: http://localhost:8501

### 3. Regeneracja interpretacji (jeśli potrzeba)

```bash
# Dry-run (3 próbki, bez zapisu do DB)
python scripts/generate_interpretations.py --dry-run

# Pełna generacja (~216 interpretacji)
python scripts/generate_interpretations.py
```

**Uwaga:** Przed regeneracją wyczyść tabelę `interpretations` w Supabase SQL Editor:
```sql
TRUNCATE TABLE interpretations CASCADE;
```

### 4. Sprawdzenie stanu tabel Supabase

```bash
python scripts/setup_supabase.py
```

---

## Jak działa ewaluacja (UI)

1. **Login** - ewaluator wpisuje imię/nick
2. **Porównanie** - wyświetlane są 2 interpretacje (A vs B) dla tego samego wyniku testu
   - Ewaluator **nie wie** który wariant promptu wygenerował którą interpretację (blind test)
3. **Ocena** - wybór lepszej interpretacji + ocena 1-5 (jak bardzo lepsza)
4. **Feedback** - opcjonalny komentarz
5. **Statystyki** - sidebar pokazuje ile ocen i które warianty wygrywają

---

## Analiza wyników

### SQL do analizy w Supabase

```sql
-- Ile razy wygrał każdy wariant
SELECT
  i.prompt_variant,
  COUNT(*) as wins
FROM evaluations e
JOIN interpretations i ON e.interpretation_id = i.id
WHERE e.preferred_over IS NOT NULL
GROUP BY i.prompt_variant
ORDER BY wins DESC;

-- Średnia ocena per wariant
SELECT
  i.prompt_variant,
  AVG(e.rating) as avg_rating,
  COUNT(*) as total_evals
FROM evaluations e
JOIN interpretations i ON e.interpretation_id = i.id
GROUP BY i.prompt_variant
ORDER BY avg_rating DESC;

-- Oceny per ewaluator
SELECT
  evaluator_name,
  COUNT(*) as evaluations
FROM evaluations
GROUP BY evaluator_name;
```

---

## Dane testowe

### Profile użytkowników (`data/user_profiles.json`)

10 profili z różnorodnością:
- Wiek: 26-50 lat
- Płeć: K/M
- Zawody: marketing manager, programista, nauczycielka, handlowiec, graficzka, kierownik projektu, pielęgniarka, analityk danych, prawniczka, przedsiębiorca
- Zainteresowania: joga, gry, bieganie, sztuka, fitness, szachy, itp.

### Wygenerowane interpretacje

- **216 interpretacji** w bazie
- 3 instrumenty × ~4 poziomy × 6 wariantów × 3 profile
- Model: GPT-4o
- Język: polski

---

## Troubleshooting

### Streamlit nie startuje

```bash
# Sprawdź czy venv aktywny
which python  # powinno być .../venv/bin/python

# Sprawdź zmienne środowiskowe
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

### Błąd połączenia z Supabase

```bash
# Zweryfikuj klucze
python scripts/setup_supabase.py
```

### Brak interpretacji w UI

```sql
-- Sprawdź w Supabase SQL Editor
SELECT COUNT(*) FROM interpretations;
```

### Regeneracja od zera

```sql
-- W Supabase SQL Editor
TRUNCATE TABLE evaluations CASCADE;
TRUNCATE TABLE interpretations CASCADE;
```

Następnie: `python scripts/generate_interpretations.py`

---

## Deploy na Streamlit Cloud (opcjonalnie)

1. Push do GitHub repo
2. https://share.streamlit.io → New app
3. Dodaj secrets:
   ```toml
   SUPABASE_URL = "https://..."
   SUPABASE_KEY = "sb_secret_..."
   ```
4. Deploy

---

## Kontakt

Projekt dla Mindgram - walidacja promptów diagnostycznych.
Właściciel: Adam Plona (adam@mindgram.com)
