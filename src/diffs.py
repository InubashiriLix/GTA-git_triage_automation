import subprocess
import pytest
from pathlib import Path
import json
import re

import logging

from src.utils import os_run, find_repo_root, diff_new_file

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(funcName)s] - %(message)s",
)

TOKEN_LIMIT_DIFF: int = 10000
HUNK_RE = re.compile(r"^@@.*?@@", re.M)
FILE_START_RE = re.compile("^diff --git a/(.*) b/(.*)$", re.M)


def collect_untracked(repo: Path) -> list[dict]:
    """
    return a list of untracked files in the git repository.
    return [{path, stage:'UNTRACKED', header, patch}, ...]
    """
    # list all the untracked and not excludede files
    out = os_run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo,
    )
    results: list[dict] = []

    for rel_path in filter(None, out.splitlines()):
        file_path = repo / rel_path
        patch = diff_new_file(file_path, repo)
        for match in HUNK_RE.finditer(patch):
            header = match.group(0)
            start = match.start()
            end = HUNK_RE.search(patch, match.end())
            end_pos = end.start() if end else len(patch)
            out_patch = patch[start:end_pos]
            results.append(
                {
                    "path": rel_path,
                    "stage": "UNTRACKED",
                    "header": header,
                    "patch": out_patch,
                }
            )
    return results


def collect_tracked_diff(repo_dir: Path, staged: bool) -> list[dict]:
    cmd = ["git", "diff", "--no-color", "--unified=0"]
    if staged:
        cmd.append("--cached")

    out = os_run(cmd, cwd=repo_dir)
    results: list[dict] = []

    current_file = None
    hunk_start = 0

    for line in out.splitlines(keepends=True):
        if line.startswith("diff --git"):
            buf = []
            if current_file and hunk_start:
                _extract_hunks(buf, current_file, hunk_start, results)
            current_file = line.split(" b/")[1].strip()
            buf, hunk_start = [], 0
            stage = "INDEX" if staged else "WORKTREE"
        if current_file is None:
            continue
        buf.append(line)

    if current_file and buf:
        _extract_hunks(buf, current_file, stage, results)

    return results


def _extract_hunks(buf: list[str], path: str, stage: str, out: list[dict]):
    text = "".join(buf)

    for match in HUNK_RE.finditer(text):
        header = match.group(0)

        start = match.start()
        end = HUNK_RE.search(text, match.end())
        end_pos = end.start() if end else len(text)
        patch = text[start:end_pos]
        out.append({"path": path, "stage": stage, "header": header, "patch": patch})


def collect_diffs(repo_dir) -> list[dict]:
    """
    merge all the diff hunks
    @return: list[dict]
    """
    hunks = (
        collect_tracked_diff(repo_dir=repo_dir, staged=False)  # WORKTREE
        + collect_tracked_diff(repo_dir=repo_dir, staged=True)  # INDEX
        + collect_untracked(repo_dir)  # UNTRACKED
    )
    return hunks


if __name__ == "__main__":
    print(collect_diffs(find_repo_root()))
