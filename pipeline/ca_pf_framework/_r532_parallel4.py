#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r532_parallel4.py —— **「一个算例 4 线程 × 同时 4 个」到底能不能把 20 核用上？**

## 背景（`R531_THREADSCALE.md`）
真实负载上（120 场 + qs-clock）：
| `--nthreads` | s/步 | 加速比 |
|---|---|---|
| 1 | 1.8750 | 1.000× |
| **4** | **0.9825** | **1.908×** ← 最快 |
| 8 | 0.9825 | 1.908× |
| 16 | 1.1225 | 1.670× |
⇒ 加线程到顶 1.9×，**16 线程反而更慢**。
⇒ 【推理】正确的"用满核"是**算例之间并行**（4 线程 × 4–5 个算例）。

## 本量具要证的（**判据先写死**）
* **P1 并发不显著拖慢单个算例**：
  4 个并发算例（各 `--nthreads 4`）的**各自** s/步
  与**单独跑**一个（`--nthreads 4`）的 s/步相比，**劣化 ≤ 35%**。
  （判据取 35%：若 4 个并发把单个拖慢到 1.35× 以上，
   则**总吞吐 = 4/1.35 = 2.96×** 仍优于 16 线程的 1.67×，但收益大幅缩水。）
* **P2 总吞吐必须真的更高**：
  `4 / s_并发` 与 `1 / s_单跑16线程` 比较 ⇒ **≥ 2.0×** 才算"值得这么干"。
* **P3 正对照：并发不得改变物理**：
  4 个算例**同配置**⇒ 末态 `Vt` **必须逐位相同**（并发只影响速度）。
* **P4 记账**：报告并发时的实际核占用（`%CPU` 之和），看是否真的把 20 核用上。

⚠ 每个并发算例用**独立 `--out`**（本仓 §3.2 教训 8：CSV 会互相覆盖）。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = '_exp/_bk_par4'
LATHS = ','.join(str(v) for v in range(1, 13) for _ in range(10))

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
        '--steps', '40']

RE_STEP = re.compile(r'\[(\s*\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')


def _env():
    e = dict(os.environ)
    for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        e[k] = '1'
    return e


def _launch(tag, nt):
    cmd = [PY, '-u', os.path.join(HERE, '_bk_exp.py')] + REAL + \
          ['--laths', LATHS, '--nthreads', str(nt), '--tag', tag,
           '--out', os.path.join(OUT, tag)]
    lp = os.path.join(HERE, '_w2_r532_%s.log' % tag)
    fh = open(lp, 'w')
    return subprocess.Popen(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                            env=_env()), fh, lp


def _parse(lp):
    txt = open(lp, errors='replace').read()
    sp = [(float(m.group(2)), float(m.group(3))) for m in RE_STEP.finditer(txt)]
    s = (sum(x[1] for x in sp[-4:]) / len(sp[-4:])) if sp else float('nan')
    return dict(s=s, n=len(sp), Vt=(sp[-1][0] if sp else float('nan')),
                crash=('Traceback' in txt))


def _cpu_sum():
    """并发期间的**核占用之和**（`ps` 的 `%cpu` 对每个 python 求和）。"""
    try:
        o = subprocess.run(['ps', '-eo', 'pcpu,args'], capture_output=True,
                           text=True, timeout=30).stdout
    except Exception:                                           # noqa: BLE001
        return float('nan')
    tot = 0.0
    for ln in o.splitlines():
        if '_bk_exp.py' in ln:
            try:
                tot += float(ln.split(None, 1)[0])
            except ValueError:
                pass
    return tot / 100.0          # ⇒ 核数


