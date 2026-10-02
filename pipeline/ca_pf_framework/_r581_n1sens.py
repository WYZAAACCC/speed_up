#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_n1sens.py --- ★★★★★★ **`nslab_n1` 的敏感性分析**（R151 那个分析要用**正确口径**重做）

## 背景
R151 我算过：**归档口径 `nslab_n`** 在 F 上 **44/49 步增量为 0** ⇒ 判它"几乎不动"。
**但 R165 查明：`nslab_n` 是 R30 **故意冻结**的归档口径** ⇒ **那个结论**不属于正确口径**。
**⇒ 本轮用 `nslab_n1`（自适应柱 + min_run=1）重做**，并**与 3-D 场计数对照**。

## 三个口径
| 口径 | 来源 | 性质 |
|---|---|---|
| **`nslab_n`** | 归档柱（`r_col`=300nm、`min_run`=2） | **R30 冻结，只为历史可复现** |
| **★ `nslab_n1`** | **自适应柱 + `min_run`=1** | **★ 判决用这个** |
| **3-D 场计数** | **快照 `vmap` 分组** | **真值（但每 100 步才有）** |
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
# ★ 3-D 场计数（来自快照，实测；**带口径**：按 vmap 分组的非零场个数）
TRUTH3D = {
    'F': {0: 1, 100: 13, 200: 22, 250: 29},
    'G': {0: 1, 100: 13, 200: 23, 250: 23},
    'L': {0: 1},
}
TAGS = sys.argv[2:] or ['E', 'F', 'G', 'L']


def main():
    for t in TAGS:
        p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
        if not os.path.exists(p):
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        hdr = list(rows[0].keys())
        ks = [r[hdr[0]] for r in rows]

        def col(name):
            out = []
            for r in rows:
                v = r.get(name, '')
                try:
                    out.append(float(v))
                except Exception:
                    out.append(float('nan'))
            return out

        a0, a1 = col('nslab_n'), col('nslab_n1')
        print('=' * 100)
        print('臂 %s（%d 行）' % (t, len(rows)))
        print('=' * 100)

        for nm, arr in (('nslab_n（归档）', a0), ('★ nslab_n1（正确）', a1)):
            d = [arr[i + 1] - arr[i] for i in range(len(arr) - 1)]
            fin = [x for x in d if x == x]
            z = sum(1 for x in fin if x == 0)
            up = sum(1 for x in fin if x > 0)
            dn = sum(1 for x in fin if x < 0)
            print('  %-22s 首=%-5g 末=%-5g  增量: 0 的 %d/%d，升 %d，**降 %d**'
                  % (nm, arr[0], arr[-1], z, len(fin), up, dn))

        # 与 3-D 对照
        tr = TRUTH3D.get(t, {})
        if tr:
            print()
            print('  ── 与 3-D 场计数对照（真值只在快照步有）──')
            print('   %-6s %-12s %-12s %-12s %s' % ('step', '3-D', 'nslab_n', 'nslab_n1', '谁更近'))
            for r in rows:
                k = r[hdr[0]]
                try:
                    kk = int(float(k))
                except Exception:
                    continue
                if kk not in tr:
                    continue
                i = ks.index(k)
                t3 = tr[kk]
                x0, x1 = a0[i], a1[i]
                d0, d1 = abs(x0 - t3), abs(x1 - t3)
                who = '★ n1' if d1 < d0 else ('n（归档）' if d0 < d1 else '平')
                print('   %-6d %-12g %-12g %-12g %s（|Δ| %.0f vs %.0f）'
                      % (kk, t3, x0, x1, who, d0, d1))
        print()
    print('=' * 100)
    print('★ 判读：')
    print(' · **增量为 0 的比例低 + 有升有降** ⇒ 该口径**携带信息**')
    print(' · **与 3-D 更近** ⇒ 该口径更接近真值（但**一条柱穿不过 3-D 全部板条** ⇒ 仍会低）')
    print('=' * 100)


if __name__ == '__main__':
    main()
