"""Scheduled EA -> Supabase sync for StereoHearts FC.

Runs independently of Streamlit; requires environment variables in GitHub Actions.
"""
import os
import sys
from datetime import datetime, timezone

from ea_client import fetch_club_bundle
from storage import SupabaseStore

CLUB_ID = "400349"
CLUB_NAME = "StereoHearts FC"


def main():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY GitHub Actions secret")

    print(f"Starting EA sync for {CLUB_NAME} ({CLUB_ID}) at {datetime.now(timezone.utc).isoformat()}", flush=True)
    bundle = fetch_club_bundle(int(CLUB_ID))
    match_count = len(bundle.get("matches") or [])
    player_count = len(bundle.get("match_players") or [])
    print(f"EA returned {match_count} matches and {player_count} player-performance records", flush=True)

    # Do not report an empty/partial EA response as a successful archival sync.
    if not match_count:
        raise RuntimeError("EA returned zero matches; refusing to report sync as successful")

    store = SupabaseStore(url, key)
    processed = store.save_bundle(CLUB_ID, CLUB_NAME, bundle)
    print(f"Sync complete: processed {processed} raw records; structured match/player rows upserted.", flush=True)
    print("Note: processed count is not the number of newly discovered records.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Sync failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
