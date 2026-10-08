#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r741_T2retry.py —— **按 `R741` 的更正值实测 `nf2 > 0`**（纯 CLI，零主代码改动）。

## 为什么重做（`R741` 的更正）
我在 `R732`/`R739`/`R740` 用的盒子是 `--plate-L/W/T 125`。
`R741` 的全盘比率检验：**`plate_{L,W,T}=125` 的 77 个臂，`nf2 > 0` 的比例 = 0.0%**
（而 `plate_W=600` ⇒ 87.5%、`plate_L=800` ⇒ 66.7%）。
⇒ **125 nm 盒在结构上看不到 F2 界面** ⇒ 我先前"F2 够不着"是**小盒假象**。

## 本设计的口径（逐项对齐 `R741 §2` 的**促进**档）
| 参数 | `R741` 的促进档 | 本实验取值 | 依据 |
|---|---|---|---|
| `plate_L/W/T` | 800 / 600 / 635 | **700 / 700 / 350**（nm） | 125 与 250 都是 `P=0` ⇒ 必须显著更大；取 700 兼顾内存 |
| `N` | 112 | **112** | `P=62.2%`（vs `N=64` 的 8.9%） |
| `dx` | — | **6.25 nm** | `700/112` |
| `steps` | 4000 / ≥250 | **200** | 125 nm 盒的失败区在 ≤100 步；200 步是折中（内存/机时） |
| `facet_proj` | 10 | **0** | ⚠ **有意不用** —— 它是"几何硬掰"（`R707`/`R734`），本实验要测**物理路径** |
| `grow_stack` | False (48.4%) | **不加 `--grow-stack`** | 走 `attach` |
| `laths` | 多值档 | **`1,1,2,2,3,3,4,4,5,5,6,6`**（M=12、6 变体） | 与 `R725` 第 3 轮同 |

## 内存预算（`R736` 的 `M-0`，**先算再跑**）
`R736` 实测：`N=96` + 6 µm 盒 + 6 场 ⇒ 峰值 **4.8 GB**。
`N=112` ⇒ `(112/96)³ = 1.59×` ⇒ **外推 ≈ 7.6 GB** < 12 GB 限 ✅。
**watchdog 仍在，超 12 GB 即中止。**

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **V-1（主）** | **`nf2 ≥ 1`**（F2 界面出现） | ≥1 |
| **V-2** | 独有可核查串（`P43`）：`n_var_sig ≥ 2` **且** `blk_laths` 有 ≥2 个非零项 | — |
| **V-3** | `box_touch = 0` 的步数 ≥ 3（否则窗口不足） | ≥3 |
| **V-4** | 峰值 RSS < 12 GB | — |

⚠ **本实验不用 `--nuc-iface-nucleation`**（`R741` 证明它与 `nf2 > 0` 无因果：
其 OFF 档有 134 个臂、pos=1）。

## 用法
    python3 _r741_T2retry.py --dry
    python3 _r741_T2retry.py
"""
import os
import subprocess
import sys
import threading
import time

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_t2big'
RSS_LIMIT_MB = 12000

BASE = [
    '--N', '112', '--dx-nm', '6.25', '--steps', '200',
    '--every', '25', '--snap-every', '25', '--pair-every', '25',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
    '--laths', '1,1,2,2,3,3,4,4,5,5,6,6',
    '--plate-L', '700.0', '--plate-W', '700.0', '--plate-T', '350.0',
    '--nuc-shape', 'disc',
    '--nuc-every', '0', '--nuc-init', '6',
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
TAG = 'big700'


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
            print('    [watchdog] RSS = %d MB' % m, flush=True)
            if m > RSS_LIMIT_MB:
                print('    ⛔ [watchdog] 超内存 ⇒ 中止', flush=True)
                for p in pids:
                    subprocess.run(['kill', '-9', p])
        stop.wait(25)


def main():
    dry = '--dry' in sys.argv
    cmd = [PY, '-u', '_bk_exp.py'] + BASE + ['--tag', TAG]
    print('=== %s ===' % TAG, flush=True)
    if dry:
        print(' '.join(cmd))
        return 0
    stop = threading.Event()
    threading.Thread(target=watchdog, args=(stop,), daemon=True).start()
    r = subprocess.run(['nice', '-n', '10', 'taskset', '-c', '0-3'] + cmd, cwd=FW)
    stop.set()
    print('    rc=%d' % r.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
