"""AI感検出スクリプト。使い方: python scripts/ai_detect.py <ファイル>

検出結果の表と、100文字あたりの検出数（AI感スコア）を出す。
"""
import re
import sys

PATTERNS = {
    "逃げ推量": [
        r"と言えるでしょう", r"ではないでしょうか", r"と考えられます",
        r"かもしれません", r"と言えます", r"(?<!言える)でしょう。",
    ],
    "副詞": [r"まさに", r"やはり", r"非常に", r"とても", r"本当に", r"しっかり"],
    "テンプレ": [
        r"いかがでしたか", r"結論から言うと", r"について解説します",
        r"を見ていきましょう", r"ぜひ.{0,10}してみてください", r"^#+ .*とは[？?]",
    ],
    "抽象語": [r"様々な", r"さまざまな", r"多くの", r"重要です", r"ポイントです", r"魅力です"],
    "3点セット": [r"[^、。]+も[^、。]+も[^、。]+も", r"[^、。]+、[^、。]+、そして[^、。]+"],
}


def find_bullet_triplets(lines):
    """ちょうど3項目の箇条書きブロックの開始行を返す。"""
    hits, run, start = [], 0, 0
    for i, line in enumerate(lines + [""]):
        if re.match(r"^\s*([-*・]|\d+[.)])\s+", line):
            if run == 0:
                start = i
            run += 1
        else:
            if run == 3:
                hits.append(start + 1)
            run = 0
    return hits


def find_same_endings(sentences):
    """「です。」「ます。」で終わる文が3回以上連続した箇所の数。"""
    count, run = 0, 0
    for s in sentences:
        if re.search(r"(です|ます)$", s):
            run += 1
            if run == 3:
                count += 1
        else:
            run = 0
    return count


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.stdout.reconfigure(encoding="utf-8")
    text =open(sys.argv[1], encoding="utf-8").read()
    lines = text.splitlines()

    results = []
    for kind, pats in PATTERNS.items():
        for pat in pats:
            for n, line in enumerate(lines, 1):
                for m in re.finditer(pat, line):
                    results.append((kind, n, m.group(0)))
    for n in find_bullet_triplets(lines):
        results.append(("3点セット", n, "3項目の箇条書き"))

    sentences = [s.strip() for s in re.split(r"。", text) if s.strip()]
    same_end = find_same_endings(sentences)

    chars = max(len(re.sub(r"\s", "", text)), 1)
    score = (len(results) + same_end) / chars * 100

    print("| 種類 | 行 | 該当 |")
    print("|---|---|---|")
    for kind, n, hit in sorted(results, key=lambda r: r[1]):
        print(f"| {kind} | {n} | {hit} |")
    print()
    by_kind = {}
    for kind, _, _ in results:
        by_kind[kind] = by_kind.get(kind, 0) + 1
    summary = "／".join(f"{k} {v}" for k, v in by_kind.items()) or "なし"
    print(f"検出 {len(results)} 件（{summary}）、同じ文末の3連続 {same_end} 箇所")
    print(f"AI感スコア: {score:.2f}（100文字あたり。0.5未満が目安）")


if __name__ == "__main__":
    main()
