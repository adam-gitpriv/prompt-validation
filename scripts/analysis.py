#!/usr/bin/env python3
"""
Analysis script for prompt validation evaluations.
Calculates win rates, generates ranking, and produces summary report.
"""
import os
from collections import defaultdict
from supabase import create_client

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_evaluations():
    """Fetch all evaluations from Supabase."""
    result = supabase.table("evaluations").select("*").execute()
    return result.data


def fetch_interpretations():
    """Fetch all interpretations from Supabase."""
    result = supabase.table("interpretations").select(
        "id, prompt_variant, instrument_code, score, level"
    ).execute()
    return {i["id"]: i for i in result.data}


def calculate_win_rates(evaluations, interpretations):
    """
    Calculate win rate for each prompt variant.
    Win rate = (wins) / (wins + losses)
    """
    variant_wins = defaultdict(int)
    variant_losses = defaultdict(int)
    variant_ties = defaultdict(int)

    for eval_record in evaluations:
        winner_id = eval_record.get("interpretation_id")
        loser_id = eval_record.get("preferred_over")

        if not winner_id:
            continue

        winner_interp = interpretations.get(winner_id)
        if not winner_interp:
            continue

        winner_variant = winner_interp["prompt_variant"]

        if loser_id:
            # Clear winner
            loser_interp = interpretations.get(loser_id)
            if loser_interp:
                loser_variant = loser_interp["prompt_variant"]
                variant_wins[winner_variant] += 1
                variant_losses[loser_variant] += 1
        else:
            # Tie
            variant_ties[winner_variant] += 1

    # Calculate win rates
    all_variants = set(variant_wins.keys()) | set(variant_losses.keys()) | set(variant_ties.keys())
    win_rates = {}

    for variant in all_variants:
        wins = variant_wins[variant]
        losses = variant_losses[variant]
        ties = variant_ties[variant]
        total = wins + losses

        if total > 0:
            win_rate = wins / total * 100
        else:
            win_rate = 50.0  # No data

        win_rates[variant] = {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "total_comparisons": total,
            "win_rate": win_rate
        }

    return win_rates


def calculate_head_to_head(evaluations, interpretations):
    """
    Calculate head-to-head comparison matrix.
    Returns dict: {(variant_a, variant_b): {"a_wins": N, "b_wins": M}}
    """
    h2h = defaultdict(lambda: {"a_wins": 0, "b_wins": 0})

    for eval_record in evaluations:
        winner_id = eval_record.get("interpretation_id")
        loser_id = eval_record.get("preferred_over")

        if not winner_id or not loser_id:
            continue

        winner_interp = interpretations.get(winner_id)
        loser_interp = interpretations.get(loser_id)

        if not winner_interp or not loser_interp:
            continue

        winner_variant = winner_interp["prompt_variant"]
        loser_variant = loser_interp["prompt_variant"]

        if winner_variant == loser_variant:
            continue  # Same variant

        # Use sorted tuple as key for consistent ordering
        key = tuple(sorted([winner_variant, loser_variant]))
        if key[0] == winner_variant:
            h2h[key]["a_wins"] += 1
        else:
            h2h[key]["b_wins"] += 1

    return h2h


def get_evaluator_stats(evaluations):
    """Get statistics per evaluator."""
    evaluator_counts = defaultdict(int)
    for e in evaluations:
        evaluator = e.get("evaluator_name", "unknown")
        evaluator_counts[evaluator] += 1
    return dict(evaluator_counts)


def get_instrument_breakdown(evaluations, interpretations):
    """Get win rates broken down by instrument."""
    instrument_data = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0}))

    for eval_record in evaluations:
        winner_id = eval_record.get("interpretation_id")
        loser_id = eval_record.get("preferred_over")

        if not winner_id or not loser_id:
            continue

        winner_interp = interpretations.get(winner_id)
        loser_interp = interpretations.get(loser_id)

        if not winner_interp or not loser_interp:
            continue

        instrument = winner_interp["instrument_code"]
        winner_variant = winner_interp["prompt_variant"]
        loser_variant = loser_interp["prompt_variant"]

        instrument_data[instrument][winner_variant]["wins"] += 1
        instrument_data[instrument][loser_variant]["losses"] += 1

    return instrument_data


