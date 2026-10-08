#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r740_T2_iface.py —— **T2/F11 前置**：`--nuc-iface-nucleation` 能否造出 F2 界面（**纯 CLI**）。

## ★★ 本轮的发现（把 `R739` 的债还了）
`R739` 查到 `stack` 通道一次没触发（`n_events_by_mode={'fresh':3}`、`pending_fresh=4`）。
顺着 `nuc_dbg.json` 的**全部键**往下挖，找到 `nuc_cfg.nuc_iface_nucleation = False`。
它的 CLI 定义（`_bk_exp.py:4630`）逐字：
```
--nuc-iface-nucleation  ★ R623 G2：允许在**已有板条的界面**上形核（异变体），
                        对应 R-A/R-B 的第 2/3 波；默认 0 = 只许落母相（归档）
```
实现（`windowB_surface.py:2786-2801`）逐条：
* **(a) 几何**：覆盖区 = 母相 ∪ **恰好一个**已转变场（= "**贴着某一根已有板条**"）；
* **(b) 取向**：新场变体必须**不同于** `ksrc` 的变体 ⇒ **这才是"异变体界面形核"**。

⇒ **这正是 `R712 §4.7` 的 edge-to-edge 形核，而且它是既有开关、默认关、已接线。**
⇒ **T2 不需要改主代码**（这条结论在 `R732`/`R739` 之间反复过 —— 现在是**有证据的**版本）。

## ⚠ 关键前置：本开关**只在 `stack` 路径上生效**（`windowB_surface.py:2798` ⊂ stack 分支）
`R739` 的失败正是因为 `pending_fresh=4` ⇒ `fresh` 优先 ⇒ `stack` 从不触发。
⇒ **本实验必须 `--nuc-init 0`**（关掉 `fresh` 位点）⇒ 逼出 `stack` 通道。
★ 这也解释 `R725` 第 1/2 轮（`--nuc-init 0`）为什么 `n_var_sig=1`：
   当时 `nuc_iface_nucleation` 是默认 0 ⇒ **新场只能是同变体** ⇒ 变体数当然是 1。

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **U-0** | **通道确证**：两臂都出现 **`stack ≥ 1`** 事件（`n_events_by_mode`） | ≥1 |
| **U-1（主）** | `--nuc-iface-nucleation 1` 臂出现 **`nf2 ≥ 1`** | ≥1 |
| **U-2（正对照）** | 默认臂（`0`）**`nf2` 恒为 0** | ==0 |
| **U-3** | 默认臂相对归档**逐位不变**的间接证据：`n_var_sig` 不因开开关而假性升高 | — |
| **U-4** | 两臂只差**这一个开关** | argv diff = 1 |
| **U-5** | 内存 < 12 GB（`R736` 的 `M-0`） | — |

## 配置（对齐 `R725` 第 3 轮 + 安全窗口）
`N=96`、6 µm、**50 步**（本类配置撞盒早 —— `R739` 实测 step 75 撞，
`--nuc-init 0` 下 `R725` 第 1/2 轮更早）⇒ **只跑到 50**，`--every 25 --snap-every 25`、
`--laths 1,1,2,2,3,3,4,4,5,5,6,6`（M=12、6 变体）、**`--nuc-init 0`**、
`--facet-proj 0`、其余等于生产。

## 用法
    python3 _r740_T2_iface.py --dry
    python3 _r740_T2_iface.py
"""
import os
import subprocess
import sys
import threading
import time

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_t2iface'
RSS_LIMIT_MB = 12000

BASE = [
    '--N', '96', '--dx-nm', '62.5', '--steps', '50',
    '--every', '25', '--snap-every', '25', '--pair-every', '25',
    '--norm-smooth', '0', '--nthreads', '4', '--arm', 'dry',
    '--laths', '1,1,2,2,3,3,4,4,5,5,6,6',
    '--plate-L', '125.0', '--plate-W', '125.0', '--plate-T', '125.0',
    '--nuc-shape', 'disc', '--grow-stack', '--nuc-every', '0',
    '--nuc-init', '0',                 # ★ 关 fresh ⇒ 逼出 stack 通道（R739 的教训）
    '--nuc-law', 'cadence', '--nuc-block-target', '0',
    '--nuc-mode', 'auto', '--eng-cadence', '15',
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
    for tag, val in (('ifn0', '0'), ('ifn1', '1')):
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + [
            '--nuc-iface-nucleation', val, '--tag', tag]
        print('=== %s (--nuc-iface-nucleation %s) ===' % (tag, val), flush=True)
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
