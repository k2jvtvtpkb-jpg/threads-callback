"""Anthropic Claude APIの薄いラッパー。

ANTHROPIC_API_KEY が未設定の場合は、実際にAPIを呼び出すタイミングで
分かりやすいエラーを出す（import時点では失敗させない＝他モジュールの
単体テストがAPIキー無しでも動くようにするため）。
"""

import json
import os

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY が設定されていません。"
                "コンテンツ生成エージェントを実行する前に環境変数を設定してください。"
            )
        from anthropic import Anthropic  # lazy import

        _client = Anthropic(api_key=api_key)
    return _client


def _response_text(resp):
    return "".join(block.text for block in resp.content if block.type == "text").strip()


def complete_text(system: str, user: str, max_tokens: int = 1200) -> str:
    # claude-sonnet-5 removes temperature/top_p/top_k (400 if sent) and runs
    # adaptive thinking by default when `thinking` is omitted.
    client = get_client()
    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _response_text(resp)


def complete_json(system: str, user: str, max_tokens: int = 2000):
    """LLMにJSON生成を依頼し、パースして返す。パース失敗時はValueErrorを投げる。"""
    raw = complete_text(system, user, max_tokens=max_tokens)
    return _extract_json(raw)


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"LLM応答からJSONを抽出できませんでした: {text[:500]}")
