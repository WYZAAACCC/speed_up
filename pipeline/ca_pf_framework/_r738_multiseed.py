#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r738_multiseed.py —— **F-1 的多种子 A/B**（按 `R737 §5` 的三条要求重设计）。

## 为什么重设计（`R737` 的结论）
`R737` 判定：宏观形状层 **`[无法判定]`**，因为
1. **单种子** ⇒ 两臂的**形核/合并事件不同** ⇒ 场集合不同；
2. `J-8b` 用的 **`PCA-max` 口径最不稳定**（step 125 它 +119%，其余三口径 −10~−29%）。

## 本设计（**逐条对应**）
| `R737 §5` 的要求 | 本脚本怎么做 |
|---|---|
| **1. 多种子** | **3 个 `--eng-seed`**（11 / 23 / 37）× 2 臂 = **6 次运行** |
| **2. 限制到单场阶段** | **`--eng-cadence 200`**（> 总步数 100）⇒ **首次形核被推到测量窗外** ⇒ **全程只有播下的那 1 个场** |
| **3. 换轨迹/鲁棒指标** | 主判据改 **`f_tip`**（端面胞占比，**直接量**，不是"取最大"）；辅判据用 **`PCA-D`**（全体胞并起来算一次） |

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **K-1（主）** | `f_tip`：两臂 × 3 种子的**中位**，开 > 关，且 **3/3 种子同向** | 同向 |
| **K-2（辅）** | `PCA-D`（全体胞）同向，且 **≥2/3 种子同向** | — |
| **K-3** | **全程 `nslab` 恒为 1**（证明单场阶段成立） | ==1 |
| **K-4** | `β_h^eff` 同向 | — |
| **K-5** | 内存 < 12 GB（watchdog 实测） | — |
| **K-6** | `--eng-seed` **真的改变**结果（否则"多种子"是空操作） | 3 个种子的关臂读数**不全同** |

⚠ 记账：`--eng-cadence 200` 与生产（30）**不同** ⇒ 本实验**不是**生产配置，
但**两臂共用同一配置** ⇒ 对比仍有效（单变量：只切 `NDIR_LSQ`）。

## 用法
    python3 _r738_multiseed.py --dry
    python3 _r738_multiseed.py
"""
import os
import subprocess
import sys
import threading
import time

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq_seed'
RSS_LIMIT_MB = 12000
SEEDS = [11, 23, 37]

BASE = [
    '--N', '96', '--dx-nm', '62.5', '--steps', '100',
    '--every', '25', '--snap-every', '25', '--pair-every', '25',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
    '--laths', '1,1,1,1,1,1',
    '--plate-L', '125.0', '--plate-W', '125.0', '--plate-T', '125.0',
    '--nuc-shape', 'disc', '--grow-stack', '--nuc-every', '0', '--nuc-init', '0',
    '--nuc-law', 'cadence', '--nuc-block-target', '0',
    '--nuc-mode', 'auto',
    '--eng-cadence', '200',          # ★ 把首次形核推到测量窗外 ⇒ 单场阶段
    '--gamma0', '0.25', '--gamma-film', '0.6', '--alpha-km', '0.041739',
    '--T-end', '298.0', '--cool-rate', '2352400.0',
    '--qs-clock', '1', '--qs-max-relax', '100',
    '--beta-h', '6.477', '--beta-w', '2.3', '--ed-eta', '0.253',
    '--mob-iform', 'exp2', '--mob-ratio', '9.0', '--mob-dip', '4.0',
    '--facet-proj', '0', '--rank1-swap', 'none', '--var-rule', 'ed',
    '--nuc-sites-refill', '1', '--band-cells', '40', '--mob-wulff',
    '--out', OUT,
]


def rss_mb(pids):
    tot = 0
    for p in pids:
        try:
            with open('/proc/%s/status' % p) as f:
                for ln in f:
                    if ln.startswith('VmRSS:'):
                        tot += int(ln.split()[1]) // 1024
        except OSError:
            pass
    return tot


def watchdog(stop):
    while not stop.is_set():
        pids = subprocess.run(['pgrep', '-f', '[_]bk_exp.py'],
                              capture_output=True, text=True).stdout.split()
        if pids:
            m = rss_mb(pids)
            if m > RSS_LIMIT_MB:
                print('    ⛔ [watchdog] RSS=%d MB 超限 ⇒ 中止' % m, flush=True)
                for p in pids:
                    subprocess.run(['kill', '-9', p])
        stop.wait(20)


def main():
    dry = '--dry' in sys.argv
    print('★ 多种子 A/B：seeds=%s，2 臂 × 3 种子 = %d 次运行' % (SEEDS, 2 * len(SEEDS)))
    print('★ K-3：`--eng-cadence 200` ⇒ 首次形核在 100 步之外 ⇒ 应全程 `nslab=1`')
    jobs = []
    for sd in SEEDS:
        for arm, env in (('off', {}), ('on', {'NDIR_LSQ': '1'})):
            jobs.append(('sd%d_%s' % (sd, arm), sd, env))
    for tag, sd, env in jobs:
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + [
            '--eng-seed', str(sd), '--tag', tag]
        print('=== %s (eng-seed=%d, NDIR_LSQ=%s) ==='
              % (tag, sd, env.get('NDIR_LSQ', 'unset')), flush=True)
        if dry:
            print(' '.join(cmd))
            continue
        e = dict(os.environ)
        e.pop('NDIR_LSQ', None)
        e.update(env)
        stop = threading.Event()
        th = threading.Thread(target=watchdog, args=(stop,), daemon=True)
        th.start()
        r = subprocess.run(['nice', '-n', '10', 'taskset', '-c', '0-3'] + cmd,
                           cwd=FW, env=e)
        stop.set()
        time.sleep(1)
        print('    rc=%d' % r.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
