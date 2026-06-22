#!/usr/bin/env python3
import sys
import json

import focalboard_client


def usage():
    print(
        "Usage:\n"
        "  ./fb_note.py <CARD_ID> \"Note text\"\n\n"
        "Example:\n"
        "  ./fb_note.py cxcm... \"Blocked: waiting for access\"\n"
    )


def main():
    if len(sys.argv) < 3:
        usage()
        sys.exit(2)

    card_id = sys.argv[1]
    note_text = sys.argv[2]

    try:
        result = focalboard_client.add_note(card_id, note_text)
    except ValueError as e:
        print("ERROR:", str(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
