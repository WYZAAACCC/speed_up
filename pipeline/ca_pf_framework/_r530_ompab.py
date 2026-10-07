#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r530_ompab.py —— **任务(4)「把核数用满」的 A/B：`OMP_NUM_THREADS` 超额订阅**。

## 实测到的现象（`_r529` 运行中，`ps`/`top` 读数）
| 量 | 值 |
|---|---|
| `--nthreads` | **16** |
| `ps -o nlwp`（线程数） | **36** |
| `top` 的 `%CPU` | **266–353**（≈ **2.7–3.5 个核**，机器有 **20** 核） |
| `load average` | 2.84 |
| `/proc/<pid>/environ` 里的 `OMP_NUM_THREADS` | **没有**（也没有 `MKL_NUM_THREADS` / `NUMEXPR_NUM_THREADS`） |

**36 = 16（显式 worker）+ ~20（numpy/BLAS 自己的 OpenMP 池）**
⇒ **超额订阅**：显式线程池与 numpy 内部线程池各开一份，互相抢核。
（numpy 的 OpenMP 池默认 = 核数 = 20，没人设过 `OMP_NUM_THREADS`。）

## 假设与判据（**先写死，再跑**）
* **H1 超额订阅**：把 `OMP_NUM_THREADS=1`（连带 MKL/OPENBLAS/NUMEXPR）设上，
  让 numpy 不开自己的池 ⇒ **s/步应当变快**。
  * **判据**：`OMP=1` 的 s/步 **< 未设** 的 s/步，且加速 ≥ **1.05×** 才算"有意义的改善"。
  * **负对照**：`OMP=1` 若**更慢**，则 H1 被否 ⇒ 说明瓶颈不是超额订阅，而是别处
    （内存带宽 / 串行段 / Python 开销），**照实记，不得硬说"调好了"**。
* **H2 线程数本身是否有效**：同配置扫 `--nthreads ∈ {1, 4, 8, 16}`，
  看 s/步 的标度。**若 1→16 只快 ~2.5×，说明并行区只占一小部分**（阿姆达尔）。
* ⚠ 两组必须**只差 `OMP_NUM_THREADS` 这一个因素**（本仓 §3.3 教训 21）。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = '_exp/_bk_omp'

# 固定工作负载：小 N、短步数，只求"每步多快"，不求物理。
BASE = ['--N', '64', '--dx-nm', '62.5', '--every', '5',
        '--snap-every', '0' if False else '200', '--phi-band-every', '200',
        '--pair-every', '0', '--norm-smooth', '0',
        '--laths', '1,1,1,1,2,2,2,2,3,3,3,3',
        '--plate-L', '1000', '--plate-W', '500', '--plate-T', '510',
        '--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
        '--nuc-law', 'athermal', '--nuc-init', '0',
        '--alpha-km', '0.011', '--T-end', '350.0', '--cool-rate', '2.3524e6',
        # ⚠ 关掉准静态钟 ⇒ 走纯时间积分 ⇒ 步数是**固定**的（可比 s/步）
        '--steps', '24', '--out', OUT]

RE_STEP = re.compile(r'\[(\s*\d+)\]\s+Vt=.*?\|\s*([\d.]+)s/步')


def run_once(tag, nthreads, omp):
    env = dict(os.environ)
    if omp is None:
        for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                  'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
            env.pop(k, None)
    else:
        for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                  'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
            env[k] = str(omp)
    cmd = [PY, '-u', os.path.join(HERE, '_bk_exp.py')] + BASE + \
          ['--nthreads', str(nthreads), '--tag', tag]
    lp = os.path.join(HERE, '_w2_r530_%s.log' % tag)
    t0 = time.time()
    with open(lp, 'w') as fh:
        subprocess.run(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                       env=env, timeout=5400)
    wall = time.time() - t0
    txt = open(lp, errors='replace').read()
    per = [float(m.group(2)) for m in RE_STEP.finditer(txt)]
    # 末 4 个读数更接近稳态（首步含编译/预热）
    steady = sum(per[-4:]) / max(len(per[-4:]), 1) if per else float('nan')
    return dict(tag=tag, nthreads=nthreads, omp=omp, wall=wall,
                n_read=len(per), s_per_step=steady,
                crash=('Traceback' in txt))


