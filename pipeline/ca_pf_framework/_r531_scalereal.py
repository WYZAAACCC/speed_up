#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r531_scalereal.py —— **任务(4) 的线程标度**，用**真实工作负载**重测。

## 为什么必须重测（`_r530` 的量具错了）
`_r530` 的 `BASE` 只给了 **12 个场**、`--N 64`，而**真实算例是 120 个场**（`_r529`）。
实测读数：

| 配置 | s/步 |
|---|---|
| `_r530`（12 场，无 qs-clock） | **0.31** |
| `_r529`（120 场，qs-clock，16 线程） | **1.74–2.19** |

⇒ `_r530` 的每步工作量比真实算例**小 ~7 倍** ⇒ **并行区太小、被串行开销淹没**
⇒ 它给出的「1→16 线程 0.98×」**不能用来判断真实算例的标度**
（而先前 `_r488_threadscale.py` 在更重的配置上量到过 **2.52× @16 线程**）。
**⇒ 这是"量具本身没测到目标现象"（本仓 §3.3 教训 14），必须换负载重测。**

## 本量具的配置 = **真实算例的配置**（与 `_r529_paramrun2.sh` 逐字相同），
只把 `--steps` 压到 40（够取 8 个稳态读数），并**显式传 `--qs-clock 1`**
（`_r530` 漏了它 ⇒ 走的是**另一条**积分路径，这是第二个不可比的点）。

## 判据（**先写死**）
* **S1**：记录 `--nthreads ∈ {1, 2, 4, 8, 16}` 的 s/步，给出 `1→N` 加速比。
  **不设通过阈值**（这是**测量**，不是判决），但**必须报告**。
* **S2 正对照**：`--nthreads 1` 与 `--nthreads 16` 的**物理末态必须一致**
  （同一步数的 `Vt` 差 ≤ 1e-6 相对）—— 否则线程数改变了物理，那本身是 bug。
* **S3**：`OMP_NUM_THREADS` 全部固定为 1（`_r530` 已证超额订阅不是主因，
  固定它以免混淆）。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = '_exp/_bk_scale'

# ★ 与 `_r529_paramrun2.sh` **逐字相同**，只压 `--steps`
REAL = ['--N', '64', '--dx-nm', '62.5', '--every', '5',
        '--snap-every', '200', '--phi-band-every', '200',
        '--pair-every', '0', '--norm-smooth', '0',
        '--plate-L', '1000', '--plate-W', '500', '--plate-T', '510',
        '--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
        '--nuc-law', 'athermal', '--nuc-init', '6',
        '--nuc-block-target', '8', '--nuc-shape', 'ellipsoid',
        '--nuc-supercrit', '1', '--nuc-sites-refill', '1',
        '--qs-clock', '1', '--qs-max-relax', '100',
        '--alpha-km', '0.011', '--T-end', '350.0', '--cool-rate', '2.3524e6',
        '--facet-proj', '0', '--facet-excl', '0',
        '--reinit-dt', '1e-4', '--reinit-band', '6.0',
        '--steps', '40', '--out', OUT]
# 12 变体 × 10 场 = 120（真实算例的 `--laths`）
LATHS = ','.join(str(v) for v in range(1, 13) for _ in range(10))

RE_STEP = re.compile(r'\[(\s*\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')


def run_once(nt):
    env = dict(os.environ)
    for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        env[k] = '1'
    tag = 'scal%02d' % nt
    cmd = [PY, '-u', os.path.join(HERE, '_bk_exp.py')] + REAL + \
          ['--laths', LATHS, '--nthreads', str(nt), '--tag', tag]
    lp = os.path.join(HERE, '_w2_r531_%s.log' % tag)
    t0 = time.time()
    with open(lp, 'w') as fh:
        subprocess.run(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                       env=env, timeout=7200)
    wall = time.time() - t0
    txt = open(lp, errors='replace').read()
    sp = [(int(m.group(1)), float(m.group(2)), float(m.group(3)))
          for m in RE_STEP.finditer(txt)]
    steady = (sum(x[2] for x in sp[-4:]) / len(sp[-4:])) if sp else float('nan')
    return dict(nt=nt, wall=wall, s=steady, n=len(sp),
                Vt=(sp[-1][1] if sp else float('nan')),
                crash=('Traceback' in txt))


def main():
    L = ['=' * 100,
         'R531 —— 线程标度（**真实负载**：120 场 + qs-clock）', '=' * 100,
         '   ⚠ `_r530` 用 12 场测出"1→16 线程 0.98×"，那是**量具太轻**的伪结果，',
         '     本量具换成真实负载重测。', '']
    res = []
    for nt in (1, 2, 4, 8, 16):
        r = run_once(nt)
        res.append(r)
        L.append('   --nthreads %2d ⇒ **%.4f s/步**（%d 读数；墙钟 %6.1f s；末 Vt=%.6g；崩=%s）'
                 % (nt, r['s'], r['n'], r['wall'], r['Vt'], r['crash']))
    ok = [r for r in res if not r['crash'] and r['s'] == r['s']]
    L.append('')
    if len(ok) >= 2:
        base = ok[0]['s']
        L.append('   ── 加速比（相对 `--nthreads %d`） ──' % ok[0]['nt'])
        for r in ok:
            L.append('     %2d 线程 ⇒ **%.3f×**' % (r['nt'], base / r['s']))
        best = min(ok, key=lambda r: r['s'])
        L.append('   ⇒ **最快 = %d 线程（%.4f s/步，%.3f×）**'
                 % (best['nt'], best['s'], base / best['s']))
        # S2 正对照：线程数不得改变物理
        vt = [r['Vt'] for r in ok]
        rel = (max(vt) - min(vt)) / max(abs(vt[0]), 1e-300)
        L.append('   ⇒ S2 正对照（线程数**不得**改变物理）：末态 Vt 相对差 = **%.3e** %s'
                 % (rel, '✅ 一致' if rel < 1e-9 else
                    '❌ **不一致 ⇒ 线程数改变了物理，那是 bug**'))
    else:
        L.append('   ⚠ 有效读数不足 ⇒ **未取证**')
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r531_scalereal.log'), 'w') as fh:
        fh.write(out + '\n')
    with open(os.path.join(HERE, '_w2_r531_scalereal.json'), 'w') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
