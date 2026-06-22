#!/usr/bin/env python3
import sys

import focalboard_client


def usage():
    print(
        "Usage:\n"
        "  ./fb_update.py <CARD_ID> [--status todo|progress|done] [--priority high|medium|low] [--delete]\n"
    )


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(2)

    block_id = sys.argv[1]
    status = None
    priority = None
    do_delete = False

    i = 2
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--status":
            status = sys.argv[i + 1]; i += 2
        elif a == "--priority":
            priority = sys.argv[i + 1]; i += 2
        elif a == "--delete":
            do_delete = True; i += 1
        else:
            print("Unknown arg:", a, file=sys.stderr)
            usage()
            sys.exit(2)

    try:
        result = focalboard_client.update_status(
            block_id, status=status, priority=priority, delete=do_delete
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if do_delete:
        print("{}")
        return

    raw = result["raw_response_text"]
    print(raw if raw.strip() else "{}")


if __name__ == "__main__":
    main()
