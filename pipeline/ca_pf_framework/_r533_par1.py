#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r533_par1.py —— **决定性实验：瓶颈是"核"还是"共享资源（内存带宽）"？**

## 为什么这个实验能分辨
`_r532` 实测：4 个并发（各 `--nthreads 4`）⇒ **每个慢 1.886×**，但总吞吐 2.41× 更好，
而核占用峰值只有 **8.33/20 = 42%** ⇒ **核没满，却已经互相拖累了。**

两种解释给出**相反**的预测：

| 假设 | 预测 |
|---|---|
| **H_core（核不够）** | 把每个算例降到 **1 线程** 再并发 4 个 ⇒ 4 个核各干各的 ⇒ **每个几乎不慢**（s/步 ≈ 单跑 1 线程的 1.8750） |
| **H_mem（共享资源/内存带宽）** | 无论几线程，**总吞吐上限固定** ⇒ 4×1 线程并发**同样**把每个拖慢 ~1.9×（即 s/步 ≈ 3.5） |

⇒ **一次实验就能分开**（本仓 §3.3 教训 27：要挑两个假设**分歧最大**的工况）。

## 判据（**先写死**）
* **单跑 `--nthreads 1` 的 s/步** = `_r531` 已实测的 **1.8750**（复用它，不再跑）。
* **4 并发 `--nthreads 1`**：
  * 若**每个** s/步 **≤ 1.8750 × 1.25** ⇒ **H_core 成立** ⇒ 结论是"**算例之间并行**确实能把核用上"。
  * 若**每个** s/步 **≥ 1.8750 × 1.6** ⇒ **H_mem 成立** ⇒ 结论是"**总吞吐被共享资源卡死**，
    加线程/加并发都拿不到更多" ⇒ **必须改算法**（降内存流量或降串行段）。
* **正对照**：4 个算例的末态 `Vt` **必须逐位相同**。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = '_exp/_bk_par1'
LATHS = ','.join(str(v) for v in range(1, 13) for _ in range(10))
SINGLE1 = 1.8750            # `_r531_scalereal.py` 实测：`--nthreads 1` 的 s/步

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
        '--reinit-dt', '1e-4', '--reinit-band', '6.0', '--steps', '40']
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
    lp = os.path.join(HERE, '_w2_r533_%s.log' % tag)
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
    return tot / 100.0


def main():
    L = ['=' * 100,
         'R533 —— 瓶颈是"核"还是"共享资源"？（4 并发 × `--nthreads 1`）',
         '=' * 100,
         '  基准：单跑 `--nthreads 1` 的 s/步 = **%.4f**（`_r531` 实测）' % SINGLE1,
         '']
    t0 = time.time()
    procs = [_launch('p1_%d' % i, 1) for i in range(4)]
    peak = 0.0
    while any(p.poll() is None for p, _, _ in procs):
        peak = max(peak, _cpu_sum())
        time.sleep(5)
    for p, fh, _ in procs:
        fh.close()
    wall = time.time() - t0
    res = []
    for i, (_, _, lp) in enumerate(procs):
        r = _parse(lp)
        res.append(r)
        L.append('   算例%d（1 线程）：s/步 = **%.4f**（%d 读数，末 Vt=%.6g，崩=%s）'
                 % (i, r['s'], r['n'], r['Vt'], r['crash']))
    L.append('   4 并发总墙钟 = %.1f s；核占用峰值 = **%.2f 核**/20' % (wall, peak))
    smax = max(r['s'] for r in res)
    deg = smax / SINGLE1
    L.append('')
    L.append('   ▶ 最慢的并发算例 %.4f vs 单跑 1 线程 %.4f ⇒ **劣化 %.3f×**'
             % (smax, SINGLE1, deg))
    if deg <= 1.25:
        v = ('✅ **H_core 成立**（核不够）⇒ "**算例之间并行**"确实能把核用上：'
             '4 个 1 线程算例几乎不互相拖累')
    elif deg >= 1.6:
        v = ('🔴 **H_mem 成立**（共享资源/内存带宽）⇒ **总吞吐被非核资源卡死** ⇒ '
             '**加线程、加并发都拿不到更多** ⇒ 必须**改算法**（降内存流量/降串行段）')
    else:
        v = '⚠ 落在两假设之间（1.25–1.6）⇒ **未能干净分辨**，照实记'
    L.append('   ⇒ %s' % v)
    vts = [r['Vt'] for r in res]
    p3 = (not any(r['crash'] for r in res)) and len(set('%.12g' % x for x in vts)) == 1
    L.append('   ▶ 正对照（并发不改物理）：末态 Vt = %s ⇒ **%s**'
             % ('/'.join('%.12g' % x for x in vts),
                '✅ 逐位相同' if p3 else '❌ 不一致'))
    # 总吞吐对照
    L.append('')
    L.append('   ── 三种打法的**总吞吐**（算例/单位时间，越大越好） ──')
    rows = [('16 线程 × 1 个', 1.0 / 1.1225),
            ('4 线程 × 1 个', 1.0 / 0.9875),
            ('4 线程 × 4 个（`_r532`）', 4.0 / 1.8625),
            ('**1 线程 × 4 个（本轮）**', 4.0 / smax)]
    for nm, th in rows:
        L.append('     %-26s %.3f' % (nm, th))
    L.append('   ⇒ 与 `_r532` 的 4 线程×4 个相比：**%.3f×**'
             % ((4.0 / smax) / (4.0 / 1.8625)))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r533_par1.log'), 'w') as fh:
        fh.write(out + '\n')
    with open(os.path.join(HERE, '_w2_r533_par1.json'), 'w') as fh:
        json.dump(dict(res=res, peak=peak, single1=SINGLE1), fh,
                  ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
