"""リサーチャー→ライターを一括実行するCLIエントリポイント。

Threadsへの実投稿(ポスターエージェント)はまだ実装・実行しない。
生成結果は output/ 以下のJSON/Markdownファイルと logs/ 以下のログファイル、
data/post_history.json に出力されるのみ。

使い方:
    export ANTHROPIC_API_KEY=sk-ant-...
    python run_pipeline.py --count 3
"""

import argparse

from agents.researcher import run_research
from agents.writer import run_writer


def main():
    parser = argparse.ArgumentParser(description="歯科医院経営Threadsコンテンツ生成パイプライン（リサーチャー→ライター）")
    parser.add_argument("--count", type=int, default=3, help="生成するネタ件数（デフォルト3）")
    args = parser.parse_args()

    ideas_path = run_research(count=args.count)
    run_writer(input_path=ideas_path)


if __name__ == "__main__":
    main()
