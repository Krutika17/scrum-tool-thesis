#!/usr/bin/env python3
import sys

import focalboard_client

SEED = [
    ("Set up project repository", "done", "high"),
    ("Write sprint backlog", "done", "medium"),
    ("Implement login screen", "progress", "high"),
    ("Design database schema", "progress", "medium"),
    ("Prepare sprint review slides", "todo", "medium"),
    ("Fix navigation bug", "todo", "low"),
]


def main():
    apply = "--apply" in sys.argv[1:]

    listing = focalboard_client.list_work_items(limit=500)
    current = listing["items"]

    print(f"Board: {listing['board_title']}")
    print(f"\nExisting cards to remove ({len(current)}):")
    for c in current:
        print(f"  - {c['id']}  {c['title']}")

    print(f"\nSeed cards to create ({len(SEED)}):")
    for title, status, priority in SEED:
        print(f"  - [{status:<8} {priority:<6}] {title}")

    if not apply:
        print("\nDry run only. Re-run with --apply to reset the board.")
        return

    print("\nRemoving existing cards...")
    for c in current:
        focalboard_client.update_status(c["id"], delete=True)

    print("Creating seed cards...")
    for title, status, priority in SEED:
        focalboard_client.create_card(title, status, priority)

    print("\nBoard reset to seed state.")


if __name__ == "__main__":
    main()
