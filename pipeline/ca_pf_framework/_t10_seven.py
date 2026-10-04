#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_seven.py --- 10 µm 盒的**七项监控**（tag/步可参数化）。

用法：python _t10_seven.py <tag> <step1,step2,...>

## 量具口径（**全部沿用本会话已核实过的**，不另造）
* 物理相 = `band_fld == k AND band_val < 0`（**`band_val` 就是带符号距离 φ**）
* **排除场 0**（= 母相 β）
* 26-连通分量；对**每个分量**做 PCA 极差 ⇒ 长/宽/厚
* **不用** CSV 的 `n_lath`/`w_lath`/`ths`（`_bk_measure.py:176` 已证是**包围盒跨度**，会被碎片撑大）
* 快照是 (胞,场) 对稀疏存储 ⇒ 全盒统计会重复计数，**只按场统计**

## 七项
① 形核正确性（核对 `df` 与理论 ΔG(Ms)）
② 新的形核**是不是板条状**（最大分量的长/厚、以及该场 pieces）
③ **长宽比变化**（长/宽、长/厚，随 step）
④ **堆叠成块**（CSV `blk_laths`）
⑤⑥ **块间影响 / 自协调**（CSV `nblk_sig`、`n_var_sig`；`n_var_sig ≥ 2` 是自协调的前提）
⑦ **一场一板条**（每场 pieces 分布 + 单块场占比）
"""
import csv
import os
import subprocess
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
DX = 62.5e-9
S26 = ndimage.generate_binary_structure(3, 3)
DRY = os.path.join(HERE, "_exp/_bk_t5/dry_%s")


def load_step(tag, st):
    fs = [f for f in os.listdir(DRY % tag) if f.endswith(".npz") and ("%05d" % st) in f]
    if not fs:
        return None
    p = os.path.join(DRY % tag, sorted(fs)[0])
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z["N"]))
        bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
        bv = np.asarray(z["band_val"]).ravel()
        bf = np.asarray(z["band_fld"]).ravel()
    return N, bi, bv, bf


def analyse(tag, st):
    r = load_step(tag, st)
    if r is None:
        return None
    N, bi, bv, bf = r
    out = []
    for k in np.unique(bf[bv < 0]):
        if int(k) == 0:
            continue
        sel = (bf == k) & (bv < 0)
        if sel.sum() < 30:
            continue
        idx = bi[sel]
        g = np.zeros((N, N, N), bool)
        g[idx // (N * N), (idx // N) % N, idx % N] = True
        lab, nc = ndimage.label(g, structure=S26)
        if nc == 0:
            continue
        sz = np.bincount(lab.ravel())[1:]
        big = int(np.argmax(sz)) + 1
        cc = np.argwhere(lab == big).astype(float)
        if len(cc) < 30:
            continue
        c0 = cc - cc.mean(0)
        _, _, vt = np.linalg.svd(c0, full_matrices=False)
        ext = np.array([(c0 @ vt[i]).max() - (c0 @ vt[i]).min() + 1.0
                        for i in range(3)])
        o = np.argsort(ext)[::-1]
        e = ext[o] * DX * 1e9                       # nm
        out.append(dict(k=int(k), cells=int(sel.sum()), big=int(sz[big - 1]),
                        nc=int(nc), main=float(sz.max()) / max(sz.sum(), 1),
                        L=e[0], W=e[1], T=e[2]))
    return N, out


def csv_rows(tag):
    p = os.path.join(DRY % tag, "series.csv")
    if not os.path.exists(p):
        return []
    n = int(subprocess.check_output(["wc", "-l", p]).split()[0])
    rr = []
    for _ in range(6):
        with open(p, "r", newline="", encoding="utf-8", errors="replace") as fh:
            r = list(csv.DictReader(fh))
        if len(r) >= len(rr):
            rr = r
        if len(rr) >= n - 1:
            break
    return rr


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "t10N160"
    steps = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2
                              else ["100"])]
    print("=" * 108)
    print("★ 七项监控  tag=%s   10 µm 盒(N=160, nv=220)" % tag)
    print("=" * 108)
    for st in steps:
        r = analyse(tag, st)
        if r is None:
            print("\n── step %d：**无快照** ──" % st)
            continue
        N, rows = r
        print("\n── step %d（带内胞场数 %d）──" % (st, len(rows)))
        if not rows:
            print("   （无够大的场）")
            continue
        rows.sort(key=lambda d: -d["big"])
        print("   %-5s %-8s %-7s %-7s %-8s %-8s %-8s %-7s %-7s"
              % ("场", "带内胞", "主片胞", "主体%", "碎片", "长nm", "宽nm", "长/宽", "长/厚"))
        for d in rows[:8]:
            print("   %-5d %-8d %-7d %-7.0f %-8d %-8.0f %-8.0f %-7.2f %-7.2f"
                  % (d["k"], d["cells"], d["big"], 100 * d["main"], d["nc"],
                     d["L"], d["W"], d["L"] / max(d["W"], 1e-9),
                     d["L"] / max(d["T"], 1e-9)))
        # ⑦ 一场一板条
        one = sum(1 for d in rows if d["nc"] == 1)
        print("   ⑦ 一场一板条：%d/%d = **%.0f%%** 的场是单一连通体（对照末态 0%%）"
              % (one, len(rows), 100.0 * one / len(rows)))
        print("   ② 板条状：长/厚 中位 = **%.2f**（设计 1000/510 = 1.96；"
              "成熟目标 ≥10）"
              % float(np.median([d["L"] / max(d["T"], 1e-9) for d in rows])))
        print("   ③ 长/宽 中位 = **%.2f**（设计 1000/500 = 2.0）"
              % float(np.median([d["L"] / max(d["W"], 1e-9) for d in rows])))
    print()
    print("── ④⑤⑥ 块表（CSV 原列；`blk_laths` = 块内板条数分布）──")
    rr = csv_rows(tag)
    for r in rr[-6:]:
        print("   step %-6s nslab=%-4s nblk=%-4s **n_var_sig=%-3s** blk_laths=%s"
              % (r.get("step"), r.get("nslab_n"), r.get("nblk_sig"),
                 r.get("n_var_sig"), (r.get("blk_laths") or "")[:36]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
