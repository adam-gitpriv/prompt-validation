# Deploy na Streamlit Cloud

## Krok 1: Zaloguj się na Streamlit Cloud

1. Otwórz: https://share.streamlit.io
2. Zaloguj się przez GitHub (adam-gitpriv)

## Krok 2: Utwórz nową aplikację

1. Kliknij "New app"
2. Wybierz repo: `adam-gitpriv/prompt-validation`
3. Branch: `main`
4. Main file path: `app/streamlit_app.py`

## Krok 3: Skonfiguruj Secrets

W ustawieniach aplikacji (Settings > Secrets) dodaj:

```toml
SUPABASE_URL = "https://crhulfzhwybxpkoxkxmr.supabase.co"
SUPABASE_KEY = "sb_secret_JsAs7L1v7L0mUho_3SYeIA_o-zOBcs6"
```

## Krok 4: Deploy

Kliknij "Deploy!" - aplikacja będzie dostępna pod adresem:
`https://prompt-validation.streamlit.app` (lub podobnym)

## Alternatywa: Uruchom lokalnie

```bash
cd /Users/adamplona/AI/features/diagnostics/prompt-validation
source venv/bin/activate
streamlit run app/streamlit_app.py
```

Aplikacja będzie dostępna na: http://localhost:8501
