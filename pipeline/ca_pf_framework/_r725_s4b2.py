#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r725_s4b2.py —— **S4-B 更正版**：先让**异变体界面真的出现**，再扫 λ。

## 上一版（`_r725_s4b_f2.py`）为什么无效应（**我的设计错**）
五臂**103 列逐位相同** ⇒ 先查症状：`nslab_n=2`、**`n_var_sig=1`**、`nf2=0`
⇒ 尽管传了 `--laths 1,1,2,2,3,3`，**step 100 时在场的是同一个变体的 2 个场**。
⇒ **F2（异变体对）根本没有对象** ⇒ λ 无效应是**必然**，不是发现。

## 本版改什么（**单变量：只改 `--nuc-init`** —— 前两版都错在这里）
`_bk_exp.py:4412-4414` 逐字：
> `--var-rule` = 新核的**变体选择规则**：ed（按弹性能，默认）/ random / doublet
> **`fresh`（独立形核）通道需要待机位点**；位点由引擎在 t=0 随机撒下（`_nuc_place_initial`）。
> `>0` 才会走 `fresh` 通道，而**只有 `fresh` 通道才按 `--var-rule` 选变体**
> （**`stack` 是"同变体、新场"**）。

⇒ **前两版都传了 `--nuc-init 0`** ⇒ `fresh` 通道**没开** ⇒ 全部事件走 `stack`/`attach`
（**同变体**）⇒ **异变体界面永远不出现** ⇒ λ 无效应是**必然**（实测 `n_var_sig=1`、`nf2=0`）。
⇒ **本版唯一改动：`--nuc-init 6`**（撒 6 个待机位点 ⇒ 走 `fresh` ⇒ 按 `--var-rule` 选变体）。

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **F11-0**（**前置条件**，`P43`） | 必须在场 **≥2 个不同变体**（`n_var_sig ≥ 2`）**且** `nf2 ≥ 1` | 满足才继续 |
| **F11-2** | λ 增大 ⇒ 块数 / `nf2` / F2 面积出现**可辨**变化 | 只报读数，**不预设方向** |
| **F11-3** | 各臂 `box_touch = 0`（`R720 §1`） | =0 |
| **F11-4** | 相对前两版**只改 `--nuc-init`** | 逐条 argv diff |

## 用法
    python3 _r725_s4b2.py --dry
    python3 _r725_s4b2.py
"""
import os
import subprocess
import sys

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_s4f2b'

BASE = [
    '--N', '96', '--dx-nm', '62.5', '--steps', '100',
    '--every', '25', '--snap-every', '99999', '--pair-every', '25',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
    '--laths', '1,1,2,2,3,3,4,4,5,5,6,6',        # ★ M=12，6 个变体
    '--plate-L', '125.0', '--plate-W', '125.0', '--plate-T', '125.0',
    '--nuc-shape', 'disc', '--grow-stack',
    '--nuc-every', '0',
    '--nuc-init', '6',                            # ★★ 本版唯一改动
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

ARMS = [('c_lam0', '0.0'), ('c_lam50', '0.5'), ('c_lam100', '1.0')]


def main():
    dry = '--dry' in sys.argv
    print('★ 本版唯一改动：`--nuc-init 0 → 6`（开 `fresh` 通道）'
          '＋ `--laths 1,1,2,2,3,3,4,4,5,5,6,6`（6 变体）；`--var-rule ed`（生产默认）')
    for tag, lam in ARMS:
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + [
            '--f2-pair-gamma', lam, '--tag', tag]
        print('=== %s  (λ=%s) ===' % (tag, lam))
        if dry:
            print(' '.join(cmd))
            continue
        r = subprocess.run(['nice', '-n', '10', 'taskset', '-c', '0-3'] + cmd, cwd=FW)
        print('    rc=%d' % r.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
