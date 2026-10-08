#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r733_longab.py —— **F-1 的更长 A/B**（`N=128`、6 µm 盒、300 步）。

## 为什么要再来一轮（`R730 §4` 的待办 1）
`R730` 的 A/B 只跑到 **step 100**，因为 `N=96` 的 `q0` 类配置 **@225 就撞盒**
（`R720 §1` 实测）⇒ **`J-8`（长厚比趋势）与 `J-10`（同 `Vt` 配对）都判不了**。
⇒ 本轮**加密网格**（`N=128` ⇒ `dx = 6 µm/128 = 46.9 nm`）来换**更长的安全轨迹**：
板条长到撞盒需要更多步（`dx` 更小 ⇒ 每步位移更小）。

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **J-8b** | 两臂在**各自 `box_touch=0` 的公共最长步**上比 PCA（长厚比） | 开 > 关（方向；单种子不报显著） |
| **J-5b** | `β_h^eff` 兑现率：**多个步的中位** | ≥ 0.98（`R727 §3.2` 原靶） |
| **J-9b** | `f_flat` **不劣化**（同安全步） | ≥ 基线 |
| **J-10b** | 同 `Vt` 的步数比 | ∈ [0.8, 1.25] |
| **J-11（新）** | **开关生效性**：两臂至少在**一个**可观测标量上不同 | 必须不同 |

⚠ 记账：`N=128` ⇒ 单步更贵（预估 8–14 s/步）；300 步 ⇒ **单臂 40–70 min**。
纪律 `R630`：4 核 + `nice 10` + 核段 0–3。

## 用法
    python3 _r733_longab.py --dry
    python3 _r733_longab.py
"""
import os
import subprocess
import sys

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq_long'

BASE = [
    '--N', '128', '--dx-nm', '46.875', '--steps', '300',
    '--every', '25', '--snap-every', '25', '--pair-every', '100',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
    '--laths', '1,1,1,1,1,1',
    '--plate-L', '125.0', '--plate-W', '125.0', '--plate-T', '125.0',
    '--nuc-shape', 'disc', '--grow-stack', '--nuc-every', '0', '--nuc-init', '0',
    '--nuc-law', 'cadence', '--nuc-block-target', '0',
    '--nuc-mode', 'auto', '--eng-cadence', '30',
    '--gamma0', '0.25', '--gamma-film', '0.6', '--alpha-km', '0.041739',
    '--T-end', '298.0', '--cool-rate', '2352400.0',
    '--qs-clock', '1', '--qs-max-relax', '100',
    '--beta-h', '6.477', '--beta-w', '2.3', '--ed-eta', '0.253',
    '--mob-iform', 'exp2', '--mob-ratio', '9.0', '--mob-dip', '4.0',
    '--facet-proj', '0', '--rank1-swap', 'none', '--var-rule', 'ed',
    '--nuc-sites-refill', '1', '--band-cells', '40', '--mob-wulff',
    '--out', OUT,
]


def main():
    dry = '--dry' in sys.argv
    for tag, env in (('L_off', {}), ('L_on', {'NDIR_LSQ': '1'})):
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + ['--tag', tag]
        print('=== %s  (NDIR_LSQ=%s) ===' % (tag, env.get('NDIR_LSQ', 'unset')))
        if dry:
            print(' '.join(cmd))
            continue
        e = dict(os.environ)
        e.pop('NDIR_LSQ', None)
        e.update(env)
        r = subprocess.run(['nice', '-n', '10', 'taskset', '-c', '0-3'] + cmd,
                           cwd=FW, env=e)
        print('    rc=%d' % r.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
