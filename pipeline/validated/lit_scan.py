#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量文献数值扫描：OpenAlex 找 OA 论文 → 下载 → 抽文本 → 关键词扫描。

## 为什么需要它

本机 `WebFetch` 对所有域名都不通（2026-09-20 实测），`WebSearch` 只给摘要片段。
能用的通道是：OpenAlex/Crossref API + `curl` 下载 OA 的 PDF
（实测 nature.com / link.springer.com / iopscience / 机构仓库可直连；
mdpi 403、sciencedirect ✗、tandfonline 403、osti 超时）。

单个 PDF 孤零零地看没用 —— **要的是从一批里筛出"哪几篇真的有那张表"**，
本脚本就是干这个的。

## 用法

    python3 lit_scan.py --queries "Ti-6Al-4V LPBF texture MUD" "Ti-6Al-4V prior beta grain" \
                        --n 12 --grep 'MUD|times random|pole figure|texture index' \
                        --out /root/work/lit/scan_texture
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

UA = {"User-Agent": "speed_up-lit-scan/1.0 (mailto:research@example.com)"}
# 实测可直连的域名（前缀匹配）
OK_HOSTS = ("link.springer.com", "www.nature.com", "nature.com",
            "iopscience.iop.org", "scholarworks.", "arxiv.org",
            "www.researchgate.net", "repository.", "dspace.", "hal.science")


def get_json(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def unabstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, ids in inv.items():
        for i in ids:
            pos[i] = w
    return " ".join(pos[k] for k in sorted(pos))


def find(query, n):
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(query)
           + f"&per-page={n}&sort=relevance_score:desc")
    return get_json(url).get("results", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--grep", required=True, help="扫描 PDF 文本用的正则")
    ap.add_argument("--out", required=True)
    ap.add_argument("--abs", type=int, default=400)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    pat = re.compile(a.grep, re.I)

    seen, cand = set(), []
    for q in a.queries:
        print(f"\n### 查询：{q}")
        for w in find(q, a.n):
            doi = (w.get("doi") or "").strip()
            if doi in seen:
                continue
            seen.add(doi)
            loc = w.get("best_oa_location") or {}
            pdf = loc.get("pdf_url") or ""
            ab = unabstract(w.get("abstract_inverted_index"))
            hit_abs = bool(pat.search(ab))
            cand.append(dict(doi=doi, title=w.get("display_name", "?"),
                             year=w.get("publication_year"), pdf=pdf, abs=ab))
            mark = "📄" if pdf else "  "
            tag = " ★摘要命中" if hit_abs else ""
            print(f"  {mark} [{w.get('publication_year')}] {w.get('display_name','?')[:88]}{tag}")

    json.dump(cand, open(os.path.join(a.out, "candidates.json"), "w"),
              ensure_ascii=False, indent=1)

    # --- 下载能下的 ---
    print(f"\n### 下载（只试实测可直连的域名）")
    got = []
    for c in cand:
        u = c["pdf"]
        if not u or not any(h in u for h in OK_HOSTS):
            continue
        f = os.path.join(a.out, re.sub(r"\W", "_", c["doi"])[:70] + ".pdf")
        if os.path.exists(f):
            got.append((c, f)); continue
        try:
            subprocess.run(["curl", "-sSL", "--max-time", "120", "-o", f, u],
                           check=False, capture_output=True)
            if os.path.exists(f) and os.path.getsize(f) > 20000:
                got.append((c, f))
                print(f"  ✅ {os.path.basename(f)} ({os.path.getsize(f)//1024} KB)")
            elif os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    # --- 抽文本 + 扫描 ---
    print(f"\n### 扫描（正则：{a.grep}）")
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("需要 pypdf（conda activate ml）")

    for c, f in got:
        t = f[:-4] + ".txt"
        if not os.path.exists(t):
            try:
                r = PdfReader(f)
                txt = "\n".join((p.extract_text() or "") for p in r.pages)
                open(t, "w", encoding="utf-8").write(txt)
            except Exception as e:
                print(f"  ⚠ {os.path.basename(f)} 抽取失败 {e}"); continue
        txt = open(t, encoding="utf-8", errors="replace").read()
        hits = [l.strip() for l in txt.splitlines() if pat.search(l)]
        if hits:
            print(f"\n  ★★ {c['title'][:80]}")
            print(f"     DOI {c['doi']}   {t}")
            for h in hits[:6]:
                print(f"       {h[:150]}")


if __name__ == "__main__":
    main()
