"""Quick end-to-end test of the MeetingCrew.

WARNING: Running this will:
  - call OpenAI (costs tokens)
  - create real GitHub issues in the repo you point it at

Edit the TODO placeholders below before running.
"""

import sys
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from meetings.crew import run_meeting_crew  # noqa: E402


# ---- Edit these ------------------------------------------------------------

REPO = "ArunaSivaram/meetingcrew-sandbox"

ROSTER = [
    {
        "name": "Aruna",
        "email": "aruna@example.com",      # TODO: replace with real email before running
        "github_username": "ArunaSivaram",
        "aliases": "Aru, A.S.",
    },
    {
        "name": "Gokul",
        "email": "gokul@example.com",      # TODO: replace with real email before running
        "github_username": "gokuljeyapaul",
        "aliases": "Gok, G.",
    },
]

NOTES = """\
Weekly sync — Aruna + Gokul

- Aruna will draft the v2 onboarding flow spec by Friday 2026-10-24.
- Gokul to spike the Postgres migration script and share findings by next Monday.
- Both: review the open PRs tagged "priority" before our next sync.
- Gok mentioned he'll run the perf benchmarks after the spike.
- Nobody owns the docs refresh yet — park it.
"""

# ---------------------------------------------------------------------------


def main() -> None:
    result = run_meeting_crew(notes=NOTES, repo=REPO, roster=ROSTER)

    print("\n" + "=" * 60)
    print("ACTION ITEMS (structured)")
    print("=" * 60)
    if result["action_items"]:
        for item in result["action_items"].items:
            print(f"- [{item.github_username or 'unassigned'}] {item.task}")
            if item.due_date:
                print(f"    due: {item.due_date}")
            if item.context:
                print(f"    context: {item.context}")

    print("\n" + "=" * 60)
    print("ISSUES (raw agent output)")
    print("=" * 60)
    print(result["issues_raw"])

    print("\n" + "=" * 60)
    print("COMMS (structured)")
    print("=" * 60)
    if result["comms"]:
        print("Summary:\n" + result["comms"].summary)
        for email in result["comms"].emails:
            print(f"\n--- To @{email.github_username} ({email.owner_name}) ---")
            print(f"Subject: {email.subject}")
            print(email.body)


if __name__ == "__main__":
    main()
