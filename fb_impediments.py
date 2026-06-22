#!/usr/bin/env python3
import os
import sys

import focalboard_client


def main():
    q = os.environ.get("IMP_PREFIX", "IMPEDIMENT:")
    limit = 50

    try:
        result = focalboard_client.list_work_items(limit=limit)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    matches = [item for item in result["items"] if q.lower() in item["title"].lower()]

    print("\nImpediments report\n")
    print(f"Board: {result['board_title']}  | cards: {result['total']}")
    print()

    if not matches:
        print(f"No cards found containing '{q}'.")
        return

    for item in matches:
        print(f"{item['id']}  |  {item['status']:<12}  |  {item['priority']:<10}  |  {item['title']}")


if __name__ == "__main__":
    main()
