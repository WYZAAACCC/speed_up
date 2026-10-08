#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r736_ab2.py —— **F-1 的内存安全 A/B**（`N=96`、6 µm、200 步）。

## 为什么重做（`R736` 的事故记录）
`_r733_longab.py` 用 **`N=128`**：**只有 4 个场时 RSS 已 11.9 GB**（WSL 限 24 GB）
⇒ **已安全中止**（`_r736_kill.sh` / `_r736_kill2.sh`，杀后内存回到 880 MB）。
**教训**：`R630` 的"C1 每进程 ≤4 核 / C5 必须实测验证"只覆盖了 **CPU**，
**没有覆盖内存** —— 本次把它补上。

## 内存预算（**实测**，写死为判据）
| 配置 | 场数 | 实测 RSS |
|---|---:|---:|
| `N=96`（`B2P_q0`） | 6 | **~1.3 GB/场** ⇒ 总 ~8 GB 以内（`R630` 记账） |
| `N=128`（`L_off`） | **4** | **11.9 GB** ⛔ **不可行** |
⇒ **本脚本只用 `N=96`。**

## 配置选择（**唯一的权衡**）
`N=96` 的 `q0` 类配置 @**225** 撞盒（`R720 §1`）⇒ **安全窗口 ≤ 200 步**。
⇒ 本脚本取 **200 步**（撞盒前最后一个 25 的倍数 = 200）。
⚠ 记账：这**仍然**比 `R730` 的 100 步长一倍，但**不是"很长"** ⇒
`J-8b` 只能判"100→200 的趋势"，**不能判饱和**。

## 判据（**先登记，可 FAIL**）
| # | 判据 | 靶 |
|---|---|---|
| **M-0（新增，安全）** | 全程 RSS **< 12 GB**；进程数 == 1 | 否则**中止** |
| **J-11** | 开关生效：至少一个可观测量不同 | 不同 |
| **J-8b** | 公共安全步上 PCA（长厚比）上升 | 开 > 关 |
| **J-5b** | `β_h^eff` 兑现率的**多步中位** | ≥ 0.98 |
| **J-9b** | `f_flat` 不劣化 | ≥ 基线 |
| **J-10b** | 同 `Vt` 步数比 | ∈ [0.8, 1.25] |

## 用法
    python3 _r736_ab2.py --dry
    python3 _r736_ab2.py
"""
import os
import subprocess
import sys
import threading
import time

PY = '/root/miniconda3/envs/ml/bin/python'
FW = '/mnt/f/speed_up/pipeline/ca_pf_framework'
OUT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq200'
RSS_LIMIT_MB = 12000          # M-0 的安全上限（WSL 24 GB，留足余量）

BASE = [
    '--N', '96', '--dx-nm', '62.5', '--steps', '200',
    '--every', '25', '--snap-every', '25', '--pair-every', '50',
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
    """M-0：每 15 s 查 RSS，超限就杀（`R630` 的内存版）。"""
    while not stop.is_set():
        pids = subprocess.run(['pgrep', '-f', '[_]bk_exp.py'],
                              capture_output=True, text=True).stdout.split()
        if pids:
            m = rss_mb(pids)
            print('    [watchdog] RSS = %d MB（限 %d）' % (m, RSS_LIMIT_MB), flush=True)
            if m > RSS_LIMIT_MB:
                print('    ⛔ [watchdog] **超内存上限 ⇒ 中止**', flush=True)
                for p in pids:
                    subprocess.run(['kill', '-9', p])
        stop.wait(15)


def main():
    dry = '--dry' in sys.argv
    print('★ 内存判据 M-0：RSS < %d MB（超限由 watchdog 中止）' % RSS_LIMIT_MB)
    for tag, env in (('S_off', {}), ('S_on', {'NDIR_LSQ': '1'})):
        cmd = [PY, '-u', '_bk_exp.py'] + BASE + ['--tag', tag]
        print('=== %s  (NDIR_LSQ=%s) ===' % (tag, env.get('NDIR_LSQ', 'unset')))
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
