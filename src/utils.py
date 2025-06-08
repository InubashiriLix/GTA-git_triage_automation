from pathlib import Path
import subprocess
import platform


def find_repo_root(cwd: Path | str = ".") -> Path | None:
    """
    return the root path of the git repository
    @params: Path | str
    @return: Path
    @except: FileNotFoundError if no git repository found
    """
    p = Path(cwd).resolve()
    for parent in [p] + list(p.parents):
        if (parent / ".git").is_dir():
            return parent
    return None


def test_find_repo_root():
    """
    test for the find_repo_root function
    in the current folder (as an folder in the repo)  and a non git folder
    """
    try:
        find_repo_root()
        print("test for current folder pass")
    except Exception as e:
        print("test for current folder not pass")
        raise Exception(e)

    try:
        find_repo_root("~/temp/")
        raise Exception("test for non git folder not pass")
    except Exception as e:
        print("test for non git folder pass")
    print("ALL DONE SUCCESSFULLY")


def os_run(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return res.stdout


def diff_new_file(path: Path, repo: Path) -> str:
    """
    generate the untracked patch for untracked files.
    """
    null_device = "NUL" if platform.system() == "Windows" else "/dev/null"
    res = subprocess.run(
        [
            "git",
            "diff",
            "--no-index",
            "--no-color",
            "--unified=0",
            null_device,
            str(path),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,  # for the untracked file, the outpu will return false, therefore we set check=False
    )
    return res.stdout


if __name__ == "__main__":
    test_find_repo_root()
