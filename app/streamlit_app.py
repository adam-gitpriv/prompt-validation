"""
Streamlit app for blind A/B evaluation of diagnostic interpretations.
"""
import os
import random
import streamlit as st
from supabase import create_client
from collections import Counter

# User profiles with full data
USER_PROFILES = {
    1: {
        "name": "Ania", "age": 28, "gender": "K", "work_type": "umysłowa", "is_leader": False,
        "subtopics": ["Zarządzanie stresem", "Poprawa snu", "Uważność na co dzień", "Relacje z partnerem",
                      "Poczucie własnej wartości", "Syndrom Oszusta", "Efektywna komunikacja w pracy",
                      "Motywacja i produktywność", "Zdrowa dieta", "Ćwiczenia oddechowe", "Trening cardio",
                      "Inteligencja emocjonalna", "Budowanie zdolności kredytowej", "Wyciszenie przed snem", "Higiena cyfrowa"]
    },
    2: {
        "name": "Tomek", "age": 38, "gender": "M", "work_type": "umysłowa", "is_leader": True,
        "subtopics": ["Wypalenie zawodowe", "Efektywne zarządzanie czasem", "Motywowanie pracowników",
                      "Efektywny feedback", "Zarządzanie zmianą", "Rozwiązywanie konfliktów w zespole",
                      "Zarządzanie stresem", "Radzenie sobie z lękiem", "Poprawa snu", "Relacje z nastolatkami (13-18)",
                      "Wczesne rodzicielstwo (0-5)", "Planowanie emerytury", "Podstawy inwestowania",
                      "Neuroróżnorodność w zespole", "Coaching i mentoring"]
    },
    3: {
        "name": "Magda", "age": 42, "gender": "K", "work_type": "fizyczna", "is_leader": False,
        "subtopics": ["Higiena snu dla pracowników zmianowych", "Radzenie sobie z lękiem", "Życie z chorobą przewlekłą",
                      "Odżywianie dla pracowników zmianowych", "Bezpieczeństwo i zapobieganie urazom",
                      "Ćwiczenia dla pracowników fizycznych", "Opieka nad seniorami", "Opieka nad chorymi i niepełnosprawnymi",
                      "Żałoba i Strata", "Radzenie sobie z traumą", "Zarządzanie domowym budżetem", "Zdrowie kobiety",
                      "Relacje z dziećmi (6-12)", "Wypalenie rodzicielskie", "Depresja"]
    },
    4: {
        "name": "Marek", "age": 50, "gender": "M", "work_type": "fizyczna", "is_leader": True,
        "subtopics": ["Ćwiczenia dla pracowników fizycznych", "Zarządzanie wypaleniem w zespole", "Zdrowe nawyki",
                      "Rozciąganie i mobilność", "Trening siłowy", "Zdrowie mężczyzny", "Ograniczanie alkoholu",
                      "Rzucanie palenia", "Zarządzanie zespołami zdalnymi", "Różnorodność pokoleniowa w zespole",
                      "Efektywna praca zdalna i hybrydowa", "Rozwiązywanie konfliktów w pracy", "Wychodzenie z długów",
                      "Strategie oszczędzania", "Kryzys w pracy", "Relacje z partnerem"]
    },
}

LEVEL_PL = {
    "minimal": "Minimalny",
    "mild": "Łagodny",
    "moderate": "Umiarkowany",
    "moderately_severe": "Umiarkowanie ciężki",
    "severe": "Ciężki",
}

GENDER_PL = {"K": "Kobieta", "M": "Mężczyzna"}