def main():
    L = ['=' * 100, 'R532 —— 4 线程 × 4 并发 vs 16 线程 × 1（真实负载）', '=' * 100, '']

    # ---- A：单独跑，4 线程 ----
    L.append('── A 单独跑（`--nthreads 4`） ──')
    t0 = time.time()
    p, fh, lp = _launch('solo4', 4)
    p.wait()
    fh.close()
    solo = _parse(lp)
    solo['wall'] = time.time() - t0
    L.append('   s/步 = **%.4f**（%d 读数，墙钟 %.1f s，末 Vt=%.6g）'
             % (solo['s'], solo['n'], solo['wall'], solo['Vt']))

    # ---- B：4 个并发，各 4 线程 ----
    L.append('')
    L.append('── B **4 个并发**（各 `--nthreads 4`，独立 `--out`） ──')
    t0 = time.time()
    procs = [_launch('par%d' % i, 4) for i in range(4)]
    peak = 0.0
    while any(p.poll() is None for p, _, _ in procs):
        peak = max(peak, _cpu_sum())
        time.sleep(5)
    for p, fh, _ in procs:
        fh.close()
    wall = time.time() - t0
    par = []
    for i, (_, _, lp) in enumerate(procs):
        r = _parse(lp)
        par.append(r)
        L.append('   算例%d：s/步 = **%.4f**（%d 读数，末 Vt=%.6g，崩=%s）'
                 % (i, r['s'], r['n'], r['Vt'], r['crash']))
    L.append('   4 个并发**总墙钟** = %.1f s（单跑 %.1f s ⇒ 摊到 4 个上每个 %.1f s）'
             % (wall, solo['wall'], wall / 4))
    L.append('   并发期间**核占用峰值（各 python 之和）** = **%.2f 核**（机器 20 核）'
             % peak)

    # ---- 判据 ----
    L.append('')
    ok = True
    smax = max(r['s'] for r in par) if par else float('nan')
    deg = smax / solo['s'] if solo['s'] else float('nan')
    p1 = deg <= 1.35
    L.append('   ▶ **P1 并发不显著拖慢单个**：最慢的并发算例 %.4f vs 单跑 %.4f '
             '⇒ 劣化 **%.3f×**（判据 ≤ 1.35×）⇒ **%s**'
             % (smax, solo['s'], deg, '✅ PASS' if p1 else '❌ FAIL'))
    thr_par = 4.0 / smax if smax else float('nan')
    thr_16 = 1.0 / 1.1225                     # `_r531` 实测 16 线程的 s/步
    p2 = (thr_par / thr_16) >= 2.0 if thr_par == thr_par else False
    L.append('   ▶ **P2 总吞吐更高**：4 并发 = %.3f 算例/单位时间；'
             '16 线程单跑 = %.3f ⇒ 比 **%.3f×**（判据 ≥ 2.0×）⇒ **%s**'
             % (thr_par, thr_16, thr_par / thr_16 if thr_16 else float('nan'),
                '✅ PASS' if p2 else '❌ FAIL'))
    vts = [r['Vt'] for r in par]
    p3 = (not any(r['crash'] for r in par)) and len(set('%.12g' % v for v in vts)) == 1
    L.append('   ▶ **P3 正对照（并发不改物理）**：4 个算例末态 Vt = %s ⇒ **%s**'
             % ('/'.join('%.12g' % v for v in vts),
                '✅ PASS（逐位相同）' if p3 else '❌ FAIL'))
    L.append('   ▶ **P4 核占用记账**：峰值 %.2f 核 / 20 核 = **%.0f%%**'
             % (peak, 100.0 * peak / 20.0))
    ok = p1 and p2 and p3
    L.append('')
    L.append('★ 汇总：P1=%s P2=%s P3=%s ⇒ **%s**'
             % ('PASS' if p1 else 'FAIL', 'PASS' if p2 else 'FAIL',
                'PASS' if p3 else 'FAIL',
                '"一个算例 4 线程 × 同时 4 个"**值得这么干**' if ok
                else '建议**不成立**，照实记'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r532_parallel4.log'), 'w') as fh:
        fh.write(out + '\n')
    with open(os.path.join(HERE, '_w2_r532_parallel4.json'), 'w') as fh:
        json.dump(dict(solo=solo, par=par, peak=peak), fh,
                  ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
