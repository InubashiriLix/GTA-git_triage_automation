import json
import requests
import sys
import re

from src.configs import MODEL, TEMPERATURE, MAX_REPLY_TOKENS, API_URL, PROMPT
from src.diffs import collect_diffs
from src.utils import find_repo_root

DEEPSEEK_API_KEY = "sk-8a8b4841788e45f89e30080fe03c55df"


def clean_json(text: str) -> str:
    """
    remove markdown fences and any extra text,
    """
    if text.strip().startswith("```"):
        parts = text.split("```")
        # 找到包含 '{' 的那段
        for p in parts:
            if "{" in p:
                text = p
                break

    match = re.search(r"(\{.*\})", text, flags=re.S)
    if match:
        text = match.group(1)

    return text.strip()


def build_prompt(hunks: list[dict]) -> list[dict]:
    """
    fill the diffs to the prompt template
    """
    filled = PROMPT.replace(
        "{HUNKS_JSON}", json.dumps(hunks, ensure_ascii=False, indent=None)
    )
    return [{"role": "system", "content": filled}]


def call_deepseek(messages: list[dict]) -> dict:
    """
    call the deepseek api, get the main commmit msgs
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_REPLY_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"]
    print(content)
    print("\n=== raw response ===")
    print(content)
    print("====================\n")

    cleaned = clean_json(content)
    print("=== cleaned JSON ===")
    print(cleaned)
    print("====================\n")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("JSON parse failed:", e, file=sys.stderr)
        sys.exit(1)


def test():
    hunks = collect_diffs(find_repo_root())
    if not hunks:
        print("⚠️ no diff hunk，exit")
        return

    messages = build_prompt(hunks)

    plan = call_deepseek(messages)

    # print("=== final plan JSON ===")
    # print(json.dumps(plan, ensure_ascii=False, indent=2))
    # print("========================")

    # with open("git_plan.json", "w", encoding="utf-8") as f:
    #     json.dump(plan, f, ensure_ascii=False, indent=2)
    #     print("✓ 已保存计划到 git_plan.json")


if __name__ == "__main__":
    test()