# Prompt descriptions
PROMPT_DESCRIPTIONS = {
    "minimal": {
        "name": "Minimal",
        "desc": "Podstawowe dane użytkownika (imię, wiek, płeć) + wynik i poziom. Bez kontekstu pracy i zainteresowań.",
        "data": "imię, wiek, płeć, wynik, poziom"
    },
    "profile": {
        "name": "Profile",
        "desc": "Pełny profil użytkownika z kontekstem pracy i zainteresowaniami. Prompt zachęca do personalizacji.",
        "data": "imię, wiek, płeć, praca, lider, ~15 zainteresowań, wynik, poziom"
    },
    "answers": {
        "name": "Answers",
        "desc": "Pełny profil + indywidualne odpowiedzi na pytania kwestionariusza. Prompt analizuje wzorce odpowiedzi.",
        "data": "imię, wiek, płeć, praca, lider, ~15 zainteresowań, wynik, poziom + odpowiedzi na każde pytanie"
    },
    "kasia_phq9": {
        "name": "Kasia PHQ-9",
        "desc": "Prompt kliniczny od psychologa (Kasia) dla PHQ-9. Strukturyzowany format, wytyczne kliniczne, kontekst pracy.",
        "data": "imię, wiek, płeć, praca, wynik, poziom (wytyczne kliniczne w prompcie)"
    },
    "kasia_gad7": {
        "name": "Kasia GAD-7",
        "desc": "Prompt kliniczny od psychologa (Kasia) dla GAD-7. Strukturyzowany format, wytyczne kliniczne, kontekst pracy.",
        "data": "imię, wiek, płeć, praca, wynik, poziom (wytyczne kliniczne w prompcie)"
    },
}


