#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_nvscale.py —— ★ Part 2 的**时间账**：s/步 随 `nv`（场数）与 `N`（网格）的**真实标度**。

## 为什么必须现在量（这是 Part 2 的关键路径）
`R525 §6` 建议生产用 **`nv = 540`（= 12 变体 × 45 场）**、`N=160`。
但 `nv` 是**场数**，而本引擎几乎每个算子都是 `O(nv · N³)`：
`region()`（argmin over nv+1 场）、`eps0_fields`、`soft_phi`、`Lam` 缩并、`extend`、`curvature_of`…
⇒ **`nv` 24 → 540 是 22.5 倍工作量**。

用旧数粗估：`N=64/nv=24` 是 0.2814 s/步 ⇒ 按 `(160/64)^3.02 × (540/24)` 外推
⇒ **~100 s/步**。而 `R525 §9.1` 已实测**准静态钟 ~600 步就自己停在 `T_end`**
⇒ 600 × 100 s ≈ **16.7 h/次**。
**这必须实测**，不能靠外推：`N` 与 `nv` 的标度很可能**不是**可分离的
（N 变大会让 numpy 的向量化更划算 ⇒ nv 的斜率会变）。

## 本脚本做什么
在一个会话里、同一套开关下，量**两个方向的标度**：
* **A 系列（定 N=64，扫 nv）**：nv = 24 / 72 / 144 / 288 / 540 ⇒ 得 `f_nv`
* **B 系列（定 nv=24 与 nv=72，扫 N）**：N = 64 / 160 ⇒ 得 `g_N`（在**两个 nv 上**各取一次，
  用来检验"可分离"这个假设本身）
* 然后**预测** `N=160, nv=540`，并**给出可接受性判决**。

## 口径
* 开关：生产意图档（7 个已验证开关全开）+ `--phi-prec f32 --pf-phi onfly`（省内存）。
  ⚠ 记账：这不是"归档默认档"，所以 s/步**不能**与归档的 0.2814 直接比 ——
  本脚本的所有比较**都在本会话内部**做。
