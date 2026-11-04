"""楽天ウェブサービスで商品を探し、アフィリエイトリンク付きの表を出す。

使い方:
    python scripts/rakuten_search.py ranking --genre beauty
    python scripts/rakuten_search.py ranking --age 30 --sex female
    python scripts/rakuten_search.py search --keyword "保湿クリーム 乾燥肌" [--genre beauty] [--min-review 100]
    （どちらも --dry-run で、キーを伏せたリクエストURLだけ表示）

環境変数（クラウド環境に社長が登録。ファイルには書かない）:
    RAKUTEN_APP_ID        楽天ウェブサービスのアプリID
    RAKUTEN_ACCESS_KEY    同じアプリのアクセスキー
    RAKUTEN_AFFILIATE_ID  楽天アフィリエイトID（これがないとリンクに報酬が付かない）
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINTS = {
    "search": "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701",
    "ranking": "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601",
}
# 楽天市場のジャンルID。違っていたら https://webservice.rakuten.co.jp/ のジャンル検索APIで確認する
GENRES = {"beauty": "100939", "diy": "100005"}


def build_params(a):
    p = {"format": "json", "formatVersion": "2"}
    if a.genre:
        p["genreId"] = GENRES.get(a.genre, a.genre)
    if a.mode == "ranking":
        if a.age:
            p["age"] = str(a.age)
        if a.sex:
            p["sex"] = "1" if a.sex == "female" else "0"
    else:
        p["keyword"] = a.keyword
        p["sort"] = "-reviewCount"
        p["hasReviewFlag"] = "1"
        p["hits"] = str(a.hits)
    return p


def fetch(url, params, access_key):
    req = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params),
        headers={"accessKey": access_key, "User-Agent": "ai-affiliate-company/1.0"},
    )
    for wait in (0, 2, 5):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                sys.exit(f"楽天APIエラー {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    sys.exit("楽天APIの回数制限（429）が続いたため中止しました")


def cell(s):
    return str(s).replace("|", "／").replace("\n", " ")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap =argparse.ArgumentParser()
    ap.add_argument("mode", choices=["ranking", "search"])
    ap.add_argument("--genre", help="beauty / diy / ジャンルID")
    ap.add_argument("--age", type=int, choices=[10, 20, 30, 40, 50])
    ap.add_argument("--sex", choices=["female", "male"])
    ap.add_argument("--keyword")
    ap.add_argument("--hits", type=int, default=20)
    ap.add_argument("--min-review", type=int, default=0, help="レビュー件数がこれ未満の商品を除く")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.mode == "search" and not a.keyword:
        sys.exit("search には --keyword が必要です")
    if a.mode == "ranking" and a.genre and (a.age or a.sex):
        sys.exit("ranking では --genre と --age/--sex を同時に使えません")

    params = build_params(a)
    if a.dry_run:
        print(ENDPOINTS[a.mode] + "?" + urllib.parse.urlencode({**params, "applicationId": "***", "affiliateId": "***"}))
        return

    app_id, key, aff = (os.environ.get(k) for k in ("RAKUTEN_APP_ID", "RAKUTEN_ACCESS_KEY", "RAKUTEN_AFFILIATE_ID"))
    if not (app_id and key):
        sys.exit("RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY が設定されていません")
    params["applicationId"] = app_id
    if aff:
        params["affiliateId"] = aff

    data = fetch(ENDPOINTS[a.mode], params, key)
    items = [i for i in data.get("Items", []) if int(i.get("reviewCount") or 0) >= a.min_review]

    print(f"取得日時：{time.strftime('%Y-%m-%d %H:%M', time.localtime())}（価格・ポイント倍率はこの時点のもの）")
    if not aff:
        print("※ RAKUTEN_AFFILIATE_ID が未設定のため、リンクに報酬は付きません")
    print()
    print("| # | 商品名 | ショップ | 価格(円) | レビュー | 料率(%) | ポイント倍率 | リンク |")
    print("|---|---|---|---|---|---|---|---|")
    for n, i in enumerate(items, 1):
        print("| " + " | ".join(cell(x) for x in (
            i.get("rank", n),
            i.get("itemName", "")[:60],
            i.get("shopName", ""),
            i.get("itemPrice", ""),
            f"{i.get('reviewAverage', '')}（{i.get('reviewCount', 0)}件）",
            i.get("affiliateRate", "要確認"),
            i.get("pointRate", ""),
            i.get("affiliateUrl") or i.get("itemUrl", ""),
        )) + " |")


if __name__ == "__main__":
    main()
