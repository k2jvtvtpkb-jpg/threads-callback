"""ライターエージェント。

リサーチャーが生成したネタ(JSON)から投稿文を作成する。
- 18種類の投稿パターンをローテーションし、直近3件（承認済み）と同じパターンは避ける
- 1行目のフックをパターンごとに指定
- 自己採点（フック/有益性/具体性/テンポ/ペルソナ一致度、平均7.0未満で書き直し、2回失敗で棄却）
- NGワード（医療広告ガイドライン対応）を生成前後でチェック

Threadsへの実際の投稿は一切行わない。出力は output/posts/ 配下のJSON・
サマリーファイルと data/post_history.json への記録、およびログのみ。
"""

import argparse
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agents import llm_client
from agents.history_store import append_post, load_history, recent_approved_patterns
from agents.ng_words import validate_no_ng_words
from agents.patterns import POST_PATTERNS

RESEARCH_DIR = Path(__file__).resolve().parent.parent / "output" / "research"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "posts"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

SCORE_THRESHOLD = 7.0
MAX_ATTEMPTS = 2
SCORE_AXES = ["hook", "usefulness", "concreteness", "tempo", "persona_fit"]

logger = logging.getLogger("writer")


def _setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(LOG_DIR / "writer.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[writer] %(message)s"))
    logger.addHandler(console_handler)


COMPLIANCE_RULES_TEXT = (
    "厳守事項（医療広告ガイドライン対応）:\n"
    "- 患者の症例・治療効果・患者の声には一切言及しない\n"
    "- 経営・組織運営・制度手続きの話題のみに限定する\n"
    "- 患者が特定されうる情報（年齢・性別・来院経緯等の症例的描写）を含めない\n"
    "- 「症例」「治療効果」「患者様の声」「before/after」等の語やそれに類する表現を使わない"
)

PERSONA_TEXT = (
    "あなたは個人事業主として歯科医院を経営する院長本人としてThreadsに投稿します。"
    "属性: 開業医・経営者、訪問診療も行っている、スタッフを雇用し給与計算や社会保険手続きにも"
    "自ら関わっている。口調は敬語一辺倒ではなく、経営者としての本音がにじむ率直な文体。"
    "読者は同業の開業医、承継や開業を検討している歯科医師。"
)

WRITER_SYSTEM_PROMPT = f"""{PERSONA_TEXT}

{COMPLIANCE_RULES_TEXT}

Threads投稿の文章ルール:
- 400字以内を目安にし、500字は超えないこと
- 1行目は指定されたフックの型に厳密に従うこと
- 改行を適度に使い、Threadsらしいテンポで書くこと
- 絵文字は使っても1〜2個までにとどめる
- 出力は投稿本文のみ。タイトル・説明・Markdown記法・前置きは一切付けない"""

SCORER_SYSTEM_PROMPT = f"""あなたは歯科医院経営Threadsアカウントの編集者です。下書きを厳しく採点してください。

{COMPLIANCE_RULES_TEXT}

採点軸（各0〜10の整数）:
- hook: 1行目でスクロールを止め、続きを読ませる力があるか
- usefulness: 読者（同業の開業医）の実務判断に役立つ情報が含まれているか
- concreteness: 抽象論ではなく、数字・制度名・具体的な手続き等が含まれているか
- tempo: 改行や文の長さのリズムがThreadsの投稿として読みやすいか
- persona_fit: 個人事業主として歯科医院を経営し、訪問診療も行う院長本人が書いた文章として自然か

さらに compliance_flag として、キーワード一致の有無にかかわらず、患者の症例・治療効果・
患者の声・患者を特定しうる描写など医療広告ガイドラインに抵触しうる表現が少しでも
あればtrueを返してください。

出力は必ず次のJSONスキーマちょうどのオブジェクトのみ:
{{
  "hook": 0,
  "usefulness": 0,
  "concreteness": 0,
  "tempo": 0,
  "persona_fit": 0,
  "compliance_flag": false,
  "compliance_notes": "懸念点があれば具体的に",
  "feedback": "書き直すなら何を直すべきか、具体的な改善指示"
}}"""


def _idea_summary_text(idea: dict) -> str:
    key_points = idea.get("key_points") or []
    key_points_text = "\n".join(f"- {p}" for p in key_points)
    return f"""タイトル: {idea.get('title', '')}
切り口: {idea.get('angle', '')}
要点:
{key_points_text}
強調すべきスタンス: {idea.get('persona_note', '')}
末尾で促す行動の方向性: {idea.get('cta_hint', '')}"""


def pick_pattern(history):
    excluded = set(recent_approved_patterns(history, n=3))
    candidates = [p for p in POST_PATTERNS if p["pattern_id"] not in excluded]
    if not candidates:
        candidates = POST_PATTERNS
    return random.choice(candidates)


def generate_draft(idea: dict, pattern: dict, feedback_note: str = None) -> str:
    user_prompt = f"""次のネタをもとに、指定されたパターンでThreads投稿を1本書いてください。

{_idea_summary_text(idea)}

投稿パターン: {pattern['name']}
1行目（フック）の作り方: {pattern['hook_instruction']}
本文の作り方: {pattern['body_instruction']}"""

    if feedback_note:
        user_prompt += f"\n\n前回の下書きへのフィードバック（必ず反映して書き直すこと）:\n{feedback_note}"

    return llm_client.complete_text(WRITER_SYSTEM_PROMPT, user_prompt, max_tokens=800)


