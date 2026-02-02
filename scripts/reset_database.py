#!/usr/bin/env python3
"""
Reset database tables for a fresh experiment.
Deletes all interpretations and evaluations.

Usage:
    python scripts/reset_database.py           # Interactive confirmation
    python scripts/reset_database.py --force   # Skip confirmation
"""
import os
import sys
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Brak zmiennych SUPABASE_URL i SUPABASE_KEY")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_counts():
    """Get current row counts."""
    interps = supabase.table("interpretations").select("id", count="exact").execute()
    evals = supabase.table("evaluations").select("id", count="exact").execute()
    return interps.count, evals.count


def reset_tables():
    """Delete all data from tables."""
    # Delete evaluations first (foreign key constraint)
    supabase.table("evaluations").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # Delete interpretations
    supabase.table("interpretations").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()


def main():
    force = "--force" in sys.argv

    interp_count, eval_count = get_counts()

    print("=== Reset Database ===")
    print(f"Interpretacje: {interp_count}")
    print(f"Ewaluacje: {eval_count}")
    print()

    if interp_count == 0 and eval_count == 0:
        print("✅ Baza jest już pusta.")
        return

    if not force:
        confirm = input("Czy na pewno usunąć wszystkie dane? (tak/nie): ")
        if confirm.lower() not in ["tak", "yes", "y", "t"]:
            print("Anulowano.")
            return

    print("Usuwanie danych...")
    reset_tables()

    # Verify
    interp_count, eval_count = get_counts()
    print(f"\n✅ Gotowe! Interpretacje: {interp_count}, Ewaluacje: {eval_count}")


if __name__ == "__main__":
    main()
