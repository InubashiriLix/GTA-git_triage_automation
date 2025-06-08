import json
import queue
from typing import Any, Dict, List
import subprocess
from pathlib import Path

from queue import PriorityQueue

from src.utils import os_run, find_repo_root


commit_queue: PriorityQueue = queue.PriorityQueue()


class CommitItem:
    def __init__(
        self,
        com_idx: int,
        com_type: str,
        scope: str,
        priority: int,
        file_list: list[str],
        title: str,
        body: list[str],
    ):
        self.com_idx = com_idx
        self.com_type = com_type
        self.scope = scope
        self.priority = priority
        self.file_list = file_list
        self.title = title
        self.body = body

    def export(self) -> Dict[str, Any]:
        return {
            "com_type": self.com_type,
            "com_idx": self.com_idx,
            "scope": self.scope,
            "priority": self.priority,
            "file_list": self.file_list,
            "title": self.title,
            "body": self.body,
        }

    def format(self) -> str:
        return f"{self.com_type}({self.scope}): {self.title}\n\n{'\n'.join(self.body) if isinstance(self.body, list) else self.body}"

    def __ge__(self, other):
        if type(other) is int:
            return self.priority < other
        elif type(other) is not CommitItem:
            raise TypeError(f"Cannot compare CommitItem with {type(other)}")
        # NOTE: reason we use <= has been explained in the __lt__ method
        return self.priority <= other.priority

    def __lt__(self, other):
        """
        NOTE: Cause' the priority is a min heap implementation,
        and our expectataion is the higher the priority, the earlier it should be executed,
        We had to change the less than opertor.
        """
        if type(other) is int:
            return self.priority < other
        elif type(other) is not CommitItem:
            raise TypeError(f"Cannot compare CommitItem with {type(other)}")
        # NOTE: reason we use > has been explained above
        return self.priority > other.priority

    def __eq__(self, other):
        if type(other) is int:
            return self.priority < other
        elif type(other) is not CommitItem:
            raise TypeError(f"Cannot compare CommitItem with {type(other)}")
        return self.priority == other.priority


def commit_json_parser(json_data: Any) -> bool:
    """
    parse the commit json from deepseek, and push to the queue
    """
    try:
        for commit_items in json_data["commits"]:
            temp_constr_dict = {
                "com_idx": commit_items["commit_index"],
                "com_type": commit_items["type"],
                "scope": commit_items["scope"],
                "priority": int(commit_items["priority"]),
                "file_list": commit_items["files"],
                "title": commit_items["title"],
                "body": commit_items["body"],
            }
            commit_queue.put(CommitItem(**temp_constr_dict))
    except Exception as e:
        # TODO: specify the exception handler
        print(f"Error parsing commit JSON: {e}")
        return False
    return True


def _os_run(cmd: List[str], cwd: Path) -> bool:
    """
    Run cmd in cwd.  Return True if exit code == 0, else False.
    """
    try:
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command {' '.join(cmd)} failed:\n{e.stderr}")
        return False


def exec_commit(commit_item: CommitItem) -> bool:
    add_git_cmd = ["git", "add"] + commit_item.file_list
    commit_cmd = ["git", "commit", "-m"] + [commit_item.format()]

    repo_dir = find_repo_root()
    if repo_dir is None:
        print("No git repository found.")
        return False

    if not _os_run(cmd=add_git_cmd, cwd=repo_dir):
        return False

    if not _os_run(cmd=commit_cmd, cwd=repo_dir):
        return False

    return True


def schedule_execute_commits(json_data):
    commit_json_parser(json_data)
    while not commit_queue.empty():
        exec_commit(commit_queue.get())
