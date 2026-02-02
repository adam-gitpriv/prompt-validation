"""
Streamlit app for blind A/B evaluation of diagnostic interpretations.
"""
import os
import random
import streamlit as st
from supabase import create_client

# Config - support both env vars and Streamlit secrets
def get_config(key: str) -> str:
    """Get config from env vars or Streamlit secrets."""
    # First try environment variables
    value = os.environ.get(key)
    if value:
        return value
    # Then try Streamlit secrets
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return None

SUPABASE_URL = get_config("SUPABASE_URL")
SUPABASE_KEY = get_config("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Brak konfiguracji Supabase. Ustaw SUPABASE_URL i SUPABASE_KEY w zmiennych srodowiskowych lub Streamlit secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Page config
st.set_page_config(
    page_title="Walidacja Promptów - Diagnostyka",
    page_icon="🧠",
    layout="wide"
)

# Session state
if "evaluator_name" not in st.session_state:
    st.session_state.evaluator_name = None
if "current_pair" not in st.session_state:
    st.session_state.current_pair = None
if "evaluated_count" not in st.session_state:
    st.session_state.evaluated_count = 0


def get_random_pair():
    """Get two random interpretations for the same instrument/score to compare."""
    # Get all unique instrument+score combinations
    result = supabase.table("interpretations").select(
        "instrument_code, score, level"
    ).execute()

    if not result.data:
        return None

    # Get unique combinations
    combinations = list(set(
        (r["instrument_code"], r["score"], r["level"])
        for r in result.data
    ))

    if not combinations:
        return None

    # Pick random combination
    instrument, score, level = random.choice(combinations)

    # Get two random interpretations for this combination (different variants)
    interpretations = supabase.table("interpretations").select("*").eq(
        "instrument_code", instrument
    ).eq("score", score).execute()

    if len(interpretations.data) < 2:
        return None

    # Pick two random different variants
    pair = random.sample(interpretations.data, 2)
    random.shuffle(pair)  # Randomize order (blind)

    return pair


def save_evaluation(interpretation_id: str, preferred_id: str, rating: int, feedback: str):
    """Save evaluation to Supabase."""
    supabase.table("evaluations").insert({
        "interpretation_id": interpretation_id,
        "evaluator_name": st.session_state.evaluator_name,
        "rating": rating,
        "preferred_over": preferred_id if preferred_id != interpretation_id else None,
        "feedback": feedback
    }).execute()


def get_stats():
    """Get evaluation statistics."""
    # Total evaluations
    evals = supabase.table("evaluations").select("*").execute()

    # By variant
    interps = supabase.table("interpretations").select("id, prompt_variant").execute()
    variant_map = {i["id"]: i["prompt_variant"] for i in interps.data}

    variant_wins = {}
    for e in evals.data:
        if e.get("preferred_over"):
            winner_variant = variant_map.get(e["interpretation_id"])
            if winner_variant:
                variant_wins[winner_variant] = variant_wins.get(winner_variant, 0) + 1

    return {
        "total_evaluations": len(evals.data),
        "variant_wins": variant_wins
    }


# Main UI
st.title("🧠 Walidacja Promptów Diagnostycznych")
st.markdown("Porównaj interpretacje i wybierz lepszą. Nie wiesz, który wariant promptu wygenerował którą odpowiedź.")

# Login
if not st.session_state.evaluator_name:
    st.subheader("Zaloguj się")
    name = st.text_input("Twoje imię lub nick:")
    if st.button("Rozpocznij ewaluację") and name:
        st.session_state.evaluator_name = name.strip()
        st.rerun()
    st.stop()

# Sidebar - stats & logout
with st.sidebar:
    st.markdown(f"**Ewaluator:** {st.session_state.evaluator_name}")
    st.markdown(f"**Ocenione pary:** {st.session_state.evaluated_count}")

    if st.button("Wyloguj"):
        st.session_state.evaluator_name = None
        st.session_state.current_pair = None
        st.rerun()

    st.divider()
    st.subheader("Statystyki")
    stats = get_stats()
    st.metric("Łączne oceny", stats["total_evaluations"])

    if stats["variant_wins"]:
        st.markdown("**Wygrane wariantów:**")
        for variant, wins in sorted(stats["variant_wins"].items(), key=lambda x: -x[1]):
            st.markdown(f"- Wariant {variant}: {wins}")

# Get or load pair
if st.session_state.current_pair is None:
    st.session_state.current_pair = get_random_pair()

pair = st.session_state.current_pair

if not pair:
    st.warning("Brak interpretacji do oceny. Najpierw wygeneruj dane.")
    st.stop()

# Display context
st.subheader(f"Instrument: {pair[0]['instrument_code']} | Wynik: {pair[0]['score']} | Poziom: {pair[0]['level']}")

# Display two interpretations side by side
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Interpretacja A")
    st.info(pair[0]["interpretation_text"])

with col2:
    st.markdown("### Interpretacja B")
    st.info(pair[1]["interpretation_text"])

# Evaluation form
st.divider()
st.subheader("Twoja ocena")

choice = st.radio(
    "Która interpretacja jest lepsza?",
    ["A jest lepsza", "B jest lepsza", "Obie równie dobre"],
    horizontal=True
)

rating = st.slider(
    "Jak bardzo lepsza? (1 = minimalnie, 5 = znacznie)",
    min_value=1,
    max_value=5,
    value=3,
    disabled=(choice == "Obie równie dobre")
)

feedback = st.text_area("Opcjonalny komentarz:", placeholder="Co sprawia, że ta interpretacja jest lepsza?")

if st.button("Zapisz ocenę i pokaż następną parę", type="primary"):
    # Determine winner
    if choice == "A jest lepsza":
        winner_id = pair[0]["id"]
        loser_id = pair[1]["id"]
    elif choice == "B jest lepsza":
        winner_id = pair[1]["id"]
        loser_id = pair[0]["id"]
    else:
        winner_id = pair[0]["id"]
        loser_id = None
        rating = 3

    # Save
    save_evaluation(winner_id, loser_id, rating, feedback)
    st.session_state.evaluated_count += 1
    st.session_state.current_pair = None  # Load new pair
    st.success("Zapisano! Ładuję następną parę...")
    st.rerun()

# Skip button
if st.button("Pomiń tę parę"):
    st.session_state.current_pair = None
    st.rerun()
