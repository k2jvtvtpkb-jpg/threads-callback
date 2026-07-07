"""投稿パターン定義（18種類）。

ライターはこの中から「直近3件と同じパターンではないもの」をローテーションで選び、
pattern["hook_instruction"] に従って1行目（フック）を組み立てる。
"""

POST_PATTERNS = [
    {
        "pattern_id": "exposure",
        "name": "暴露系",
        "hook_instruction": "「実はこれ、業界ではあまり言われませんが」のように、内側の人間しか知らない事実を明かす切り口で1行目を書く。",
        "body_instruction": "業界の慣習・裏側を経営者目線で率直に明かし、最後に読者への実務的な示唆で締める。",
    },
    {
        "pattern_id": "assertion",
        "name": "断言型",
        "hook_instruction": "「〜は不要です。」のように、強い言い切りの一文から始める。",
        "body_instruction": "断言の根拠を経営データや自身の経験から2〜3点で示す。",
    },
    {
        "pattern_id": "list",
        "name": "リスト系",
        "hook_instruction": "「開業医が最初にやるべきこと、3つ。」のように数字を伴う列挙予告で始める。",
        "body_instruction": "箇条書き風に改行を使い、3〜5項目を簡潔に列挙する。",
    },
    {
        "pattern_id": "qna",
        "name": "Q&A型",
        "hook_instruction": "読者からよく聞かれる質問をそのまま1行目に置く（例：「『社労士に頼まなくていいの？』とよく聞かれます。」）。",
        "body_instruction": "自問自答形式で質問に答え、実務上の判断基準を示す。",
    },
    {
        "pattern_id": "common_pitfall",
        "name": "あるある型",
        "hook_instruction": "「開業医あるある。」のように読者が思わず頷く共感フレーズで始める。",
        "body_instruction": "経営者としての共感を誘うエピソードを挙げつつ、教訓につなげる。",
    },
    {
        "pattern_id": "numeric_impact",
        "name": "数字インパクト型",
        "hook_instruction": "具体的な数字（金額・件数・年数など）を1行目の冒頭に置く。",
        "body_instruction": "その数字の背景・意味を解説し、経営判断への活かし方を示す。",
    },
    {
        "pattern_id": "comparison",
        "name": "比較型",
        "hook_instruction": "「Aだと思ってたら、実はBでした。」のようなギャップ・対比構文で始める。",
        "body_instruction": "誤解と実態を対比しながら説明し、実務での注意点を添える。",
    },
    {
        "pattern_id": "warning",
        "name": "警告型",
        "hook_instruction": "「これ、知らずにやると痛い目を見ます。」のように注意喚起で始める。",
        "body_instruction": "リスクの具体的内容と回避策を経営・制度面から解説する。",
    },
    {
        "pattern_id": "own_failure",
        "name": "自分の失敗談型",
        "hook_instruction": "「開業して◯年目、一番後悔しているのはこれです。」のように自身の経営上の失敗を認める一文で始める。",
        "body_instruction": "自分（院長）の経営判断ミスとその経緯・学びを率直に語る。患者に関する話題には触れない。",
    },
    {
        "pattern_id": "howto",
        "name": "手順解説型",
        "hook_instruction": "「◯◯の手続き、ステップはこの3つです。」のように手順予告で始める。",
        "body_instruction": "ステップ1、2、3の形式で実務手順を簡潔に解説する。",
    },
    {
        "pattern_id": "myth_busting",
        "name": "誤解訂正型",
        "hook_instruction": "「『◯◯』は誤解です。」のように世間の思い込みを否定する一文で始める。",
        "body_instruction": "誤解の内容と正しい理解を対比させ、経営・制度上の正確な知識を伝える。",
    },
    {
        "pattern_id": "system_explainer",
        "name": "制度解説型",
        "hook_instruction": "専門用語や制度名をそのまま1行目に置き、「これ、正しく説明できますか？」のように問いかける。",
        "body_instruction": "専門用語を開業医向けに噛み砕いて解説し、実務での対応方法を示す。",
    },
    {
        "pattern_id": "storytelling",
        "name": "ストーリーテリング型",
        "hook_instruction": "「ある朝、税理士から電話がかかってきました。」のように場面描写から始める。",
        "body_instruction": "経営上の出来事を時系列で語り、最後に得られた教訓を提示する。",
    },
    {
        "pattern_id": "self_qna",
        "name": "自問自答型",
        "hook_instruction": "「なぜウチは訪問診療を続けているのか。」のように自分自身への問いかけで始める。",
        "body_instruction": "問いに対する自分なりの答えを、経営方針や地域医療への考え方から述べる。",
    },
    {
        "pattern_id": "industry_realtalk",
        "name": "業界あるある本音型",
        "hook_instruction": "「歯科医院経営、正直しんどいのはここです。」のように本音を漏らす一文で始める。",
        "body_instruction": "経営者としての本音を率直に語りつつ、対処法や心構えで締める。",
    },
    {
        "pattern_id": "contrarian",
        "name": "逆説型",
        "hook_instruction": "常識とされていることの逆を1行目で述べる（例：「税理士がいなくても回ります。」）。",
        "body_instruction": "逆説の根拠を具体的な運用方法で裏付ける。",
    },
    {
        "pattern_id": "conclusion_first",
        "name": "先出し結論型",
        "hook_instruction": "結論を1行目で先に言い切る（例：「承継は『契約書』より『引き継ぎ期間』が命です。」）。",
        "body_instruction": "結論に至った理由を2〜3点で後付けする（結論→理由の順）。",
    },
    {
        "pattern_id": "checklist",
        "name": "チェックリスト型",
        "hook_instruction": "「◯◯前に確認すべきこと、チェックリストにしました。」のように確認事項予告で始める。",
        "body_instruction": "□（チェックボックス）を使い、確認すべき項目を簡潔に並べる。",
    },
]

PATTERN_IDS = [p["pattern_id"] for p in POST_PATTERNS]


def find_pattern(pattern_id):
    for p in POST_PATTERNS:
        if p["pattern_id"] == pattern_id:
            return p
    return None
