#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r175_r165pre.py —— **R165 的前置接线核对**（单变量性 + 初态一致性）。

## 为什么必须先做这一步

`§113`/`§116`/`§128` 反复吃过同一个亏：**两臂"看着只差一个开关"，实际差了好几个**。
本脚本在**读判决之前**，先把 `meta.json` 的**全部键**逐项对比，回答：

* **W-1** λ=1 臂与 λ=0 对照臂**除了 `--f2-pair-gamma` 以外**，还有没有别的差异？
  ⚠ 已知风险：两个 λ=1 臂都带 **`--facet-proj 10`**（实测进程命令行）——
    若对照臂**不带**投影，则 R165 **不是单变量对照**，`G-1`/`G-2` 全部作废。
* **W-2** 两臂的 **`t=0` 行**是否一致（`Vt`、`nf3col`、厚度表）？
  若初态就不同 ⇒ **差异不能归因于 λ**。
* **W-3** 打印各自**当前进度**（末步），避免把中途读数当末态（硬规则 ③）。

**本脚本不下任何物理结论**，只回答"这两臂能不能比"。
"""
from __future__ import annotations

import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')

PAIRS = [('saSet2', 'saSet2F2'), ('saOddG', 'saOddGF2')]

# 这些键**允许**不同（它们就是被比较的自变量 / 记账元数据）
ALLOW_DIFF = {'tag', 'f2_pair_gamma', 'out', 't_wall', 'wall_s', 'started',
              'git', 'sha256', 'argv', 'cmdline', 'run_id', 'host'}


def same_val(a, b):
    """★ 修：**本函数是第一版三个假阳性的根因**，逐条记下来。

    * 假阳性 1：`psi_mean` 两臂都是 `nan` ⇒ `nan != nan` ⇒ 被判"不同"。
      ⇒ 正确判据：**都是 NaN 视为相同**。
    * 假阳性 2：`gamma_RS` 是 **dict**，`repr` 对**键顺序**敏感 ⇒ 顺序不同被判"不同"。
      ⇒ 正确判据：dict **按键比较值**（并比较键集合）。
    * 假阳性 3：`exp_args` 是**整个 argv 的 dict**，λ=1 必然含 `--f2-pair-gamma`
      ⇒ 整体比必然"不同"，但真正的信息在**逐键**里。
      ⇒ 正确做法：**展开逐键比**，并单独点名 `nthreads` 等。
    """
    if isinstance(a, float) and isinstance(b, float) and a != a and b != b:
        return True                                    # 都是 NaN
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(same_val(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same_val(x, y) for x, y in zip(a, b))
    return repr(a) == repr(b)


def flatten(d, prefix=''):
    """把嵌套 dict 展平成 `a.b.c -> 叶子`，好逐键比。"""
    out = {}
    for k, v in d.items():
        key = '%s.%s' % (prefix, k) if prefix else str(k)
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out


def load_meta(tag):
    p = os.path.join(MB, 'dry_' + tag, 'meta.json')
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except (OSError, ValueError) as e:
        print('    ⚠ %s 读失败：%s' % (p, e))
        return None


def load_rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    return list(csv.DictReader(open(p)))


def main():
    print('=' * 112)
    print('_r175 —— R165 前置接线核对（**先问"能不能比"，再读判决**）')
    print('=' * 112)
    bad = 0
    for t0, t1 in PAIRS:
        print()
        print('  ' + '=' * 106)
        print('  ## `dry_%s`(λ=0)  vs  `dry_%s`(λ=1)' % (t0, t1))
        print('  ' + '=' * 106)
        m0, m1 = load_meta(t0), load_meta(t1)
        if m0 is None or m1 is None:
            print('     ⚠ meta 缺失（%s=%s, %s=%s）⇒ 跳过'
                  % (t0, m0 is not None, t1, m1 is not None))
            bad += 1
            continue
        keys = sorted(set(m0) | set(m1))
        f0, f1 = flatten(m0), flatten(m1)
        allk = sorted(set(f0) | set(f1))
        diff = []
        for k in allk:
            a, b = f0.get(k, '<缺>'), f1.get(k, '<缺>')
            if not same_val(a, b):
                diff.append((k, a, b))
        print('     **W-1 单变量性**：meta 共 %d 个键（展平后 %d 个叶子），'
              '**不同的有 %d 个**' % (len(keys), len(allk), len(diff)))
        for (k, a, b) in diff:
            mark = '✔ 应为自变量' if k in ALLOW_DIFF else '⚠ 需解释'
            print('        %-26s %-30s → %-30s %s'
                  % (k, repr(a)[:30], repr(b)[:30], mark))
        unexpected = [d for d in diff if d[0] not in ALLOW_DIFF]
        # ★ 代码 SHA 不同是**预期的**（本轮改过 `_bk_exp.py`/`windowB_lath.py`）；
        #   但它**不能靠 SHA 判定无害** —— 必须另跑「λ=0 惰性复现」来证。
        sha_keys = [d[0] for d in unexpected if d[0].startswith('sha_')]
        real = [d for d in unexpected if not d[0].startswith('sha_')]
        if sha_keys:
            print('     ⇒ ⚠ **代码 SHA 不同**：%s' % ', '.join(sha_keys))
            print('        ⇒ 这是**预期**的（本轮改过 `_bk_exp.py`/`windowB_lath.py`/'
                  '`_bk_measure.py`），但**不能靠 SHA 判无害**：')
            print('        ⇒ **必须另跑「λ=0 + 新代码」与归档 `dry_%s` 逐位对比**'
                  '（见 `_r176_inert.sh`）。' % t0)
        if real:
            bad += 1
            print('     ⇒ ❌ **W-1 有非 SHA 的非预期差异 %d 个**：%s'
                  % (len(real), ', '.join(d[0] for d in real)))
        elif not sha_keys:
            print('     ⇒ ✅ **W-1 通过**：只差 `%s`'
                  % (', '.join(d[0] for d in diff) or '（无差异）'))
        # 关键开关单独点名
        for k in ('facet_proj', 'rank1_swap', 'gamma0', 'laths', 'N', 'dx_nm',
                  'plate_L_nm', 'plate_W_nm', 'plate_T_nm', 'block_gap_nm',
                  'el_scale', 'steps', 'seed', 'omega_max_deg', 'omega_mode'):
            if k in keys:
                a, b = m0.get(k, '<缺>'), m1.get(k, '<缺>')
                flag = '' if repr(a) == repr(b) else '   ← **不同**'
                print('        %-16s λ=0: %-22s λ=1: %-22s%s'
                      % (k, repr(a)[:22], repr(b)[:22], flag))

        # ---- W-2 初态一致性 ----
        print()
        r0, r1 = load_rows(t0), load_rows(t1)
        if not r0 or not r1:
            print('     ⚠ series.csv 缺失 ⇒ 跳过 W-2')
            continue
        print('     **W-3 进度**：λ=0 末步 %s（%d 行）；λ=1 末步 %s（%d 行）'
              % (r0[-1].get('step'), len(r0), r1[-1].get('step'), len(r1)))
        h0, h1 = r0[0], r1[0]
        print('     **W-2 初态（第 1 行，step=%s / %s）**' % (h0.get('step'), h1.get('step')))
        cols = [c for c in ('Vt', 'nf2', 'nf3col', 'nslab_sig', 'f3_area_m2',
                            'f2_area_m2', 'r_selfac', 'box_touch_core', 'psi_mean')
                if c in h0 and c in h1]
        nd = 0
        for c in cols:
            a, b = h0.get(c), h1.get(c)
            try:
                fa, fb = float(a), float(b)
                if fa != fa and fb != fb:
                    same = True                        # 都是 NaN（修假阳性 1）
                else:
                    same = (abs(fa - fb) <= 1e-12 * max(1.0, abs(fa)))
            except (TypeError, ValueError):
                same = (a == b)
            nd += (not same)
            print('        %-15s λ=0: %-22s λ=1: %-22s %s'
                  % (c, a, b, '' if same else '❌ **不同**'))
        if nd:
            bad += 1
            print('     ⇒ ❌ **W-2 不通过**：初态有 %d 个量不同 ⇒ '
                  '**末态差异不能归因于 λ**' % nd)
        else:
            print('     ⇒ ✅ **W-2 通过**：可比列在 t=0 逐位一致')
        # nf2(t=0) 必须为 0（G-3 的一半）
        try:
            nf2_0 = float(h0.get('nf2', 'nan'))
            print('     **G-3a** `nf2(t=0)` = %s ⇒ %s'
                  % (nf2_0, '✅' if nf2_0 == 0 else '❌ 应为 0'))
            if nf2_0 != 0:
                bad += 1
        except (TypeError, ValueError):
            pass
    print()
    print('=' * 112)
    print('  ## 总判定')
    print('=' * 112)
    print('     **不能比的对数 = %d / %d**' % (bad, len(PAIRS)))
    if bad == 0:
        print('     ⇒ ✅ 两对都**可以**作单变量对照 ⇒ 可以读 `_r171` 的判决。')
    else:
        print('     ⇒ ❌ **不得**直接读判决；先修对照设计（见上）。')
    print()
    print('  ⚠ 本脚本**不下物理结论**，只回答"这两臂能不能比"。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
