#!/usr/bin/env python3
import argparse
import sys

import focalboard_client


def main():
    ap = argparse.ArgumentParser(prog="fb_list.py")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--status", choices=["todo", "progress", "done"], default=None)
    ap.add_argument("--priority", choices=["high", "medium", "low"], default=None)
    ap.add_argument("--query", default=None, help="substring match on title")
    args = ap.parse_args()

    try:
        result = focalboard_client.list_work_items(
            status=args.status,
            priority=args.priority,
            query=args.query,
            limit=args.limit,
        )
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    print(f"\nBoard: {result['board_title']}  | cards: {result['total']}\n")
    for item in result["items"]:
        print(f"{item['id']}  |  {item['status']:<12}  |  {item['priority']:<10}  |  {item['title']}")


if __name__ == "__main__":
    main()
