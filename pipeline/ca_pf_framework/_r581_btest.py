#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_btest.py --- ★★★★★ **用**已在盘上的数据**直接检验 R92 的公式 `_tgt = B × n_blk`**

## 为什么能直接检验（**不需要新算例**）
R92 从 `_bk_exp.py:2004-2010` 读出 **`_tgt = min(_Bt * _n_blk, nv)`**，
其中 `_Bt = --nuc-block-target`、`_n_blk = CL.alpha_km_n_lath(T, α)`。
**⇒ 若公式对，则 `n_target_final` 应当**正比于 `B`**（同一 `α_KM`/`T(t)` 下 `n_blk` 相同）。**

**而盘上的 N=160 长跑正好是**单变量**的：**
* `p2_b5`：`--nuc-block-target 5`
* `p2_b3`：`--nuc-block-target 3`
**其余逐字相同** ⇒ **预测 `n_target_final` = 15 : 9（比 5:3）**。

**⇒ 这是一次**零成本**的公式检验（P21：新数与前数矛盾时先怀疑量具 —— 这里是反过来，用旧数验新公式）。
"""
import json
import os
import sys

ROOTS = sys.argv[1:] or ['_exp/_bk_p2', '_exp/_bk_mb', '_exp/_bk_mn64']
WANT = ['p2_b5', 'p2_b3', 'p2_b5ov', 'p2_b5ps', 'p2_m12', 'p2_m12b', 'p2_m20',
        'p2_m12ov', 'p2_m20full', 'A', 'B', 'C', 'D', 'E', 'F']


def find(tag):
    for r in ROOTS:
        p = os.path.join(r, 'dry_' + tag, 'nuc_dbg.json')
        if os.path.exists(p):
            return p
    return None


def main():
    print('=' * 104)
    print('R92 公式的**零成本**检验：`n_target_final` 是否 ∝ `--nuc-block-target B`？')
    print('=' * 104)
    print(' %-12s %-8s %-14s %-10s %-12s %s'
          % ('tag', 'B', 'n_target', 'events', '推断 n_blk', '公式核对'))
    print(' ' + '-' * 100)
    rows = []
    for t in WANT:
        p = find(t)
        if not p:
            continue
        j = json.load(open(p, encoding='utf-8'))
        cfg = j.get('nuc_cfg', {})
        nt = j.get('n_target_final', None)
        ev = j.get('n_athermal_ev', None)
        # ★ B 不在 nuc_cfg 里（它是 CLI 直传）⇒ 从文档/命名推断，并如实标注
        B = {'p2_b5': 5, 'p2_b3': 3, 'p2_b5ov': 5, 'p2_b5ps': 5}.get(t, None)
        # n_blk 的独立估计：alpha_km_n_lath(T, α) 由 qs 钟的档位决定；
        # 这里只做**比值**核对（不需要知道 n_blk 的绝对值）
        nb = (nt / B) if (B and nt) else None
        chk = ''
        if B and nb:
            chk = 'n_blk ≈ %.2f' % nb
        print(' %-12s %-8s %-14s %-10s %-12s %s'
              % (t, B if B else '?', nt, ev, ('%.2f' % nb) if nb else '?', chk))
        rows.append((t, B, nt))
    # ★ 比值检验（**这才是判据**）
    print()
    print('─' * 104)
    d = {t: (B, nt) for t, B, nt in rows if B and nt}
    if 'p2_b5' in d and 'p2_b3' in d:
        B5, n5 = d['p2_b5']
        B3, n3 = d['p2_b3']
        print(' ★ **比值检验**（`p2_b5` vs `p2_b3`，两臂只差 `--nuc-block-target`）')
        print('     `B`      ：%d vs %d   ⇒ 比 = %.4f' % (B5, B3, B5 / B3))
        print('     `n_target`：%d vs %d   ⇒ 比 = %.4f' % (n5, n3, n5 / n3))
        print('     公式预测比 = B 之比 = %.4f' % (B5 / B3))
        rel = abs((n5 / n3) - (B5 / B3)) / (B5 / B3)
        print('     相对偏差 = %.4f%%' % (100 * rel))
        if rel < 0.02:
            print('     ⇒ ★★★★★ **公式 `_tgt = B × n_blk` 成立**（同 `n_blk` 下正比于 `B`）')
        else:
            print('     ⇒ ❌ **公式不成立或两臂还有其他差异** ⇒ 回去查（先怀疑量具/配置，P21）')
    else:
        print(' ⚠ `p2_b5`/`p2_b3` 的 `nuc_dbg.json` 还没落盘 ⇒ 本检验待跑完再做')
    print('=' * 104)
    print('⚠ 口径：`B` 不在 `nuc_dbg.json` 里（它是 CLI 直传）⇒ 上表的 `B` 是从**运行配置**填的；')
    print('   若某臂的配置与上表不符，请以 `_w2_r581_p2_<tag>.log` 的命令行为准。')
    print('=' * 104)


if __name__ == '__main__':
    main()
