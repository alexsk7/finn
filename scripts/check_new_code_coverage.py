"""Fail when added executable Python lines are covered below a threshold.

This script compares a git range and uses coverage.json line data to measure
coverage only for newly added executable lines.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
ZERO_SHA = "0000000000000000000000000000000000000000"


@dataclass
class FileResult:
    file_path: str
    executable_added: int
    covered_added: int

    @property
    def pct(self) -> float:
        if self.executable_added == 0:
            return 100.0
        return (self.covered_added / self.executable_added) * 100.0


def _load_coverage_lines(json_path: Path) -> dict[str, dict[int, int]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    coverage_map: dict[str, dict[int, int]] = {}

    for filename, file_data in payload.get("files", {}).items():
        line_hits: dict[int, int] = {int(n): 1 for n in file_data.get("executed_lines", [])}
        for n in file_data.get("missing_lines", []):
            line_hits.setdefault(int(n), 0)
        coverage_map[filename] = line_hits

    return coverage_map


def _added_python_lines(base: str, head: str) -> dict[str, set[int]]:
    cmd = [
        "git",
        "diff",
        "--unified=0",
        "--no-color",
        f"{base}..{head}",
        "--",
        "*.py",
        ":!tests/**",
    ]
    patch = subprocess.check_output(cmd, text=True)

    added: dict[str, set[int]] = {}
    current_file: str | None = None
    current_line = 0

    for raw in patch.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
            if current_file == "/dev/null":
                current_file = None
            continue

        hunk_match = HUNK_RE.match(raw)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue

        if current_file is None:
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            added.setdefault(current_file, set()).add(current_line)
            current_line += 1
            continue

        if raw.startswith("-") and not raw.startswith("---"):
            continue

        if raw.startswith("\\"):
            continue

        current_line += 1

    return added


def _merge_base(head: str, ref: str) -> str | None:
    try:
        return subprocess.check_output(["git", "merge-base", head, ref], text=True).strip()
    except subprocess.CalledProcessError:
        return None


def _resolve_base(head: str) -> str:
    """Return the best base commit for the provided head SHA/ref."""
    # Prefer configured upstream when running on a checked-out branch.
    try:
        upstream_ref = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        base_sha = _merge_base(head, upstream_ref)
        if base_sha:
            return base_sha
    except subprocess.CalledProcessError:
        pass

    # Fall back: pick the remote ref this head is fewest commits ahead of.
    refs_out = subprocess.check_output(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/"],
        text=True,
    )
    best_ref: str | None = None
    best_count: int | None = None
    for ref in refs_out.splitlines():
        if ref.endswith("/HEAD"):
            continue
        try:
            count = int(
                subprocess.check_output(
                    ["git", "rev-list", "--count", f"{ref}..{head}"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            )
        except (subprocess.CalledProcessError, ValueError):
            continue

        if best_count is None or count < best_count:
            best_count = count
            best_ref = ref

    if best_ref is None:
        print("Could not determine base ref automatically.", file=sys.stderr)
        sys.exit(2)

    base_sha = _merge_base(head, best_ref)
    if not base_sha:
        print(f"Could not compute merge-base for {head} and {best_ref}.", file=sys.stderr)
        sys.exit(2)

    return base_sha


def _format_pct(value: float) -> str:
    return f"{value:5.1f}%"


def _coverage_keys_for_file(file_path: str) -> list[str]:
    p = Path(file_path)
    keys = [file_path, p.name]
    if file_path.startswith("app/"):
        keys.append(f"app/{p.name}")
    return keys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None)
    parser.add_argument("--auto-base", action="store_true")
    parser.add_argument("--remote-sha", default=None)
    parser.add_argument("--head", required=True)
    parser.add_argument("--print-range", action="store_true")
    parser.add_argument("--threshold", type=float, default=80.0)
    parser.add_argument("--coverage-json", default="coverage.json")
    args = parser.parse_args()

    if args.base is None and not args.auto_base:
        parser.error("one of --base or --auto-base is required")

    if args.base is not None and args.auto_base:
        parser.error("--base and --auto-base are mutually exclusive")

    if args.base is not None:
        base = args.base
    elif args.remote_sha and args.remote_sha != ZERO_SHA:
        base = args.remote_sha
    else:
        base = _resolve_base(args.head)

    if args.print_range:
        print(f"Using range: {base}..{args.head}")

    coverage_json = Path(args.coverage_json)
    if not coverage_json.exists():
        print("coverage.json not found; run make coverage first.", file=sys.stderr)
        return 2

    coverage_map = _load_coverage_lines(coverage_json)
    added_map = _added_python_lines(base, args.head)

    if not added_map:
        print("No added Python lines detected in push range.")
        return 0

    results: list[FileResult] = []
    skipped: list[str] = []

    total_exec = 0
    total_covered = 0

    for file_path in sorted(added_map):
        line_hits = None
        for key in _coverage_keys_for_file(file_path):
            line_hits = coverage_map.get(key)
            if line_hits is not None:
                break
        if line_hits is None:
            skipped.append(file_path)
            continue

        executable_added = 0
        covered_added = 0
        for line_no in sorted(added_map[file_path]):
            if line_no in line_hits:
                executable_added += 1
                if line_hits[line_no] > 0:
                    covered_added += 1

        result = FileResult(file_path=file_path, executable_added=executable_added, covered_added=covered_added)
        results.append(result)
        total_exec += executable_added
        total_covered += covered_added

    print("\nNew-code coverage (added executable Python lines):")
    print("  %      covered/executable   file")
    print("  -----------------------------------------------")
    for r in results:
        print(f"  {_format_pct(r.pct)}   {r.covered_added:4d}/{r.executable_added:<4d}       {r.file_path}")

    if skipped:
        print("\nSkipped (no coverage data for file):")
        for path in skipped:
            print(f"  - {path}")

    if total_exec == 0:
        print("\nNo added executable Python lines found; threshold check passed.")
        return 0

    overall = (total_covered / total_exec) * 100.0
    print(
        f"\nOverall new-code coverage: {_format_pct(overall)} "
        f"({total_covered}/{total_exec}) | threshold: {_format_pct(args.threshold)}"
    )

    if overall < args.threshold:
        print("Push blocked: new-code coverage is below threshold.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
