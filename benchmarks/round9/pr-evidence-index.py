"""Snapshot fresh GitHub PR metadata and write the comprehensive research index."""
import datetime
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "QuiteLiterallyConnor/Minkowski4CPP"


def section(body, name):
    match = re.search(
        rf"(?ims)^\s*\#{{1,6}}\s+{re.escape(name)}\b[^\n]*\n(.*?)(?=^\s*\#{{1,6}}\s|\Z)",
        body or "",
    )
    if not match:
        return "See PR body (section not automatically extracted)."
    return match.group(1).strip()


def cell(value, limit=520):
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        value = value[:limit].rstrip() + "…"
    return value.replace("|", "\\|")


def main():
    raw = subprocess.check_output(
        ["gh", "pr", "list", "--repo", REPO, "--author", "itsSio", "--state", "all",
         "--limit", "100", "--json", "number,title,state,url,body,reviewDecision,mergedAt,headRefOid,updatedAt"],
        text=True, encoding="utf-8",
    )
    prs = sorted(json.loads(raw), key=lambda p: p["number"])
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    snapshot = ROOT / "pr-snapshot"
    snapshot.mkdir(exist_ok=True)
    (snapshot / "all.json").write_text(raw, encoding="utf-8")
    lines = ["# Minkowski4CPP pull request evidence index", "",
             f"GitHub snapshot: {stamp}. Tests and benchmarks below are excerpts from PR descriptions; "
             "they remain attributed reports unless independently verified in the round receipts.", "",
             "| PR | Title | Review status | Summary | Tests reported | Benchmarks reported |",
             "|---|---|---|---|---|---|"]
    for pr in prs:
        (snapshot / f"pr{pr['number']}.json").write_text(
            json.dumps(pr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        decision = pr.get("reviewDecision") or "no review decision"
        status = f"{pr['state'].lower()}; {decision.lower()}"
        lines.append("| " + " | ".join([
            f"[#{pr['number']}]({pr['url']})", cell(pr["title"], 220), cell(status),
            cell(section(pr["body"], "SUMMARY"), 320),
            cell(section(pr["body"], "TESTING"), 600),
            cell(section(pr["body"], "BENCHMARKS"), 700),
        ]) + " |")
    counts = {state: sum(pr["state"] == state for pr in prs) for state in ("OPEN", "MERGED", "CLOSED")}
    lines += ["", f"Totals: {len(prs)} PRs; " + "; ".join(f"{n} {state.lower()}" for state, n in counts.items()) + ".", ""]
    (ROOT / "pr-index.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"snapshot_utc": stamp, "total": len(prs), "counts": counts,
                      "index": str(ROOT / "pr-index.md")}))


if __name__ == "__main__":
    main()