def get_config(key: str) -> str:
    value = os.environ.get(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return None


SUPABASE_URL = get_config("SUPABASE_URL")
SUPABASE_KEY = get_config("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Brak konfiguracji Supabase.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Page config - wide layout, no sidebar
st.set_page_config(
    page_title="Walidacja Promptów",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide sidebar completely
st.markdown("""
<style>
    [data-testid="collapsedControl"] { display: none; }
    section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# Session state
if "evaluator_name" not in st.session_state:
    st.session_state.evaluator_name = None
if "current_pair" not in st.session_state:
    st.session_state.current_pair = None
if "evaluated_count" not in st.session_state:
    st.session_state.evaluated_count = 0
if "page" not in st.session_state:
    st.session_state.page = "evaluate"


def get_random_pair():
    """Get two random interpretations for the same instrument/score/profile to compare."""
    result = supabase.table("interpretations").select(
        "instrument_code, score, level, user_profile_id"
    ).in_("instrument_code", ["PHQ-9", "GAD-7"]).execute()

    if not result.data:
        return None

    combinations = list(set(
        (r["instrument_code"], r["score"], r["level"], r["user_profile_id"])
        for r in result.data
    ))

    if not combinations:
        return None

    instrument, score, level, user_profile_id = random.choice(combinations)

    interpretations = supabase.table("interpretations").select("*").eq(
        "instrument_code", instrument
    ).eq("score", score).eq("user_profile_id", user_profile_id).execute()

    if len(interpretations.data) < 2:
        return None

    pair = random.sample(interpretations.data, 2)
    random.shuffle(pair)
    return pair


def save_evaluation(winner_id: str, loser_id: str | None):
    """Save evaluation to Supabase."""
    supabase.table("evaluations").insert({
        "interpretation_id": winner_id,
        "evaluator_name": st.session_state.evaluator_name,
        "rating": 3,
        "preferred_over": loser_id,
        "feedback": ""
    }).execute()


def get_stats():
    """Get detailed statistics."""
    # Get all evaluations
    evals = supabase.table("evaluations").select("*").execute()

    # Get all interpretations for variant mapping
    interps = supabase.table("interpretations").select("id, prompt_variant").execute()
    variant_map = {i["id"]: i["prompt_variant"] for i in interps.data}

    # Count wins per variant
    variant_wins = Counter()
    variant_losses = Counter()
    variant_ties = Counter()
    head_to_head = {}  # (winner, loser) -> count

    for e in evals.data:
        winner_variant = variant_map.get(e["interpretation_id"])
        loser_id = e.get("preferred_over")

        if loser_id:
            loser_variant = variant_map.get(loser_id)
            if winner_variant and loser_variant:
                variant_wins[winner_variant] += 1
                variant_losses[loser_variant] += 1
                key = (winner_variant, loser_variant)
                head_to_head[key] = head_to_head.get(key, 0) + 1
        else:
            # Tie
            if winner_variant:
                variant_ties[winner_variant] += 1

    return {
        "total_evaluations": len(evals.data),
        "variant_wins": dict(variant_wins),
        "variant_losses": dict(variant_losses),
        "variant_ties": dict(variant_ties),
        "head_to_head": head_to_head,
        "evaluators": Counter(e["evaluator_name"] for e in evals.data)
    }


# === LOGIN ===
if not st.session_state.evaluator_name:
    st.title("🧠 Walidacja Promptów Diagnostycznych")
    st.markdown("---")
    name = st.text_input("Twoje imię lub nick:")
    col_login1, col_login2 = st.columns(2)
    with col_login1:
        if st.button("Rozpocznij ocenianie", type="primary", use_container_width=True) and name:
            st.session_state.evaluator_name = name.strip()
            st.rerun()
    with col_login2:
        if st.button("📊 Zobacz wyniki", use_container_width=True):
            st.session_state.evaluator_name = "Gość"
            st.session_state.page = "results"
            st.rerun()
    st.stop()

# === HEADER WITH NAVIGATION ===
col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2, 1, 1, 1, 0.5])

with col_h1:
    st.markdown(f"### 🧠 Walidacja Promptów")

with col_h2:
    if st.button("📝 Ocenianie", use_container_width=True,
                 type="primary" if st.session_state.page == "evaluate" else "secondary"):
        st.session_state.page = "evaluate"
        st.rerun()

with col_h3:
    if st.button("📊 Wyniki", use_container_width=True,
                 type="primary" if st.session_state.page == "results" else "secondary"):
        st.session_state.page = "results"
        st.rerun()

with col_h4:
    st.markdown(f"**{st.session_state.evaluator_name}**")

with col_h5:
    if st.button("🚪", help="Wyloguj"):
        st.session_state.evaluator_name = None
        st.session_state.current_pair = None
        st.rerun()

st.markdown("---")


# === RESULTS PAGE ===
if st.session_state.page == "results":
    stats = get_stats()

    st.markdown("## Statystyki ewaluacji")

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Łączna liczba ocen", stats["total_evaluations"])
    with c2:
        st.metric("Liczba ewaluatorów", len(stats["evaluators"]))
    with c3:
        st.metric("Warianty promptów", len(set(stats["variant_wins"].keys()) | set(stats["variant_losses"].keys())))

    st.markdown("---")

    # Win rates table
    st.markdown("### Wyniki wariantów")

    all_variants = set(stats["variant_wins"].keys()) | set(stats["variant_losses"].keys()) | set(stats["variant_ties"].keys())

    if all_variants:
        rows = []
        for v in sorted(all_variants):
            wins = stats["variant_wins"].get(v, 0)
            losses = stats["variant_losses"].get(v, 0)
            ties = stats["variant_ties"].get(v, 0)
            total = wins + losses + ties
            win_rate = (wins / total * 100) if total > 0 else 0

            desc = PROMPT_DESCRIPTIONS.get(v, {})
            rows.append({
                "Wariant": v,
                "Opis": desc.get("desc", "-"),
                "Dane wejściowe": desc.get("data", "-"),
                "Wygrane": wins,
                "Przegrane": losses,
                "Remisy": ties,
                "Win Rate": f"{win_rate:.1f}%"
            })

        # Sort by win rate descending
        rows.sort(key=lambda x: float(x["Win Rate"].replace("%", "")), reverse=True)

        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Brak danych do wyświetlenia.")

    st.markdown("---")

    # Head-to-head matrix
    st.markdown("### Macierz pojedynków bezpośrednich")
    st.caption("Procent wygranych: jak często wariant z wiersza wygrywa z wariantem z kolumny")

    if stats["head_to_head"] and all_variants:
        sorted_variants = sorted(all_variants)
        matrix_data = []

        for row_var in sorted_variants:
            row = {"Wariant ↓ vs →": row_var}
            row_total_wins = 0
            row_total_matches = 0
            for col_var in sorted_variants:
                if row_var == col_var:
                    row[col_var] = "—"
                else:
                    wins = stats["head_to_head"].get((row_var, col_var), 0)
                    losses = stats["head_to_head"].get((col_var, row_var), 0)
                    total = wins + losses
                    row_total_wins += wins
                    row_total_matches += total
                    if total > 0:
                        pct = wins / total * 100
                        row[col_var] = f"{pct:.0f}%"
                    else:
                        row[col_var] = "—"
            # Add row totals
            if row_total_matches > 0:
                pct = row_total_wins / row_total_matches * 100
                row["RAZEM"] = f"{pct:.0f}%"
            else:
                row["RAZEM"] = "—"
            matrix_data.append(row)

        st.dataframe(matrix_data, use_container_width=True, hide_index=True)

        # Overall winner
        st.markdown("---")
        st.markdown("### 🏆 Ranking końcowy")

        ranking = []
        for v in sorted_variants:
            total_wins = sum(stats["head_to_head"].get((v, other), 0) for other in sorted_variants if other != v)
            total_matches = sum(
                stats["head_to_head"].get((v, other), 0) + stats["head_to_head"].get((other, v), 0)
                for other in sorted_variants if other != v
            )
            if total_matches > 0:
                win_pct = total_wins / total_matches * 100
                ranking.append((v, total_wins, total_matches, win_pct))

        ranking.sort(key=lambda x: x[3], reverse=True)

        for i, (v, wins, matches, pct) in enumerate(ranking, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            st.markdown(f"{medal} **{v}** — {wins}/{matches} wygranych ({pct:.1f}%)")
    else:
        st.info("Brak pojedynków do wyświetlenia.")

    st.markdown("---")

    # Prompt details
    st.markdown("### Szczegóły wariantów promptów (V3)")

    for variant_id, info in PROMPT_DESCRIPTIONS.items():
        with st.expander(f"**{info['name']}** - {info['desc'][:50]}..."):
            st.markdown(f"**Dane przekazywane do prompta:**")
            st.code(info["data"])
            st.markdown(f"**Opis:**")
            st.markdown(info["desc"])

    st.stop()


# === EVALUATION PAGE ===

# Load pair
if st.session_state.current_pair is None:
    st.session_state.current_pair = get_random_pair()

pair = st.session_state.current_pair

if not pair:
    st.warning("Brak interpretacji do oceny.")
    st.stop()

# Context
profile = USER_PROFILES.get(pair[0].get("user_profile_id"), {})
level_pl = LEVEL_PL.get(pair[0]["level"], pair[0]["level"])
gender_pl = GENDER_PL.get(profile.get("gender", ""), "")
leader_txt = "Tak" if profile.get("is_leader") else "Nie"

st.markdown("**DANE WEJŚCIOWE DLA PROMPTA:**")
st.markdown(f"""
**Instrument:** {pair[0]['instrument_code']} · **Wynik:** {pair[0]['score']} pkt · **Poziom:** {level_pl}

**Użytkownik:** {profile.get('name', '?')} · {gender_pl} · {profile.get('age', '?')} lat · Praca: {profile.get('work_type', '?')} · Lider: {leader_txt}

**Zainteresowania:** {', '.join(profile.get('subtopics', [])[:8])}...
""")

st.markdown("---")

# Interpretations
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Interpretacja A")
    st.info(pair[0]["interpretation_text"])

with col2:
    st.markdown("#### Interpretacja B")
    st.info(pair[1]["interpretation_text"])

# Evaluation buttons
st.markdown("---")

c1, c2, c3, c4 = st.columns([1, 1, 1, 0.5])

with c1:
    if st.button("🅰️ A jest lepsza", use_container_width=True, type="primary"):
        save_evaluation(pair[0]["id"], pair[1]["id"])
        st.session_state.evaluated_count += 1
        st.session_state.current_pair = None
        st.rerun()

with c2:
    if st.button("🟰 Remis", use_container_width=True):
        save_evaluation(pair[0]["id"], None)
        st.session_state.evaluated_count += 1
        st.session_state.current_pair = None
        st.rerun()

with c3:
    if st.button("🅱️ B jest lepsza", use_container_width=True, type="primary"):
        save_evaluation(pair[1]["id"], pair[0]["id"])
        st.session_state.evaluated_count += 1
        st.session_state.current_pair = None
        st.rerun()

with c4:
    if st.button("⏭️ Pomiń", use_container_width=True):
        st.session_state.current_pair = None
        st.rerun()