* `s/步` 取**末 4 个稳定读数**的均值（`_r531` 同口径）。
* 峰值 RSS 由**独立看门狗**每 0.4 s 读 `/proc/<pid>/status` 的 `VmHWM` 取，不靠进程自报。
* 每臂 `taskset` 绑 **0–3**，`--nthreads 4`（`R531` 实测的最优打法）。
"""
import json
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = '_exp/_bk_nvscale'

# ★ 真实算例配置（与 `_r531_scalereal.py` 的 REAL **逐字相同**），只压 `--steps` 与 `--N`
REAL = ['--dx-nm', '62.5', '--every', '1',
        # ⚠ `--snap-every 0` **非法**（`_bk_exp.py:3199` 硬失败）——
        #   它会被直接拿去取模。要"不打快照"就传一个 > --steps 的值。
        '--snap-every', '99999', '--phi-band-every', '0', '--eng-cadence', '0',
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
        '--steps', '12',
        # ★ 生产意图档（7 个已验证开关；逐位相同，见 `R580_VERIFY.md`）
        '--eps0-mode', 'einsum', '--ed-pair', 'gather', '--argmin2-mode', 'copyto',
        '--k-loop', 'act', '--act-mode', 'bincount', '--grad-mode', 'sliced',
        '--pf-phi', 'onfly', '--phi-prec', 'f32',
        '--out', OUT]

RE_STEP = re.compile(r'\[(\s*\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')


def laths_for(m):
    """12 变体 × m 场 —— 生产形状（`R526`：变体数 12 是物理量）。"""
    return ','.join(str(v) for v in range(1, 13) for _ in range(m))


def peak_rss_watch(pid, box, stop):
    """独立看门狗：每 0.4 s 读一次 /proc/<pid>/status 的 VmHWM。"""
    best = 0
    while not stop.is_set():
        try:
            with open('/proc/%d/status' % pid) as fh:
                for ln in fh:
                    if ln.startswith('VmHWM:'):
                        best = max(best, int(ln.split()[1]))
                        break
        except Exception:
            pass
        stop.wait(0.4)
    box['kb'] = best


def run_once(N, m, tag):
    nv = 12 * m
    env = dict(os.environ)
    for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        env[k] = '1'
    cmd = (['taskset', '-c', '0-3', PY, '-u', os.path.join(HERE, '_bk_exp.py')]
           + REAL + ['--N', str(N), '--laths', laths_for(m),
                     '--nthreads', '4', '--tag', tag])
    lp = os.path.join(HERE, '_w2_r581_%s.log' % tag)
    box, stop = {}, threading.Event()
    t0 = time.time()
    with open(lp, 'w') as fh:
        p = subprocess.Popen(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                             env=env)
        th = threading.Thread(target=peak_rss_watch, args=(p.pid, box, stop),
                              daemon=True)
        th.start()
        try:
            p.wait(timeout=14400)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait()
        stop.set(); th.join(timeout=3)
    wall = time.time() - t0
    txt = open(lp, errors='replace').read()
    sp = [(int(mm.group(1)), float(mm.group(2)), float(mm.group(3)))
          for mm in RE_STEP.finditer(txt)]
    k = min(4, len(sp))
    steady = (sum(x[2] for x in sp[-k:]) / k) if k else float('nan')
    # ★ 判据：0 读数 = **量具失效**，不许静默变成 nan 混过去（本仓 §3.4 的教训）。
    bad = ''
    if k == 0:
        bad = '0 读数'
        if 'Traceback' in txt:
            bad += ' + Traceback'
        elif '❌' in txt:
            bad += ' + 参数被拒'
        else:
            bad += ' + 不明原因'
    elif 'Traceback' in txt:
        bad = 'Traceback'
    if bad:
        print('   ⚠⚠ 臂 %s **量具失效**（%s）—— 日志尾 12 行：' % (tag, bad))
        for ln in txt.strip().splitlines()[-12:]:
            print('        | ' + ln)
    # 构造期：从日志里抓 "构造" 或 "build" 的耗时（有就记，没有就 None）
    build = None
    mb_ = re.search(r'构造[^0-9]{0,24}([\d.]+)\s*s', txt)
    if mb_:
        build = float(mb_.group(1))
    return dict(N=N, m=m, nv=nv, tag=tag, wall=wall, s_step=steady, n=len(sp),
                peak_mb=(box.get('kb', 0) / 1024.0), build_s=build,
                Vt=(sp[-1][1] if sp else float('nan')),
                crash=('Traceback' in txt), log=os.path.basename(lp))


def main():
    L = ['=' * 100,
         'R581 —— Part 2 时间账：s/步 随 nv 与 N 的**实测标度**',
         '=' * 100,
         '  ⚠ 所有比较都在**本会话内部**做（同宿主、同开关、同绑核）。',
         '  开关档 = 生产意图档（7 开关全开 + f32 + onfly）。', '']
    res = []

    # ---- A 系列：定 N=64，扫 nv -------------------------------------------
    L.append('── A 系列：N=64，扫 nv（12 变体 × m） ──')
    for m in (2, 6, 12, 24, 45):
        r = run_once(64, m, 'A_N64_m%02d' % m)
        res.append(r)
        L.append('   m=%-3d nv=%-4d ⇒ **%8.4f s/步**  (%2d 读数, 墙钟 %6.1f s, '
                 '峰值 %7.1f MB, 崩=%s)'
                 % (m, r['nv'], r['s_step'], r['n'], r['wall'], r['peak_mb'],
                    r['crash']))
        sys.stdout.flush()

    # ---- B 系列：两个 nv 上各扫 N -----------------------------------------
    L.append('')
    L.append('── B 系列：N=64 vs N=160（在两个 nv 上各做一次，检验"可分离"） ──')
    for m in (2, 6):
        r = run_once(160, m, 'B_N160_m%02d' % m)
        res.append(r)
        L.append('   m=%-3d nv=%-4d N=160 ⇒ **%8.4f s/步**  (%2d 读数, 墙钟 %6.1f s, '
                 '峰值 %7.1f MB, 崩=%s)'
                 % (m, r['nv'], r['s_step'], r['n'], r['wall'], r['peak_mb'],
                    r['crash']))
        sys.stdout.flush()

    # ---- 标度律 ------------------------------------------------------------
    L.append('')
    L.append('=' * 100)
    L.append('标度律')
    L.append('=' * 100)
    A = [r for r in res if r['N'] == 64 and not r['crash'] and r['s_step'] == r['s_step']]
    import math
    if len(A) >= 2:
        x = [math.log(r['nv']) for r in A]
        y = [math.log(r['s_step']) for r in A]
        n = len(x)
        sx, sy = sum(x), sum(y)
        sxx = sum(v * v for v in x)
        sxy = sum(a * b for a, b in zip(x, y))
        p = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        c = math.exp((sy - p * sx) / n)
        L.append('   f_nv（N=64）： s/步 ≈ %.4e · nv^%.3f' % (c, p))
        L.append('      ⇒ 若严格线性（p=1）则 s/步 ∝ nv；实测指数 p 就是"nv 摊薄程度"。')

    def get(N, m):
        for r in res:
            if r['N'] == N and r['m'] == m:
                return r
        return None

    pred = {}
    for m in (2, 6):
        a, b = get(64, m), get(160, m)
        if a and b and a['s_step'] > 0 and not (a['crash'] or b['crash']):
            g = b['s_step'] / a['s_step']
            pred[m] = g
            L.append('   g_N（nv=%d）： N 64→160 是 **%.3f×**（=  (160/64)^%.3f）'
                     % (a['nv'], g, math.log(g) / math.log(160.0 / 64.0)))
    if len(pred) == 2:
        gg = sorted(pred.values())
        L.append('      ⇒ 两个 nv 上分别 %.3f× 与 %.3f× ⇒ 差 %.1f%% ⇒ %s'
                 % (gg[0], gg[1], 100 * (gg[1] - gg[0]) / gg[0],
                    '**不可分离**（要用各自 nv 自己的 g_N）' if gg[1] / gg[0] > 1.05
                    else '**近似可分离**（可用同一 g_N）'))

    # ---- 预测 N=160 / nv=540 ----------------------------------------------
    L.append('')
    L.append('=' * 100)
    L.append('★ 预测：N=160, nv=540（R525 §6 建议的生产配置）')
    L.append('=' * 100)
    a6, b6 = get(64, 6), get(160, 6)          # nv=72 臂
    a2, b2 = get(64, 2), get(160, 2)          # nv=24 臂
    est = None
    if len(A) >= 2 and a6 and b6:
        # 用 nv=72 的 g_N 外推到 nv=540（同一条 nv 曲线，最接近的锚点）
        s160_72 = b6['s_step']
        est = s160_72 * (540.0 / 72.0) ** (res and _p_of(A) or 1.0)
        L.append('   锚点：N=160/nv=72 实测 %.4f s/步' % s160_72)
        L.append('   用 f_nv 的指数外推到 nv=540 ⇒ **%.2f s/步**' % est)
    elif a2 and b2:
        est = b2['s_step'] * (540.0 / 24.0)
        L.append('   锚点：N=160/nv=24 实测 %.4f s/步（线性外推）' % b2['s_step'])
        L.append('   ⇒ **%.2f s/步**' % est)
    if est:
        for ns in (600, 900, 1200):
            L.append('   ⇒ %4d 步（准静态钟 ~600 步量级，R525 §9.1）≈ **%6.2f h**'
                     % (ns, est * ns / 3600.0))
        res_ok = est * 600 / 3600.0 <= 12
        L.append('   ⇒ 判决（判据：600 步 ≤ 12 h）：%s'
                 % ('✅ 可行' if res_ok else '❌ **不可行 —— 必须改 nv 或 N**'))

    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r581_nvscale.log'), 'w') as fh:
        fh.write(out + '\n')
    with open(os.path.join(HERE, '_w2_r581_nvscale.json'), 'w') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return 0


def _p_of(A):
    import math
    x = [math.log(r['nv']) for r in A]
    y = [math.log(r['s_step']) for r in A]
    n = len(x)
    sx, sy = sum(x), sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(a * b for a, b in zip(x, y))
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


if __name__ == '__main__':
    sys.exit(main())
