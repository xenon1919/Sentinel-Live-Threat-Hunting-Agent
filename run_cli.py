"""
CLI runner: stream a scan to the terminal.

Usage:
    python run_cli.py --company "Acme Corp" --domain acme.com
    python run_cli.py --company "Acme Corp" --domain acme.com --context "fintech, SF"
"""

from __future__ import annotations

import argparse
import json

from agent.config import Settings
from agent.orchestrator import ExposureMonitorAgent


STAGE_ICON = {
    "plan": "🧭",
    "search": "🔎",
    "triage": "🗂️",
    "fetch": "🌐",
    "analyze": "🧪",
    "report": "📊",
    "memory": "🧠",
    "error": "⚠️",
    "done": "✅",
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Open-web exposure monitor agent")
    ap.add_argument("--company", required=True)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--context", default="")
    args = ap.parse_args()

    settings = Settings.load()
    agent = ExposureMonitorAgent(settings)

    print(f"\n=== Exposure scan: {args.company} ({args.domain}) ===\n")
    gen = agent.scan(args.company, args.domain, args.context)
    report = None
    try:
        while True:
            ev = next(gen)
            icon = STAGE_ICON.get(ev.stage, "·")
            print(f"{icon} [{ev.stage}] {ev.message}")
    except StopIteration as stop:
        result = stop.value
        report = result.report if result else None

    print("\n=== FINAL RISK REPORT ===")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
