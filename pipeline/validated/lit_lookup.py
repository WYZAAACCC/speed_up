#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 **OpenAlex / Crossref 的开放 API** 查文献并取回摘要 —— 本项目取文献数值的正路。

## 为什么需要它

本机（2026-09-20 实测）：
  * `WebFetch` 对**所有域名**都报 "Unable to verify if domain … is safe to fetch" ✗
  * `WebSearch` 可用，但只给**摘要片段**，拿不到表格里的数
  * WSL 里 `curl`：**arXiv 200** ✅、**api.openalex.org 200** ✅、**api.crossref.org 200** ✅、
    mdpi.com 403 ✗、osti.gov 超时 ✗、sciencedirect ✗
⇒ **只能走开放 API**。OpenAlex 的 `abstract_inverted_index` 可以还原出完整摘要，
  而**摘要里常常就有关键数值**；它还会给 `best_oa_location` 的 PDF 链接（可 curl）。

## 用法

    python3 lit_lookup.py "Ti-6Al-4V partition coefficient vanadium" --n 8
    python3 lit_lookup.py "Ti-6Al-4V LPBF texture MUD" --n 8 --abs 900
    python3 lit_lookup.py --doi 10.1016/j.jcrysgro.2021.126112
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

UA = {"User-Agent": "speed_up-lit-lookup/1.0 (mailto:research@example.com)"}


def get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def unabstract(inv):
    """OpenAlex 的 abstract_inverted_index -> 文本"""
    if not inv:
        return ""
    pos = {}
    for w, ids in inv.items():
        for i in ids:
            pos[i] = w
    return " ".join(pos[k] for k in sorted(pos))


def show(w, abslen):
    t = w.get("display_name") or w.get("title") or "?"
    y = w.get("publication_year", "?")
    doi = (w.get("doi") or "").replace("https://doi.org/", "")
    oa = w.get("open_access") or {}
    loc = w.get("best_oa_location") or {}
    pdf = loc.get("pdf_url") or loc.get("landing_page_url") or ""
    ab = unabstract(w.get("abstract_inverted_index"))
    print(f"\n{'='*78}")
    print(f"[{y}] {t}")
    print(f"  DOI : {doi or '(无)'}")
    print(f"  被引: {w.get('cited_by_count','?')}   OA: {oa.get('oa_status','?')}")
    if pdf:
        print(f"  PDF : {pdf}")
    if ab:
        print(f"  摘要: {ab[:abslen]}" + (" …（截断）" if len(ab) > abslen else ""))
    else:
        print("  摘要: （OpenAlex 没有）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--abs", type=int, default=700, help="摘要截断长度")
    ap.add_argument("--doi", default="")
    ap.add_argument("--from-year", type=int, default=0)
    a = ap.parse_args()

    if a.doi:
        w = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(a.doi))
        show(w, a.abs)
        return

    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(a.query)
           + f"&per-page={a.n}&sort=relevance_score:desc")
    if a.from_year:
        url += f"&filter=from_publication_date:{a.from_year}-01-01"
    d = get(url)
    print(f"查询：{a.query}")
    print(f"命中 {d.get('meta', {}).get('count', '?')} 篇，取前 {len(d.get('results', []))}")
    for w in d.get("results", []):
        show(w, a.abs)


if __name__ == "__main__":
    main()
