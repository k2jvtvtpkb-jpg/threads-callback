"""リサーチャーエージェント。

テーマツリーの中で投稿が手薄なノードを判定し、そのノードについての
投稿ネタ（テーマ・切り口・要点）をLLMで作成してJSON化する。

このモジュールは Threads への投稿は一切行わない。
出力は output/research/ 配下のJSONファイルとログのみ。
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from agents import llm_client
from agents.history_store import load_history, recent_titles_for_node
from agents.ng_words import find_ng_violations
from agents.theme_tree import iter_leaf_nodes

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "research"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

logger = logging.getLogger("researcher")


def _setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(LOG_DIR / "researcher.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[researcher] %(message)s"))
    logger.addHandler(console_handler)


COMPLIANCE_RULES_TEXT = (
    "厳守事項（医療広告ガイドライン対応）:\n"
    "- 患者の症例・治療効果・患者の声には一切言及しない\n"
    "- 経営・組織運営・制度手続きの話題のみに限定する\n"
    "- 患者が特定されうる情報（年齢・性別・来院経緯等の症例的描写）を含めない\n"
    "- 「症例」「治療効果」「患者様の声」「before/after」等の語やそれに類する表現を使わない"
)

RESEARCHER_SYSTEM_PROMPT = f"""あなたは歯科医院経営（個人事業主・訪問診療あり）に関するThreadsアカウントの
コンテンツリサーチャーです。院長（開業医）のペルソナで発信するアカウントの
「ネタ出し」を担当します。

{COMPLIANCE_RULES_TEXT}

出力は必ず有効なJSONオブジェクトのみとし、説明文やコードフェンスは付けないでください。"""


def _build_user_prompt(node_info, recent_titles):
    recent_titles_text = (
        "\n".join(f"- {t}" for t in recent_titles) if recent_titles else "（まだ投稿履歴なし）"
    )
    return f"""以下のノードについて、Threads投稿1本分のネタを1件作成してください。

カテゴリ: {node_info['category_name']}
ノード: {node_info['label']}

このノードで直近使用済みのネタタイトル（内容が重複しないようにすること）:
{recent_titles_text}

次のJSONスキーマちょうどのオブジェクトを1つ出力してください:
{{
  "title": "ネタの一言タイトル（15〜25文字程度）",
  "angle": "切り口の説明（1〜2文）",
  "key_points": ["投稿に盛り込む具体的な要点（経営・制度・実務に関するもの）を3〜5個の配列で"],
  "persona_note": "この投稿で強調すべき院長としてのスタンスや立場",
  "cta_hint": "投稿末尾で促したい行動の方向性（例:フォロー訴求。患者集客の直接的な誘導ではないこと）",
  "compliance_note": "このネタが医療広告ガイドライン上、患者の症例・治療効果に触れていないことの自己確認メモ"
}}
"""


def _idea_flat_text(idea: dict) -> str:
    parts = [
        idea.get("title", ""),
        idea.get("angle", ""),
        " ".join(idea.get("key_points", []) or []),
        idea.get("persona_note", ""),
        idea.get("cta_hint", ""),
    ]
    return "\n".join(parts)


def generate_idea_for_node(node_info, recent_titles, max_retries=1):
    """1ノード分のネタをLLMで生成し、NGワードチェックを通す。

    NGワードが検出された場合は1回だけ再生成を試み、それでもNGなら
    そのノードのネタ生成を諦めて None を返す（このネタは出力しない）。
    """
    user_prompt = _build_user_prompt(node_info, recent_titles)
    attempt = 0
    while attempt <= max_retries:
        attempt += 1
        idea = llm_client.complete_json(RESEARCHER_SYSTEM_PROMPT, user_prompt)
        violations = find_ng_violations(_idea_flat_text(idea))
        if not violations:
            idea["_ng_violations"] = []
            return idea
        logger.warning(
            "ノード '%s' のネタ生成でNGワード検出（試行%d回目）: %s",
            node_info["node_id"], attempt, violations,
        )
        user_prompt += (
            f"\n\n前回の出力には次のNG表現が含まれていました: {violations}。"
            "これらの表現を一切使わず、経営・制度手続きの話題だけで作り直してください。"
        )
    logger.error("ノード '%s' はNGワードを除去できず、ネタ生成を棄却しました。", node_info["node_id"])
    return None


def compute_scarcity_ranking(history):
    """投稿履歴をもとに、手薄なノードほど上位に来るランキングを返す。"""
    from collections import Counter

    counts = Counter()
    last_posted = {}
    for post in history.get("posts", []):
        if post.get("status") != "approved":
            continue
        node_id = post.get("node_id")
        if not node_id:
            continue
        counts[node_id] += 1
        ts = post.get("timestamp")
        if ts and (node_id not in last_posted or ts > last_posted[node_id]):
            last_posted[node_id] = ts

    now = datetime.now(timezone.utc)
    ranking = []
    for category_id, category_name, node_id, label in iter_leaf_nodes():
        count = counts.get(node_id, 0)
        last_ts = last_posted.get(node_id)
        if last_ts:
            try:
                days_since = (now - datetime.fromisoformat(last_ts)).days
            except ValueError:
                days_since = 9999
        else:
            days_since = 9999  # 未投稿ノードは最優先
        scarcity_score = days_since / (count + 1)
        ranking.append({
            "category_id": category_id,
            "category_name": category_name,
            "node_id": node_id,
            "label": label,
            "post_count": count,
            "days_since_last_post": days_since,
            "scarcity_score": round(scarcity_score, 2),
        })

    ranking.sort(key=lambda x: x["scarcity_score"], reverse=True)
    return ranking


def run_research(count: int = 3):
    _setup_logging()
    history = load_history()
    ranking = compute_scarcity_ranking(history)

    logger.info("手薄ノードランキング（上位%d件を採用）:", count)
    for rank in ranking[:count]:
        logger.info(
            "  - [%s] %s / %s (投稿数=%d, 未投稿日数=%d, scarcity=%.2f)",
            rank["category_name"], rank["label"], rank["node_id"],
            rank["post_count"], rank["days_since_last_post"], rank["scarcity_score"],
        )

    target_nodes = ranking[:count]
    ideas = []
    for rank in target_nodes:
        node_info = {
            "category_id": rank["category_id"],
            "category_name": rank["category_name"],
            "node_id": rank["node_id"],
            "label": rank["label"],
        }
        recent_titles = recent_titles_for_node(history, rank["node_id"])
        idea = generate_idea_for_node(node_info, recent_titles)
        if idea is None:
            continue
        idea_record = {
            **node_info,
            "scarcity_score": rank["scarcity_score"],
            "title": idea.get("title"),
            "angle": idea.get("angle"),
            "key_points": idea.get("key_points", []),
            "persona_note": idea.get("persona_note"),
            "cta_hint": idea.get("cta_hint"),
            "compliance_note": idea.get("compliance_note"),
        }
        ideas.append(idea_record)
        logger.info("ネタ生成完了: [%s] %s", node_info["node_id"], idea_record["title"])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{timestamp}_ideas.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scarcity_ranking_snapshot": ranking,
        "ideas": ideas,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info("ネタJSONを出力しました: %s（%d件）", output_path, len(ideas))
    return output_path


def main():
    parser = argparse.ArgumentParser(description="手薄ノードを判定し、投稿ネタをJSON化するリサーチャーエージェント")
    parser.add_argument("--count", type=int, default=3, help="生成するネタの件数（デフォルト3）")
    args = parser.parse_args()
    run_research(count=args.count)


if __name__ == "__main__":
    main()
