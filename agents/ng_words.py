"""医療広告ガイドライン対応の軽量バリデーション。

このリストと関数は「最後の砦」の機械的セーフティネットであり、
医療広告ガイドラインへの適合を保証するものではない。
最終的な公開判断は必ず人間（院長・法務担当）が行うこと。

厳守事項:
- 患者の症例・治療効果・患者の声には一切言及しない
- 経営・組織運営・制度手続きの話題のみに限定
- 患者が特定されうる情報を含めない
"""

import re

# NGワード（部分一致・大小文字無視で検出）
NG_WORDS = [
    "症例",
    "治療効果",
    "治療前",
    "治療後",
    "術前",
    "術後",
    "ビフォーアフター",
    "before/after",
    "before after",
    "患者様の声",
    "患者の声",
    "お客様の声",
    "患者様写真",
    "患者写真",
    "口コミ",
    "体験談（患者",
    "改善事例",
    "施術効果",
    "実績症例",
    "治癒率",
    "有効率",
    "満足度調査",
    "ビフォー・アフター",
]

# 患者を特定しうる/症例を想起させる表現の緩いパターン検出（正規表現）
NG_PATTERNS = [
    r"\d+歳の(患者|女性|男性|方)",  # 「45歳の患者様」のような症例的表現
    r"来院された.*(患者|方)",
]


def find_ng_violations(text: str):
    """テキスト中のNGワード・NGパターンを検出し、ヒットしたものの一覧を返す。"""
    if not text:
        return []

    hits = []
    lowered = text.lower()
    for word in NG_WORDS:
        if word.lower() in lowered:
            hits.append(word)

    for pattern in NG_PATTERNS:
        if re.search(pattern, text):
            hits.append(f"pattern:{pattern}")

    return hits


def validate_no_ng_words(text: str):
    """(問題なしか, 違反リスト) のタプルを返す。"""
    violations = find_ng_violations(text)
    return (len(violations) == 0, violations)
