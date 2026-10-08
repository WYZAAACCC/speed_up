#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r742_f2ab.py —— ★★ **第一次真正跑成功的 `γ_F2` A/B**（λ = 0 / 0.5 / 1）。

## 为什么这是"第一次"
`_t11_f2_ab.py` **设计过**同样的 A/B（2026-10-05），但：
* 它用 `--laths 1×70`（**全部同变体**）⇒ **`nf2 ≡ 0`** ⇒ `γ_F2` 无作用对象；
* 而且归档里 **只有 `f2L0` 有 `series.csv`，`f2L05`/`f2L1` 连结果都没有**（`_r742_check_f2ab.py` 实测）。
⇒ **该 A/B 从未真正跑成功。**

`R741` 更正了根因（小盒假象）⇒ 本脚本用**已验证能产出 `nf2 ~ 3×10⁴`** 的配置
（`_r741_T2retry.py` 的 `big700`）**加上 λ 这个单变量**。

## 机制（`windowB_lath.py:295-318`）
```
λ = 0  ⇒ F2 项保持 NaN ⇒ 走标量路径（**归档**）
λ > 0  ⇒ γ_F2(v,w) = γ₀·[(1−λ) + λ·min(1, ‖Δε_{v,w}‖/Δe_ref)]
         Δe_ref = max over 异变体对的 ‖Δε‖
```

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **W-0（硬前置）** | **三臂都真的跑出结果**（`series.csv` 存在且 `rc=0`） | 3/3 |
| **W-1（`P43` 独有串）** | λ>0 的两臂**必须打印** `§122`/`Δe_ref`/`n_f2` 段；λ=0 臂**必须不打印** | 是/否 |
| **W-2（主）** | 三臂的 `nf2` **至少两两不同**（λ 有作用对象且有响应） | 有差异 |
| **W-3** | 若 W-2 无差异 ⇒ **如实报"λ 无响应"**，并给出**机理归因**（不得硬说成功） | — |
| **W-4** | `box_touch = 1` 全程（与 `big700` 同；本类判据适用） | =1 |
| **W-5** | 内存 < 12 GB（`R736` 的 `M-0`） | — |

## 配置 = `big700` **逐项不变** + 只加 `--f2-pair-gamma`
⇒ 满足`教训 21`（两臂只差一个因素）。

## 用法
    python3 _r742_f2ab.py --dry
    python3 _r742_f2ab.py
"""
import os
import subprocess
import sys
import threading
import time

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_f2ab'
RSS_LIMIT_MB = 12000

# ★ 与 `_r741_T2retry.py` 的 BASE **逐项相同**（唯一差别是下面加的 `--f2-pair-gamma`）
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
ARMS = [('f2lam0', '0.0'), ('f2lam05', '0.5'), ('f2lam1', '1.0')]


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
        stop.wait(25)


def main():
    dry = '--dry' in sys.argv
    for tag, lam in ARMS:
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + [
            '--f2-pair-gamma', lam, '--tag', tag]
        print('=== %s (--f2-pair-gamma %s) ===' % (tag, lam), flush=True)
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