def self_score(text: str, idea: dict, pattern: dict) -> dict:
    user_prompt = f"""以下の下書きを採点してください。

--- 下書き ---
{text}
--- ここまで ---

このネタの意図: {idea.get('angle', '')}
使用パターン: {pattern['name']}"""

    result = llm_client.complete_json(SCORER_SYSTEM_PROMPT, user_prompt)
    scores = {}
    for axis in SCORE_AXES:
        try:
            scores[axis] = int(result.get(axis, 0))
        except (TypeError, ValueError):
            scores[axis] = 0

    avg = sum(scores.values()) / len(SCORE_AXES)
    compliance_flag = bool(result.get("compliance_flag", False))
    if compliance_flag:
        avg = 0.0

    return {
        **scores,
        "avg": round(avg, 2),
        "compliance_flag": compliance_flag,
        "compliance_notes": result.get("compliance_notes", ""),
        "feedback": result.get("feedback", ""),
    }


def generate_post_for_idea(idea: dict, history: dict) -> dict:
    pattern = pick_pattern(history)
    attempts = []
    feedback_note = None

    for attempt_num in range(1, MAX_ATTEMPTS + 1):
        text = generate_draft(idea, pattern, feedback_note)
        ok, violations = validate_no_ng_words(text)

        if not ok:
            score_result = {
                **{axis: 0 for axis in SCORE_AXES},
                "avg": 0.0,
                "compliance_flag": True,
                "compliance_notes": f"NGワード検出: {violations}",
                "feedback": f"次のNG表現を除去し、経営・制度手続きの話題に限定して書き直してください: {violations}",
            }
        else:
            score_result = self_score(text, idea, pattern)

        attempts.append({
            "attempt": attempt_num,
            "text": text,
            "ng_violations": violations,
            "scores": score_result,
        })

        logger.info(
            "  試行%d: pattern=%s avg=%.2f compliance_flag=%s",
            attempt_num, pattern["pattern_id"], score_result["avg"], score_result["compliance_flag"],
        )

        if ok and not score_result["compliance_flag"] and score_result["avg"] >= SCORE_THRESHOLD:
            return {
                "status": "approved",
                "pattern": pattern["pattern_id"],
                "pattern_name": pattern["name"],
                "final_text": text,
                "final_avg_score": score_result["avg"],
                "attempts": attempts,
            }

        feedback_note = score_result.get("feedback") or score_result.get("compliance_notes")

    return {
        "status": "rejected",
        "pattern": pattern["pattern_id"],
        "pattern_name": pattern["name"],
        "final_text": None,
        "final_avg_score": attempts[-1]["scores"]["avg"] if attempts else 0.0,
        "attempts": attempts,
    }


def _latest_ideas_file():
    files = sorted(RESEARCH_DIR.glob("*_ideas.json"))
    if not files:
        raise FileNotFoundError(
            f"{RESEARCH_DIR} にネタJSONが見つかりません。先に researcher を実行してください。"
        )
    return files[-1]


def load_ideas(input_path=None):
    path = Path(input_path) if input_path else _latest_ideas_file()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def _write_summary(results, output_path):
    lines = [f"# 投稿生成サマリー ({datetime.now(timezone.utc).isoformat()})\n"]
    approved = [r for r in results if r["status"] == "approved"]
    rejected = [r for r in results if r["status"] == "rejected"]
    lines.append(f"承認: {len(approved)}件 / 棄却: {len(rejected)}件\n")

    for r in approved:
        lines.append(f"## [承認] {r['category_name']} / {r['label']} (pattern={r['pattern_name']}, avg={r['final_avg_score']})")
        lines.append("```")
        lines.append(r["final_text"])
        lines.append("```\n")

    for r in rejected:
        last_attempt = r["attempts"][-1] if r["attempts"] else {}
        reason = last_attempt.get("scores", {}).get("feedback") or last_attempt.get("scores", {}).get("compliance_notes", "")
        lines.append(f"## [棄却] {r['category_name']} / {r['label']} (pattern={r['pattern_name']})")
        lines.append(f"理由: {reason}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_writer(input_path=None):
    _setup_logging()
    ideas_payload, resolved_input_path = load_ideas(input_path)
    logger.info("ネタJSONを読み込みました: %s", resolved_input_path)

    history = load_history()
    results = []

    for idea in ideas_payload.get("ideas", []):
        logger.info("生成開始: [%s] %s", idea.get("node_id"), idea.get("title"))
        result = generate_post_for_idea(idea, history)

        record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category_id": idea.get("category_id"),
            "node_id": idea.get("node_id"),
            "idea_title": idea.get("title"),
            "pattern": result["pattern"],
            "status": result["status"],
            "text": result["final_text"],
            "avg_score": result["final_avg_score"],
        }
        history = append_post(history, record)

        logger.info(
            "生成結果: [%s] status=%s pattern=%s avg=%.2f",
            idea.get("node_id"), result["status"], result["pattern"], result["final_avg_score"],
        )

        results.append({
            **idea,
            **result,
            "history_id": record["id"],
        })

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{timestamp}_posts.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results}, f, ensure_ascii=False, indent=2)

    summary_path = OUTPUT_DIR / f"{timestamp}_posts_summary.md"
    _write_summary(results, summary_path)

    logger.info("投稿候補JSONを出力しました: %s", json_path)
    logger.info("サマリーを出力しました: %s", summary_path)
    logger.info("※ Threadsへの実投稿は行っていません（ポスターエージェント未実装・未実行）。")

    return json_path, summary_path


def main():
    parser = argparse.ArgumentParser(description="ネタから投稿文を生成するライターエージェント")
    parser.add_argument("--input", type=str, default=None, help="リサーチャー出力のネタJSONパス（省略時は最新のものを使用）")
    args = parser.parse_args()
    run_writer(input_path=args.input)


if __name__ == "__main__":
    main()
