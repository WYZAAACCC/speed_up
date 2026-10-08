#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r722_s4_omega.py —— **S4-A：F10 的受控 A/B**（`--omega-mode`，2×2）。

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **F10-1**（静态） | `perstep` 下**相邻同变体对**的 F3 面能**不随 M 变**（跨度比 = 1） | 已由 `_r182_omega_check.py` P-2 实测 **1.000000000000** ✅ |
| **F10-2**（动力学） | 四臂在同一步比较 `f3_area` / `nf3_col`，看 `perstep` 是否**削弱 M 依赖** | 只报读数；**不预设方向** |
| **F10-3**（正对照） | 四臂 `nslab_n ≥ 2`（否则"块内界面"不存在，判据不适用） | ≥2 |
| **F10-4**（惰性） | `--omega-mode` 默认 `ladder` ⇒ 归档路径逐位不变 | 已由 `_r182` P-6 实测 ✅ |

## 单变量性
四臂**只差 `--laths` 与 `--omega-mode`**；其余 argv 逐条等于 `B2P_q0`
（`--facet-proj 0` ⇒ **与投影解耦**）。
⚠ 记账：`--laths` 同时决定"场数上限"与"名义堆叠跨度"⇒ `M` 不是干净单变量
（`R709 §5.3` 已登记）；本实验的目的是**F10 的模式对比**，不是"M 的因果"。

## 安全步
`R720 §1` 实测：`CLIbig` @100 / `Mlo3` @150 / `q0` @225 撞盒
⇒ 本实验**只跑 100 步**，并在 `box_touch=0` 的区间内取值。

## 用法
    python3 _r722_s4_omega.py            # 跑四臂（每臂 ~4 核，nice 10）
    python3 _r722_s4_omega.py --dry      # 只打印 argv
"""
import os
import subprocess
import sys

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_s4omega'
STEPS = '100'

BASE = [
    '--N', '96', '--dx-nm', '62.5', '--steps', STEPS,
    '--every', '25', '--snap-every', '25', '--pair-every', '25',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
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
    '--nuc-sites-refill', '1',
    '--band-cells', '40', '--mob-wulff',
    '--out', OUT,
]

ARMS = [
    ('om_lad_M3',  '1,1,1', 'ladder'),
    ('om_lad_M12', ','.join(['1'] * 12), 'ladder'),
    ('om_pst_M3',  '1,1,1', 'perstep'),
    ('om_pst_M12', ','.join(['1'] * 12), 'perstep'),
]


def main():
    dry = '--dry' in sys.argv
    for tag, laths, mode in ARMS:
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + [
            '--laths', laths, '--omega-mode', mode, '--tag', tag]
        print('=== %s  (M=%d, omega-mode=%s) ===' % (tag, laths.count(',') + 1, mode))
        print(' '.join(cmd))
        if dry:
            continue
        env = dict(os.environ)
        r = subprocess.run(['nice', '-n', '10', 'taskset', '-c', '0-3'] + cmd,
                           cwd=FW, env=env)
        print('    rc=%d' % r.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
