#!/usr/bin/python3
#!/usr/bin/env python3
import argparse
from pathlib import Path

from src.utils import find_repo_root
from src.diffs import collect_diffs
from src.ds_commu import build_prompt, call_deepseek
from src.commit import schedule_execute_commits


def cmd_scan(args):
    repo = normalize_path(args.path)
    try:
        root = find_repo_root(repo)
        print(f"✅ Git repo root: {root}")
    except FileNotFoundError:
        print("❌ No git repository found in the specified directory or its parents.")


def cmd_diff(args):
    repo = normalize_path(args.path)
    hunks = collect_diffs(repo)
    if hunks:
        print("📄 Diffs found:")
        for h in hunks:
            print(f" - {h['path']} {h['header']}")
    else:
        print("✔️  No diffs found.")


def cmd_run(args):
    repo = normalize_path(args.path)
    # Override collect_diffs to accept repo path if needed
    hunks = collect_diffs(repo)
    if not hunks:
        print("⚠️  No diff hunks to process, exiting.")
        return

    messages = build_prompt(hunks)
    plan = call_deepseek(messages)
    print("commmiting")
    schedule_execute_commits(plan)


def normalize_path(path_str: str) -> Path:
    """Expand ~, resolve . and .., but don't require path to exist."""
    return Path(path_str).expanduser().resolve(strict=False)


def main():
    parser = argparse.ArgumentParser(
        prog="gta", description="gta – Git Triage & Automation CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # gta scan
    p_scan = subparsers.add_parser("scan", help="Scan for the git repository root")
    p_scan.add_argument(
        "-p",
        "--path",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    p_scan.set_defaults(func=cmd_scan)

    # gta diff
    p_diff = subparsers.add_parser("diff", help="Collect and print git diff hunks")
    p_diff.add_argument(
        "-p",
        "--path",
        default=".",
        help="Repository directory (default: current directory)",
    )
    p_diff.set_defaults(func=cmd_diff)

    # gta run
    p_run = subparsers.add_parser(
        "run", help="Run AI plan: generate and schedule commits"
    )
    p_run.add_argument(
        "-p",
        "--path",
        default=".",
        help="Repository directory (default: current directory)",
    )
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
