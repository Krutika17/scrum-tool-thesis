import os, sys, subprocess

def main():
    q = os.environ.get("IMP_PREFIX", "IMPEDIMENT:")
    limit = 50

    # Run fb_list.py and filter lines containing the prefix
    cmd = ["python3", "fb_list.py", "--limit", str(limit)]
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)

    lines = out.splitlines()
    header = []
    body = []
    for ln in lines:
        if ln.strip() == "":
            continue
        if ln.startswith("Board:") or ln.startswith("----") or " | cards:" in ln:
            header.append(ln)
            continue
        # card lines look like: <id>  |  <status>  |  <priority>  |  <title>
        if "  |  " in ln and q.lower() in ln.lower():
            body.append(ln)

    print("\nImpediments report\n")
    if header:
        print(header[0])
        print()

    if not body:
        print(f"No cards found containing '{q}'.")
        return

    for ln in body:
        print(ln)

if __name__ == "__main__":
    main()