def main():
    rows = []
    L = ['=' * 100,
         'R530 —— `OMP_NUM_THREADS` 超额订阅的 A/B（任务(4)「把核数用满」）',
         '=' * 100, '']

    # ---- H1：只差 OMP_NUM_THREADS ----
    L.append('── H1 只差 `OMP_NUM_THREADS`（`--nthreads 16` 固定） ──')
    a = run_once('omp_unset', 16, None)
    b = run_once('omp_1', 16, 1)
    for r in (a, b):
        L.append('   %-12s nthreads=%2d OMP=%-5s ⇒ **%.4f s/步**（%d 个读数，崩=%s）'
                 % (r['tag'], r['nthreads'], r['omp'], r['s_per_step'],
                    r['n_read'], r['crash']))
    if a['s_per_step'] and b['s_per_step'] and not a['crash'] and not b['crash']:
        sp = a['s_per_step'] / b['s_per_step']
        L.append('   ⇒ 加速 = %.4f / %.4f = **%.3f×**'
                 % (a['s_per_step'], b['s_per_step'], sp))
        ok1 = sp >= 1.05
        L.append('   ⇒ H1（超额订阅）%s'
                 % ('✅ **成立**：设 `OMP_NUM_THREADS=1` 确有改善' if ok1 else
                    '❌ **被否**：没有改善甚至更慢 ⇒ **瓶颈不是超额订阅**，'
                    '要往"内存带宽 / 串行段 / Python 开销"查。**照实记，不得硬说调好了。**'))
    else:
        ok1 = False
        L.append('   ⚠ 有跑崩溃或没读到 s/步 ⇒ **未取证**')
    rows.append(('H1 `OMP_NUM_THREADS=1` 加速 ≥ 1.05×', ok1,
                 '取自上面两个读数'))

    # ---- H2：线程标度 ----
    L.append('')
    L.append('── H2 线程标度（`OMP=1`，扫 `--nthreads`） ──')
    sc = []
    for nt in (1, 4, 16):
        r = run_once('thr%d' % nt, nt, 1)
        sc.append(r)
        L.append('   nthreads=%2d ⇒ **%.4f s/步**（崩=%s）'
                 % (nt, r['s_per_step'], r['crash']))
    if all(not r['crash'] for r in sc) and sc[0]['s_per_step']:
        sp16 = sc[0]['s_per_step'] / sc[-1]['s_per_step']
        L.append('   ⇒ 1 → 16 线程加速 = **%.3f×**' % sp16)
        L.append('   ⇒ %s'
                 % ('⚠ **只有 %.2f×（远低于 16×）** ⇒ 并行区只占一小部分'
                    '（阿姆达尔），或受**内存带宽**限制。' % sp16 if sp16 < 8 else
                    '✅ 标度良好'))
        rows.append(('H2 1→16 线程加速（记录值，不设阈值）', True,
                     '%.3f×' % sp16))
    else:
        L.append('   ⚠ 有跑崩溃 ⇒ **未取证**')
        rows.append(('H2 1→16 线程加速（记录值，不设阈值）', False, '有崩溃'))

    npass = sum(1 for _, ok, _ in rows if ok)
    L.append('')
    L.append('★ 汇总（**注意：H1 的"PASS"指"假设成立"，不是"跑得好"**）：%d/%d' % (npass, len(rows)))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r530_ompab.log'), 'w') as fh:
        fh.write(out + '\n')
    with open(os.path.join(HERE, '_w2_r530_ompab.json'), 'w') as fh:
        json.dump(dict(a=a, b=b, scale=sc), fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
