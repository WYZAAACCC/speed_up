#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r725_s4b_f2.py —— **S4-B：F11（`--f2-pair-gamma`）的敏感性研究**。

## 为什么是"敏感性研究"而不是"A/B 两档"
`R712 §10.2` 的 S4 写的是"`--f2-pair-gamma > 0` 单变量 A/B"。但**填哪个数没有依据**。
按 `R712 §0.3` 的 **E2 教训**（"判据里挂了我拍的 `ΔT_win = 100 K`" = 引入无依据参数），
**本脚本不拍一个数，而是扫 λ 并报结果如何随 λ 变**。

★ **λ 不是外来参数**：`windowB_lath.py:277-289` 逐字说明它的依据**来自模型自身**：
```
γ_F2(v,w) = γ₀·[(1−λ) + λ·min(1, ‖Δε(v,w)‖_F / Δε_ref)]
```
其中 `Δε = ε_v − ε_w` 是**两变体的相变应变失配**（模型自带量），
`Δε_ref` 取实测尺度。⇒ **λ 是"这条通道开多大"的开关，不是材料常数**。

## 配置选择（关键）
⚠ **必须用异变体配置**：`M=6` 全为变体 1 时，**异变体对 = 0** ⇒ F2 通道**无作用**。
⇒ 本脚本用 **`--laths 1,1,2,2,3,3`（3 个变体 × 2 块）**，
   这样 F2（异变体）对存在，λ 才有可观测效果。

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **F11-1** | `λ=0` 与归档 `ladder` 等价路径**逐位相同**（路径不变性） | 逐位 |
| **F11-2** | λ 增大 ⇒ **块数 / `nf2`（异变体界面数）/ F2 面积** 出现**可辨**变化 | 只报读数，**不预设方向** |
| **F11-3** | 四臂 `box_touch = 0`（`R720 §1`：否则不可比） | =0 |

## 用法
    python3 _r725_s4b_f2.py --dry
    python3 _r725_s4b_f2.py
"""
import os
import subprocess
import sys

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_s4f2'

BASE = [
    '--N', '96', '--dx-nm', '62.5', '--steps', '100',
    '--every', '25', '--snap-every', '99999', '--pair-every', '25',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
    '--laths', '1,1,2,2,3,3',                  # ★ 异变体 ⇒ F2 通道存在
    '--plate-L', '125.0', '--plate-W', '125.0', '--plate-T', '125.0',
    '--nuc-shape', 'disc', '--grow-stack',
    '--nuc-every', '0', '--nuc-init', '0',
    '--nuc-law', 'cadence', '--nuc-block-target', '0',
    '--nuc-mode', 'auto', '--eng-cadence', '30',
    '--gamma0', '0.25', '--gamma-film', '0.6',
    '--alpha-km', '0.041739', '--T-end', '298.0', '--cool-rate', '2352400.0',
    '--qs-clock', '1', '--qs-max-relax', '100',
    '--beta-h', '6.477', '--beta-w', '2.3', '--ed-eta', '0.253',
    '--mob-iform', 'exp2', '--mob-ratio', '9.0', '--mob-dip', '4.0',
    '--facet-proj', '0', '--rank1-swap', 'none', '--var-rule', 'ed',
    '--nuc-sites-refill', '1', '--band-cells', '40', '--mob-wulff',
    '--out', OUT,
]

ARMS = [
    ('f2_lam0',  '0.0'),
    ('f2_lam25', '0.25'),
    ('f2_lam50', '0.5'),
    ('f2_lam75', '0.75'),
    ('f2_lam100', '1.0'),
]


def main():
    dry = '--dry' in sys.argv
    for tag, lam in ARMS:
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + [
            '--f2-pair-gamma', lam, '--tag', tag]
        print('=== %s  (--f2-pair-gamma %s) ===' % (tag, lam))
        if dry:
            print(' '.join(cmd))
            continue
        r = subprocess.run(['nice', '-n', '10', 'taskset', '-c', '0-3'] + cmd,
                           cwd=FW)
        print('    rc=%d' % r.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
