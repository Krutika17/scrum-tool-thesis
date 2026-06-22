#!/usr/bin/env python3
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import focalboard_client

SCRIPT_DIR = Path(__file__).resolve().parent

PORT = int(focalboard_client.get_config("MATTERMOST_BRIDGE_PORT", "9091"))
EXPECTED_TOKEN = focalboard_client.get_config("MATTERMOST_TOKEN", "").strip()

STATUS_WORDS = {"todo", "progress", "done"}
PRIORITY_WORDS = {"high", "medium", "low"}

USAGE = (
    "Commands:\n"
    "  /fb list [todo|progress|done]\n"
    "  /fb impediments\n"
    "  /fb add <title>\n"
    "  /fb impediment <text>\n"
    "  /fb done <card_id>\n"
    "  /fb move <card_id> <todo|progress|done>\n"
    "  /fb resolve <card_id> <note>\n"
    "  /fb standup <yesterday> | <today> | <blockers>\n"
    "  /fb report"
)


def ephemeral(text):
    return {"response_type": "ephemeral", "text": text}


def in_channel(text):
    return {"response_type": "in_channel", "text": text}


def log_action(action, **fields):
    cmd = ["python3", str(SCRIPT_DIR / "fb_log.py"), action]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        cmd += [f"--{key}", str(value)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except Exception:
        pass


def format_items(result):
    lines = [f"Board: {result['board_title']}  | cards: {result['total']}", ""]
    if not result["items"]:
        lines.append("No cards.")
        return "\n".join(lines)
    rows = ["```"]
    for item in result["items"]:
        rows.append(f"{item['id']}  |  {item['status']:<12}  |  {item['priority']:<10}  |  {item['title']}")
    rows.append("```")
    return "\n".join(lines + rows)


def cmd_list(args):
    status = None
    for a in args:
        low = a.lower()
        if low in STATUS_WORDS:
            status = low
    result = focalboard_client.list_work_items(status=status, limit=50)
    return ephemeral(format_items(result))


def cmd_impediments(args):
    result = focalboard_client.list_work_items(limit=50)
    matches = [i for i in result["items"] if "impediment:" in i["title"].lower()]
    if not matches:
        return ephemeral("No impediments found.")
    rows = ["Impediments", "", "```"]
    for item in matches:
        rows.append(f"{item['id']}  |  {item['status']:<12}  |  {item['priority']:<10}  |  {item['title']}")
    rows.append("```")
    return ephemeral("\n".join(rows))


def cmd_add(args):
    title = " ".join(args).strip()
    if not title:
        return ephemeral("Usage: /fb add <title>")
    card = focalboard_client.create_card(title, "todo", "medium")
    cid = card.get("id", "")
    log_action("add", card=cid, title=title, status="todo", priority="medium")
    return in_channel(f"Added card `{cid}` — {title}")


def cmd_impediment(args):
    text = " ".join(args).strip()
    if not text:
        return ephemeral("Usage: /fb impediment <text>")
    result = focalboard_client.create_impediment(text)
    cid = result["card_id"]
    log_action("imp", card=cid, title=result["title"], status="todo", priority="high")
    return in_channel(f"Impediment raised `{cid}` — {result['title']}")


def cmd_done(args):
    if not args:
        return ephemeral("Usage: /fb done <card_id>")
    cid = args[0]
    focalboard_client.update_status(cid, status="done")
    log_action("done", card=cid, status="done")
    return in_channel(f"Marked `{cid}` as done.")


def cmd_move(args):
    if len(args) < 2 or args[1].lower() not in STATUS_WORDS:
        return ephemeral("Usage: /fb move <card_id> <todo|progress|done>")
    cid = args[0]
    status = args[1].lower()
    focalboard_client.update_status(cid, status=status)
    log_action("move", card=cid, status=status)
    return in_channel(f"Moved `{cid}` to {status}.")


def cmd_resolve(args):
    if len(args) < 2:
        return ephemeral("Usage: /fb resolve <card_id> <note>")
    cid = args[0]
    note = " ".join(args[1:]).strip()
    focalboard_client.resolve_impediment(cid, note)
    log_action("resolve", card=cid, extra=note, status="done", priority="low")
    return in_channel(f"Resolved `{cid}` — {note}")


def cmd_standup(args):
    raw = " ".join(args)
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 3:
        return ephemeral("Usage: /fb standup <yesterday> | <today> | <blockers>")
    yesterday, today, blockers = parts[0], parts[1], parts[2]
    result = focalboard_client.create_standup(yesterday, today, blockers)
    cid = result["standup_card_id"]
    log_action(
        "standup",
        card=cid,
        title=result["title"],
        yesterday=yesterday,
        today=today,
        blockers=blockers,
    )
    return in_channel(
        f"Standup saved `{cid}` — {result['title']}\n"
        f"Yesterday: {yesterday}\nToday: {today}\nBlockers: {blockers}"
    )


def cmd_report(args):
    report = focalboard_client.build_report()
    open_imps = report["open_impediments"]
    lines = [
        "Summary",
        "",
        f"Total logged actions : {len(report['events'])}",
        f"Standups logged      : {len(report['standups'])}",
        f"Open impediments     : {len(open_imps)}",
        f"Resolved impediments : {len(report['resolved_impediments'])}",
    ]
    if open_imps:
        lines.append("")
        lines.append("Open impediments:")
        for imp in open_imps:
            lines.append(f"- {imp.get('title', '')}  (card={imp.get('card_id', '')})")
    return ephemeral("\n".join(lines))


HANDLERS = {
    "list": cmd_list,
    "impediments": cmd_impediments,
    "add": cmd_add,
    "impediment": cmd_impediment,
    "imp": cmd_impediment,
    "done": cmd_done,
    "move": cmd_move,
    "resolve": cmd_resolve,
    "standup": cmd_standup,
    "report": cmd_report,
}


def dispatch(text):
    tokens = text.split()
    if not tokens or tokens[0].lower() in ("help", "-h", "--help"):
        return ephemeral(USAGE)

    sub = tokens[0].lower()
    handler = HANDLERS.get(sub)
    if not handler:
        return ephemeral(f"Unknown command: {sub}\n\n{USAGE}")

    try:
        return handler(tokens[1:])
    except ValueError as e:
        return ephemeral(f"Error: {e}")
    except Exception as e:
        return ephemeral(f"Failed: {e}")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._send({"status": "ok"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length).decode("utf-8") if length else ""
        params = parse_qs(body)

        token = params.get("token", [""])[0]
        if EXPECTED_TOKEN and token != EXPECTED_TOKEN:
            self._send(ephemeral("Unauthorized request."))
            return

        text = params.get("text", [""])[0].strip()
        self._send(dispatch(text))

    def _send(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mattermost bridge listening on port {PORT}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