def print_report(win_rates, h2h, evaluator_stats, instrument_breakdown, total_evaluations):
    """Print formatted analysis report."""
    print("=" * 60)
    print("       WYNIKI WALIDACJI PROMPTÓW DIAGNOSTYCZNYCH")
    print("=" * 60)
    print()

    print(f"Łączna liczba ocen: {total_evaluations}")
    print(f"Liczba oceniających: {len(evaluator_stats)}")
    print()

    # Evaluator breakdown
    print("OCENIAJĄCY:")
    for evaluator, count in sorted(evaluator_stats.items(), key=lambda x: -x[1]):
        print(f"  - {evaluator}: {count} ocen")
    print()

    # Overall ranking
    print("-" * 60)
    print("RANKING WARIANTÓW PROMPTÓW (wg win rate):")
    print("-" * 60)
    print(f"{'Rank':<5} {'Variant':<20} {'Win Rate':<10} {'W-L':<10} {'Ties':<6}")
    print("-" * 60)

    sorted_variants = sorted(
        win_rates.items(),
        key=lambda x: x[1]["win_rate"],
        reverse=True
    )

    for rank, (variant, stats) in enumerate(sorted_variants, 1):
        win_rate = stats["win_rate"]
        w_l = f"{stats['wins']}-{stats['losses']}"
        ties = stats["ties"]
        print(f"{rank:<5} {variant:<20} {win_rate:>6.1f}%    {w_l:<10} {ties:<6}")

    print()

    # Head-to-head matrix
    if h2h:
        print("-" * 60)
        print("BEZPOŚREDNIE PORÓWNANIA (HEAD-TO-HEAD):")
        print("-" * 60)
        for (var_a, var_b), stats in sorted(h2h.items()):
            total = stats["a_wins"] + stats["b_wins"]
            if total > 0:
                a_pct = stats["a_wins"] / total * 100
                print(f"  {var_a} vs {var_b}: {stats['a_wins']}-{stats['b_wins']} ({a_pct:.0f}% dla {var_a})")
        print()

    # Instrument breakdown
    if instrument_breakdown:
        print("-" * 60)
        print("WYNIKI WG INSTRUMENTU:")
        print("-" * 60)
        for instrument, variants in sorted(instrument_breakdown.items()):
            print(f"\n  {instrument}:")
            sorted_vars = sorted(
                variants.items(),
                key=lambda x: x[1]["wins"] / max(1, x[1]["wins"] + x[1]["losses"]),
                reverse=True
            )
            for variant, stats in sorted_vars:
                total = stats["wins"] + stats["losses"]
                if total > 0:
                    rate = stats["wins"] / total * 100
                    print(f"    {variant}: {rate:.0f}% ({stats['wins']}-{stats['losses']})")

    print()
    print("=" * 60)
    print("WNIOSKI:")
    print("=" * 60)

    if sorted_variants:
        best_variant = sorted_variants[0][0]
        best_rate = sorted_variants[0][1]["win_rate"]
        print(f"  Najlepszy wariant: {best_variant} ({best_rate:.1f}% win rate)")

        if len(sorted_variants) > 1:
            worst_variant = sorted_variants[-1][0]
            worst_rate = sorted_variants[-1][1]["win_rate"]
            print(f"  Najsłabszy wariant: {worst_variant} ({worst_rate:.1f}% win rate)")

        # Insights
        print()
        print("  Obserwacje:")
        if best_variant in ["full", "with_history"]:
            print("  - Więcej kontekstu (historia, pełny profil) poprawia jakość")
        if best_variant in ["with_interests", "with_work"]:
            print("  - Personalizacja przez zainteresowania/pracę jest wartościowa")
        if sorted_variants[-1][0] == "basic":
            print("  - Podstawowy prompt bez kontekstu jest najmniej efektywny")

    print()


def main():
    """Run analysis."""
    print("Pobieranie danych...")

    evaluations = fetch_evaluations()
    interpretations = fetch_interpretations()

    print(f"Znaleziono {len(evaluations)} ocen i {len(interpretations)} interpretacji")

    if not evaluations:
        print("\nBrak ocen do analizy. Najpierw przeprowadź ewaluacje w aplikacji Streamlit.")
        return

    # Calculate metrics
    win_rates = calculate_win_rates(evaluations, interpretations)
    h2h = calculate_head_to_head(evaluations, interpretations)
    evaluator_stats = get_evaluator_stats(evaluations)
    instrument_breakdown = get_instrument_breakdown(evaluations, interpretations)

    # Print report
    print_report(
        win_rates,
        h2h,
        evaluator_stats,
        instrument_breakdown,
        len(evaluations)
    )


if __name__ == "__main__":
    main()
