#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r739_T2_stackedg.py —— **T2/F11 前置的纯 CLI 实验**：`--stack-pick-dg` 能否造出 F2 界面。

## ★ 为什么这个脚本会存在（**重要发现**）
我在 `R732` 里设计了一个"最小改动"（把 `fresh` 的源场从全局随机改成按 (S1) 局部记分选），
并判定它**需要改主代码**。
**⇒ 那个设计是在重造一个已经存在的开关。** `windowB_surface.py:2428`：

> `if c.get('stack_pick_dg', False) and not hardened:` … **只把新片接到"外侧面平均 `dG` 最大"的那个块上**

`_bk_exp.py:4457`：
```
--stack-pick-dg  0=均匀随机（归档）；1=接到"外侧面平均 dG 最大"的块（§200 接线修复）
```
⇒ **它就是 `§5.4` 的 (S1) 记分式（`w=(1,0,0)`），已接线、默认关。**

## 因此本实验**零主代码改动**（纯 CLI），却直击 `R725` 的阻塞点
`R725` 实测：生产机制下 **`n_var_sig=3` 但 `nf2 = 0`** ⇒ F2 通道**没有作用对象**。
本实验问：**打开 `--stack-pick-dg` 后，`nf2` 会不会 > 0？**

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **T2-0** | **正对照**：`--stack-pick-dg 0` 臂复现 `R725` 的症状 | `nf2 == 0` |
| **T2-1** | `--stack-pick-dg 1` 臂出现 **`nf2 ≥ 1`** | ≥1 |
| **T2-2** | 两臂**只差这一个开关** | argv diff = 1 项 |
| **T2-3** | 两臂 `box_touch = 0`（`R720 §1`） | =0 |
| **T2-4** | 内存 < 12 GB（`R736` 的 `M-0`） | — |

## 配置（对齐 `R725` 第 3 轮 + 内存安全）
`N=96`（**不是 `N=128`** —— `R736` 的教训）、6 µm、**100 步**、
`--laths 1,1,2,2,3,3,4,4,5,5,6,6`（M=12、6 变体）、**`--nuc-init 6`**（开 `fresh` 通道）、
`--facet-proj 0`、其余等于生产。

## 用法
    python3 _r739_T2_stackedg.py --dry
    python3 _r739_T2_stackedg.py
"""
import os
import subprocess
import sys
import threading
import time

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_t2stackdg'
RSS_LIMIT_MB = 12000

BASE = [
    '--N', '96', '--dx-nm', '62.5', '--steps', '100',
    '--every', '25', '--snap-every', '25', '--pair-every', '25',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
    '--laths', '1,1,2,2,3,3,4,4,5,5,6,6',
    '--plate-L', '125.0', '--plate-W', '125.0', '--plate-T', '125.0',
    '--nuc-shape', 'disc', '--grow-stack', '--nuc-every', '0',
    '--nuc-init', '6',                    # ★ 开 fresh 通道（R725 的教训）
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
        if pids and rss_mb(pids) > RSS_LIMIT_MB:
            print('    ⛔ [watchdog] 超内存 ⇒ 中止', flush=True)
            for p in pids:
                subprocess.run(['kill', '-9', p])
        stop.wait(20)


def main():
    dry = '--dry' in sys.argv
    for tag, sdg in (('dgr0', '0'), ('dgr1', '1')):
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + [
            '--stack-pick-dg', sdg, '--tag', tag]
        print('=== %s (--stack-pick-dg %s) ===' % (tag, sdg), flush=True)
        if dry:
            print(' '.join(cmd))
            continue
        stop = threading.Event()
        threading.Thread(target=watchdog, args=(stop,), daemon=True).start()
        r = subprocess.run(['nice', '-n', '10', 'taskset', '-c', '0-3'] + cmd, cwd=FW)
        stop.set()
        time.sleep(1)
        print('    rc=%d' % r.returncode, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
