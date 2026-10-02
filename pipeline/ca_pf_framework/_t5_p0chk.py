#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_p0chk.py --- 第 8 条：**实测** `P0`（F3 位置基准）是否在检查点里

## 为什么必须实测（不能靠键名推断 —— 本仓库 P28）
`f3_pos_dx = (pm − P0)/dx`。若 `P0` **不在**检查点里，续跑后它只能**重算**
⇒ 重算值与原值不同就是**结构性**差异（不是 bug，但会让该列不可比）。
**⚠ 我第一遍只看了 44 个键里的前 12 个就写下"未见 P0 字样" —— 那是**推断**。
本脚本把**全部键**打出来，并**按值搜**（不只按键名）。**
"""
import glob
import os
import sys

import numpy as np

CKS = sys.argv[1:] or ['_exp/_bk_t5/dry_ck8A/ckpt',
                       '_exp/_bk_t5/dry_t5H3/ckpt']
print('=' * 96)
print('第 8 条：`P0`（F3 位置基准）是否在检查点里 —— **实测**')
print('=' * 96)
for d in CKS:
    fs = sorted(glob.glob(os.path.join(d, '*.npz')))
    if not fs:
        print('  %-38s ⚠ 无检查点' % d)
        continue
    f = fs[0]
    print()
    print('  ── %s（%d 帧，取第 1 帧 %.1f MB）──'
          % (d, len(fs), os.path.getsize(f) / 1048576))
    with np.load(f, allow_pickle=False) as z:
        ks = sorted(z.files)
        print('     **全部 %d 个键**：' % len(ks))
        for i in range(0, len(ks), 5):
            print('        %s' % ks[i:i + 5])
        # ── ① 按**键名**搜（大小写、常见前缀都试）──
        name_hits = [k for k in ks
                     if any(t in k.lower() for t in ('p0', 'pos0', 'f3pos', 'f3_pos', 'base'))]
        # ── ② 按**值**搜：F3 基准是个标量（米）⇒ 找 0~1e-5 量级的标量 ──
        val_hits = []
        for k in ks:
            a = np.asarray(z[k])
            if a.ndim == 0 and a.dtype.kind == 'f':
                v = float(a)
                if 0.0 < abs(v) < 1.0e-4:
                    val_hits.append((k, v))
        print()
        print('     ★ ① **按名**搜（p0/pos0/f3pos/f3_pos/base）⇒ %s'
              % (name_hits or '**空**'))
        print('     ★ ② **按值**搜（0 < |v| < 1e-4 的**标量**）⇒ %d 个'
              % len(val_hits))
        for k, v in val_hits[:12]:
            print('          %-26s = %.10g' % (k, v))
    print()
    print('     ⇒ 判定：若 ① 与 ② 都空 ⇒ **`P0` 不在检查点里**（结构性）⇒')
    print('        续跑后它只能**重算** ⇒ `f3_pos_dx` 列**不可比***（不是 bug，是口径）')
    print('     ⇒ 若 ② 里有候选 ⇒ **必须逐个核对它是不是 F3 基准**（不得凭量级断定）')
print('=' * 96)
