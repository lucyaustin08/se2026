#!/usr/bin/env python3
"""Turn a JUnit XML test report, plus a coverage report, into a Markdown summary.

CI appends the output to each run's Summary page, so every run shows a per-file breakdown
(tests, failures, duration, success rate) and the coverage totals.

Usage:
  test_summary.py TITLE JUNIT_XML [--coverage-xml COBERTURA_XML] [--coverage-json SUMMARY_JSON]
"""

import argparse
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def group_results(junit_path: Path) -> dict[str, dict[str, float]]:
    """Count tests, failures, skips and time for each test file."""
    root = ET.parse(junit_path).getroot()
    groups: dict[str, dict[str, float]] = defaultdict(
        lambda: {"tests": 0, "failures": 0, "skipped": 0, "time": 0.0}
    )
    for suite in root.iter("testsuite"):
        for case in suite.findall("testcase"):
            name = case.get("classname") or suite.get("name") or "tests"
            group = groups[name]
            group["tests"] += 1
            group["time"] += float(case.get("time") or 0)
            if case.find("failure") is not None or case.find("error") is not None:
                group["failures"] += 1
            elif case.find("skipped") is not None:
                group["skipped"] += 1
    return dict(sorted(groups.items()))


def success_rate(tests: float, failures: float, skipped: float) -> str:
    ran = tests - skipped
    return "n/a" if ran == 0 else f"{100 * (ran - failures) / ran:.0f}%"


def coverage_line(args: argparse.Namespace) -> str | None:
    if args.coverage_xml and Path(args.coverage_xml).exists():
        root = ET.parse(args.coverage_xml).getroot()
        lines = float(root.get("line-rate", 0)) * 100
        branches = float(root.get("branch-rate", 0)) * 100
        return f"**Coverage:** {lines:.1f}% of lines, {branches:.1f}% of branches"
    if args.coverage_json and Path(args.coverage_json).exists():
        total = json.loads(Path(args.coverage_json).read_text())["total"]
        return (
            f"**Coverage:** {total['lines']['pct']:.1f}% of lines, "
            f"{total['branches']['pct']:.1f}% of branches"
        )
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    parser.add_argument("junit")
    parser.add_argument("--coverage-xml")
    parser.add_argument("--coverage-json")
    args = parser.parse_args()

    out = [f"## {args.title}", ""]
    if not Path(args.junit).exists():
        out.append("_No test report was produced (the tests did not run)._")
        print("\n".join(out))
        return

    groups = group_results(Path(args.junit))
    total = {
        key: sum(group[key] for group in groups.values())
        for key in ("tests", "failures", "skipped", "time")
    }
    status = "✅ All passed" if total["failures"] == 0 else "❌ Some failed"
    out += [
        "| Tests | Failures | Skipped | Duration | Success rate | |",
        "|---:|---:|---:|---:|---:|---|",
        (
            f"| {total['tests']:.0f} | {total['failures']:.0f} | {total['skipped']:.0f} "
            f"| {total['time']:.2f}s "
            f"| {success_rate(total['tests'], total['failures'], total['skipped'])} | {status} |"
        ),
        "",
    ]
    coverage = coverage_line(args)
    if coverage:
        out += [coverage, ""]
    out += [
        "| Test file | Tests | Failures | Skipped | Duration | Success rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, group in groups.items():
        out.append(
            f"| `{name}` | {group['tests']:.0f} | {group['failures']:.0f} "
            f"| {group['skipped']:.0f} | {group['time']:.2f}s "
            f"| {success_rate(group['tests'], group['failures'], group['skipped'])} |"
        )
    out.append("")
    print("\n".join(out))


if __name__ == "__main__":
    main()
