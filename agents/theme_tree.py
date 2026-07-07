"""テーマツリー定義。

歯科医院経営・開業医（個人事業主・訪問診療あり）というジャンルの中で、
投稿ネタを分類するためのカテゴリ／ノード構造。
リサーチャーはこの木構造のリーフノードごとに投稿の蓄積状況を見て、
手薄なノードを判定する。
"""

THEME_TREE = [
    {
        "category_id": "succession_management",
        "category_name": "クリニック承継・経営",
        "nodes": [
            {"node_id": "succession_backstage", "label": "承継の裏側"},
            {"node_id": "asset_goodwill_handling", "label": "固定資産・営業権処理"},
            {"node_id": "succession_failures", "label": "失敗談"},
        ],
    },
    {
        "category_id": "payroll_social_insurance",
        "category_name": "給与計算・社保手続き",
        "nodes": [
            {"node_id": "kosei_nenkin_new_registration", "label": "厚生年金新規適用"},
            {"node_id": "kyuryo_rakuda_operation", "label": "給料らくだ運用"},
            {"node_id": "no_accountant_knowhow", "label": "税理士要らずノウハウ"},
        ],
    },
    {
        "category_id": "home_visit_dental_care",
        "category_name": "訪問診療",
        "nodes": [
            {"node_id": "consent_form_paperwork", "label": "同意書・書類整備"},
            {"node_id": "medical_coordination", "label": "医科連携"},
            {"node_id": "regional_care_reality", "label": "地域医療のリアル"},
        ],
    },
    {
        "category_id": "staff_management",
        "category_name": "スタッフマネジメント",
        "nodes": [
            {"node_id": "private_car_policy", "label": "私有車規程"},
            {"node_id": "retirement_payout", "label": "退職金処理"},
            {"node_id": "hiring_retention", "label": "採用・定着"},
        ],
    },
    {
        "category_id": "owner_daily_life",
        "category_name": "開業医の日常",
        "nodes": [
            {"node_id": "work_life_balance", "label": "経営とプライベートのバランス"},
        ],
    },
]


def iter_leaf_nodes():
    """(category_id, category_name, node_id, label) のタプルを全ノード分returnする。"""
    for category in THEME_TREE:
        for node in category["nodes"]:
            yield category["category_id"], category["category_name"], node["node_id"], node["label"]


def find_node(node_id):
    """node_idからノード情報を引く。見つからなければNone。"""
    for category in THEME_TREE:
        for node in category["nodes"]:
            if node["node_id"] == node_id:
                return {
                    "category_id": category["category_id"],
                    "category_name": category["category_name"],
                    "node_id": node["node_id"],
                    "label": node["label"],
                }
    return None


def all_node_ids():
    return [node_id for _, _, node_id, _ in iter_leaf_nodes()]
