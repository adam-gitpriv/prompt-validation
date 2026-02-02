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
│   ├── instruments.json          # Definicje instrumentów klinicznych
│   ├── instruments_extended.json # Rozszerzone metadane instrumentów
│   ├── user_profiles.json        # 10 profili użytkowników testowych
│   └── prompt_variants_v2.json   # 7 wariantów promptów (A-G)
├── prompts/
│   ├── variant_a_structural.jinja2   # Wariant strukturalny
│   ├── variant_b_clinical.jinja2     # Wariant kliniczny
│   ├── variant_c_personalized.jinja2 # Wariant personalizowany
│   ├── variant_d_fewshot.jinja2      # Wariant few-shot (rekomendowany)
│   ├── variant_e_cot.jinja2          # Wariant chain-of-thought
│   ├── variant_kasia_phq9.jinja2     # Wariant Kasi dla PHQ-9
│   └── variant_kasia_gad7.jinja2     # Wariant Kasi dla GAD-7
├── scripts/
│   ├── setup_supabase.py             # Generuje SQL do utworzenia tabel
│   ├── generate_interpretations.py   # Generuje interpretacje przez GPT
│   └── analysis.py                   # Analiza wyników ewaluacji
├── app/
│   └── streamlit_app.py      # Aplikacja do ewaluacji blind A/B
├── venv/                     # Virtual environment Python
├── requirements.txt          # Zależności Python
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

Prompty generują pełną strukturę interpretacji zgodną z designem w Figmie.

### Warianty uniwersalne (wszystkie instrumenty)

| Wariant | Plik | Kiedy używać |
|---------|------|--------------|
| **A - Strukturalny** | `variant_a_structural.jinja2` | Domyślny, najbezpieczniejszy |
| **B - Kliniczny** | `variant_b_clinical.jinja2` | Gdy zależy na merytoryce klinicznej |
| **C - Personalizowany** | `variant_c_personalized.jinja2` | Gdy mamy profil użytkownika |
| **D - Few-shot** | `variant_d_fewshot.jinja2` | **REKOMENDOWANY** - najbardziej spójny |
| **E - Chain-of-Thought** | `variant_e_cot.jinja2` | Dla edge cases, najwyższa jakość |

### Warianty specyficzne dla instrumentów (Kasia)

| Wariant | Plik | Instrument |
|---------|------|------------|
| **F - Kasia PHQ-9** | `variant_kasia_phq9.jinja2` | Tylko PHQ-9 |
| **G - Kasia GAD-7** | `variant_kasia_gad7.jinja2` | Tylko GAD-7 |

### Output v2 (zgodny z Figma)

```json
{
  "headline": "Twój wynik wskazuje [poziom] [objawy obszaru]",
  "summary": {
    "level_meaning": "Co zwykle oznacza ten poziom: ...",
    "daily_impact": "Wpływ na codzienność: ...",
    "warning_signs": "Na co uważać: ..."
  },
  "interpretation": "2-3 akapity rozbudowanej interpretacji...",
  "comparison_to_previous": "Porównanie do poprzednich lub null",
  "recommendations": ["5-6 konkretnych rekomendacji"],
  "specialist_recommendation": {
    "recommended": true/false,
    "urgency": "low/medium/high",
    "type": "chat/consultation"
  }
}
```

**Dokumentacja v2:** `prompts/PROMPTY_INTERPRETACJI_v2.md`
**Metadane:** `data/prompt_variants_v2.json`
**Instrumenty rozszerzone:** `data/instruments_extended.json`

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

## Deploy na Streamlit Cloud

### Aktualna konfiguracja (LIVE)

**Publiczny URL:** https://prompt-validation-jb7ey4wgzuvhbforapp4mqf.streamlit.app/

**Status:** Aplikacja jest wdrożona i działa publicznie.

| Parametr | Wartość |
|----------|---------|
| **Repository** | `adam-gitpriv/prompt-validation` (publiczne) |
| **Branch** | `main` |
| **Main file** | `app/streamlit_app.py` |
| **Python** | 3.13 |
| **Konto Streamlit** | adam-gitpriv (GitHub OAuth) |

### Secrets (skonfigurowane w Streamlit Cloud)

```toml
SUPABASE_URL = "https://crhulfzhwybxpkoxkxmr.supabase.co"
SUPABASE_KEY = "sb_secret_JsAs7L1v7L0mUho_3SYeIA_o-zOBcs6"
```

### Zarządzanie aplikacją

1. **Panel admina:** https://share.streamlit.io → My apps → prompt-validation
2. **Logi:** W panelu admina → Manage app → Logs
3. **Restart:** Manage app → Reboot app
4. **Secrets:** Settings → Secrets (format TOML)

### Redeploy po zmianach

Streamlit Cloud automatycznie wykrywa zmiany w repozytorium GitHub i redeplojuje aplikację po każdym pushu do brancha `main`.

```bash
# Wystarczy:
git add . && git commit -m "Update" && git push
# Aplikacja się automatycznie przebuduje
```

### Troubleshooting Streamlit Cloud

| Problem | Rozwiązanie |
|---------|-------------|
| Aplikacja nie startuje | Sprawdź logi w panelu admina |
| Błąd Supabase | Zweryfikuj Secrets w Settings |
| Stara wersja | Kliknij "Reboot app" w Manage app |
| Zmiana secrets | Po edycji secrets kliknij "Reboot app" |

---

## Kontakt

Projekt dla Mindgram - walidacja promptów diagnostycznych.
Właściciel: Adam Plona (adam@mindgram.com)
