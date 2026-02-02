# Deploy na Streamlit Cloud

## Status: WDROŻONE

**Publiczny URL:** https://prompt-validation-jb7ey4wgzuvhbforapp4mqf.streamlit.app/

Data wdrożenia: 2026-02-02

---

## Konfiguracja

| Parametr | Wartość |
|----------|---------|
| Repository | `adam-gitpriv/prompt-validation` |
| Visibility | **Publiczne** |
| Branch | `main` |
| Main file | `app/streamlit_app.py` |
| Python | 3.13 |
| Konto Streamlit | adam-gitpriv (GitHub OAuth) |

---

## Secrets (w Streamlit Cloud)

```toml
SUPABASE_URL = "https://crhulfzhwybxpkoxkxmr.supabase.co"
SUPABASE_KEY = "sb_secret_JsAs7L1v7L0mUho_3SYeIA_o-zOBcs6"
```

---

## Jak zarządzać

### Panel admina
https://share.streamlit.io → Zaloguj przez GitHub (adam-gitpriv) → My apps

### Dostępne akcje
- **Logs** - podgląd logów aplikacji
- **Reboot app** - restart (po zmianie secrets)
- **Settings** - edycja secrets, Python version
- **Delete** - usunięcie aplikacji

### Auto-redeploy
Każdy push do `main` automatycznie triggeruje redeploy.

---

## Uruchomienie lokalne (alternatywa)

```bash
cd /Users/adamplona/AI/features/diagnostics/prompt-validation
source venv/bin/activate
streamlit run app/streamlit_app.py
```

Aplikacja lokalna: http://localhost:8501
