"""はてなブログに記事を「下書き」としてアップロードする。公開はしない。

使い方:
    python scripts/hatena_post.py <記事.md> [--category DIY --category 床] [--dry-run]

記事ファイルの1行目 `# タイトル` をタイトル、2行目以降を本文として送る。
環境変数（クラウド環境のシークレットに社長が登録）:
    HATENA_ID       はてなID
    HATENA_BLOG_ID  diyfamiliar.hatenablog.com
    HATENA_API_KEY  はてなブログ 設定 > 詳細設定 > AtomPub の APIキー
"""
import argparse
import base64
import os
import re
import sys
import urllib.error
import urllib.request
from xml.sax.saxutils import escape


def build_entry(title, body, categories):
    cats = "".join(f'<category term="{escape(c, {'"': '&quot;'})}" />' for c in categories)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">
  <title>{escape(title)}</title>
  <content type="text/x-markdown">{escape(body)}</content>
  {cats}
  <app:control><app:draft>yes</app:draft></app:control>
</entry>"""


def read_article(path):
    text = open(path, encoding="utf-8").read().lstrip("﻿")
    first, _, body = text.partition("\n")
    m = re.match(r"^#\s+(.+)$", first.strip())
    if not m:
        sys.exit("1行目が `# タイトル` の形になっていません")
    return m.group(1).strip(), body.strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--category", action="append", default=[])
    p.add_argument("--dry-run", action="store_true", help="送信せずに送る内容を表示する")
    a = p.parse_args()

    title, body = read_article(a.file)
    xml = build_entry(title, body, a.category)
    if a.dry_run:
        print(xml)
        return

    hid, blog, key = (os.environ.get(k) for k in ("HATENA_ID", "HATENA_BLOG_ID", "HATENA_API_KEY"))
    if not (hid and blog and key):
        sys.exit("HATENA_ID / HATENA_BLOG_ID / HATENA_API_KEY が設定されていません")

    url = f"https://blog.hatena.ne.jp/{hid}/{blog}/atom/entry"
    auth = base64.b64encode(f"{hid}:{key}".encode()).decode()
    req = urllib.request.Request(
        url, data=xml.encode("utf-8"), method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/xml; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            resp = res.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        sys.exit(f"アップロード失敗: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")

    edit = re.search(r'<link rel="alternate" type="text/html" href="([^"]+)"', resp)
    print(f"下書きアップロード完了: {title}")
    print(f"確認URL: {edit.group(1) if edit else '(管理画面の下書き一覧を確認)'}")


if __name__ == "__main__":
    main()
