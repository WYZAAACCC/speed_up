#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_smoke_f3.py —— **F3（同变体低角晶界）能不能存在、会不会动**的最小判决实验。

## 为什么能在**不改引擎**的前提下先做

引擎对"场的个数"本来就是通用的：`nreg = len(eps0)+1`。
把**同一个变体的 eps0 传两次**，就得到两个**物理上同变体、但彼此独立**的场
⇒ 它们之间的界面就是 **F3**（`BLOCK_DERIVATION.md` §2.3），
此时面能是标量 `gamma`（=0.15 J/m²）= **`dry` 臂在 θ≈1.83° 处的取值**。

## 装置（**板条贴面堆叠**，即真实 block 的几何）

两根同变体板条沿 @@\\mathbf n^*@@（惯习面法向）**面对面**放置，初始**贴合**（gap=0）
⇒ t=0 就有一张 F3 界面 ⇒ 位置基线 P0 有定义。

## 三臂（单变量 + 双向对照）

| 臂 | 设置 | 预期 | 作用 |
|---|---|---|---|
| `main` | nv=2（eps0 复制），γ=0.15 | F3 **存在**且**几乎不动** | 主臂（预言 P-1） |
| `ctrl_pos` | 同上，γ=**100** J/m² | F3 **必须明显移动** | **量具正对照**（AGENTS §3.3-19） |
| `ctrl_neg` | nv=1：两片播进**同一个场** | F3 胞数恒 = **0** | **量具负对照** |

没有 `ctrl_pos`，"界面不动"这句话**没有意义**（量具可能根本量不出移动）。

## 落盘（用户要求：全过程数据留 F 盘）

每臂写 `<out>/<arm>/series.csv`（逐步指标）+ `snap_XXXXX.npz`（**全量 φ + region**）
⇒ 即使量具有 bug，事后也能用修好的量具在**完整数据**上重测。

跑法：
    python3 _bk_smoke_f3.py --steps 120 --every 10
    python3 _bk_smoke_f3.py --probe-only
"""
import argparse
import csv
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import _bk_measure as BM                                        # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

COLS = ['step', 't_s', 'wall_s', 'dt', 'V0', 'V1', 'V2', 'Vt',
        'nf3', 'f3_area_m2', 'f3_area_stair', 'f3_pos_m', 'f3_pos_dx',
        'f3_std_m', 'nslab_n', 'nf3_col', 'runs', 'ncomp_1', 'ncomp_2',
        'n_1', 'w_1', 'a_1', 'n_2', 'w_2', 'a_2', 'box_touch', 'finite']
assert len(COLS) == 27
assert len(set(COLS)) == 27


def argmin_normal_zero_strain_probe(do=True):
    """B4 探针：`eps0[k]==eps0[l]` ⇒ `de=0` ⇒ `_argmin_normal(C, 0)` 会怎样？"""
    print('-' * 100)
    print('探针 B4：`_argmin_normal(C, 零应变)`（复制 eps0 ⇒ ncmp 会拿到零应变）')
    t0 = time.time()
    try:
        out = W._argmin_normal(C, np.zeros((3, 3)))
        n = np.asarray(out[0], float)
        print('   返回 n=%s  E=%.6e  cons=%.6f  （%.1f s）'
              % (np.array2string(n, precision=6), out[1], out[2], time.time() - t0))
        print('   判定：**不崩、但零应变的"最优法向"没有物理意义** ⇒')
        print('        同变体配对的 `ncmp` 必须**显式置 NaN**（让 `facet_nref` 回退 `npref`），')
        print('        不能靠"它没崩"蒙过去。（`BLOCK_DERIVATION.md` §I-2）')
    except Exception as e:
        print('   ✗ 抛异常 %r（%.1f s）⇒ 必须守卫' % (e, time.time() - t0))
    print('-' * 100)


def _pos_grid(g, n_hab):
    N = g.N
    ii = np.arange(N)
    return g.dx * (n_hab[0] * ii[:, None, None] + n_hab[1] * ii[None, :, None]
                   + n_hab[2] * ii[None, None, :])


def f3_metrics(g, k1, k2, pos):
    reg = g.region()
    m1, m2 = (reg == k1), (reg == k2)
    if not m1.any() or not m2.any():
        return 0, np.nan, np.nan, 0.0
    touch = np.zeros_like(m1)
    for ax in (0, 1, 2):
        for sh in (1, -1):
            touch |= (m1 & np.roll(m2, sh, axis=ax))
            touch |= (m2 & np.roll(m1, sh, axis=ax))
    n = int(touch.sum())
    if n == 0:
        return 0, np.nan, np.nan, 0.0
    v = pos[touch]
    return n, float(v.mean()), float(v.std()), n * g.dx ** 2


def f1_count(g, k):
    reg = g.region()
    mk, m0 = (reg == k), (reg == 0)
    c = 0
    for ax in (0, 1, 2):
        for sh in (1, -1):
            c += int((mk & np.roll(m0, sh, axis=ax)).sum())
    return c


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def run_arm(name, a, gamma, nv, dup, plate, outroot):
    N, L = a.N, a.L_um * 1e-6
    dx = L / N
    # ★★ 每次运行写在**带 tag 的子目录**里 —— 绝不覆盖上一次的数据
    #   （用户要求：全过程数据留 F 盘，量具有 bug 也能事后重测）。
    outdir = os.path.join(outroot, '%s_%s' % (name, a.tag) if a.tag else name)
    os.makedirs(outdir, exist_ok=True)
    print('=' * 100)
    print('臂 %-9s N=%d Δx=%.1f nm L=%.2f µm nv=%d γ=%.5g J/m² norm_smooth=%d '
          'gap=%.0f nm steps=%d'
          % (name, N, dx * 1e9, L * 1e6, nv, gamma, a.norm_smooth, a.gap_nm, a.steps))
    print('=' * 100)
    eps0 = ([np.asarray(EPS0[0], float).copy() for _ in range(nv)] if dup
            else [np.asarray(EPS0[v], float).copy() for v in range(nv)])
    npref = {i + 1: np.asarray(NPF[1 if dup else (i + 1)], float)
             for i in range(nv)}
    t0 = time.time()
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=gamma, Mob=MOB,
                        df=[0.0] + [DF] * nv, workers=1, reinit_every=0,
                        reinit_dt=6.0e-7, reinit_band_cells=6.0)
    print('构造 %.1f s' % (time.time() - t0))
    n_hab = np.asarray(NPF[1], float); n_hab = n_hab / np.linalg.norm(n_hab)
    w_ax = np.asarray(g.wtab[1], float); w_ax = w_ax / np.linalg.norm(w_ax)
    a_ax = np.asarray(g.atab[1], float); a_ax = a_ax / np.linalg.norm(a_ax)
    print('   n*=%s  w=%s  a=%s   (n*·w=%.3f n*·a=%.3f w·a=%.3f)'
          % (np.array2string(n_hab, precision=4), np.array2string(w_ax, precision=4),
             np.array2string(a_ax, precision=4), n_hab @ w_ax, n_hab @ a_ax,
             w_ax @ a_ax))
    pos = _pos_grid(g, n_hab)

    c0 = np.array([L / 2] * 3)
    half = 0.5 * (plate['T'] + a.gap_nm) * 1e-9
    fields = [1, 2] if nv >= 2 else [1, 1]
    for f, c in zip(fields, [c0 - half * n_hab, c0 + half * n_hab]):
        g.seed_plate(f, c, n_hab, plate['W'] * 0.5e-9, plate['T'] * 1e-9,
                     elong=plate['L'] / plate['W'], along=a_ax, flat_end=True)
    g.init_parent()
    print('播种：场 %s（板条 %s nm，间隔 %.0f nm，沿 n* 面对面）'
          % (fields, plate, a.gap_nm))

    KW = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=a.beta_h,
              mob_beta_w=a.beta_w, adv_grad='proj2', norm_smooth=a.norm_smooth,
              facet_lam=0.0, facet_eps=0.05)
    dt = 0.15 * dx / (MOB * DF)
    tsim = a.steps * dt
    print('dt=%.4e s（标称 %.2f nm/步）  %d 步 ⇒ t_sim=%.3e s'
          % (dt, 0.15 * dx * 1e9, a.steps, tsim))

    csvf = open(os.path.join(outdir, 'series.csv'), 'w', newline='')
    cw = csv.writer(csvf); cw.writerow(COLS)
    import json
    with open(os.path.join(outdir, 'meta.json'), 'w', encoding='utf-8') as _m:
        json.dump(dict(arm=name, tag=a.tag, N=N, L=L, dx_nm=dx * 1e9,
                       nv=nv, dup_eps0=bool(dup), gamma=gamma,
                       norm_smooth=a.norm_smooth, beta_h=a.beta_h,
                       beta_w=a.beta_w, gap_nm=a.gap_nm, steps=a.steps,
                       every=a.every, plate=plate, dt=dt,
                       t_sim=a.steps * dt,
                       n_hab=n_hab.tolist(), w_ax=w_ax.tolist(),
                       a_ax=a_ax.tolist(),
                       # ★★ 引擎版本必须逐次记录 —— 否则不同臂之间会被"引擎版本"
                       #    这个隐藏变量污染（本轮已踩过一次：ns 扫描跑在 pre-guard
                       #    引擎上，长跑跑在 post-guard 引擎上，结果不可直接比）。
                       sha_windowB_surface=_sha256(
                           os.path.join(_HERE, 'windowB_surface.py')),
                       sha_windowB_par=_sha256(os.path.join(_HERE, 'windowB_par.py')),
                       sha_self=_sha256(os.path.abspath(__file__))),
                  _m, ensure_ascii=False, indent=1)
    P0 = None
    t_sim, wall0 = 0.0, time.time()
    tstep = []
    for it in range(0, a.steps + 1):
        if it > 0:
            tw = time.time()
            g.advance(dt, **KW)
            tstep.append(time.time() - tw)
            t_sim += dt
        if it % a.every == 0 or it == a.steps:
            reg = g.region()
            vmap = {k + 1: 1 for k in range(nv)}
            mm = BM.measure_state(reg, dx, n_hab, w_ax, a_ax, vmap)
            pm = mm['f3_pos_n']
            if P0 is None and np.isfinite(pm):
                P0 = pm
            row = dict(
                step=it, t_s=round(t_sim, 12), wall_s=round(time.time() - wall0, 2),
                dt=dt, V0=mm['vol_0'], V1=mm['vol_1'],
                V2=mm.get('vol_2', float('nan')),
                Vt=mm['vol_1'] + mm.get('vol_2', 0.0),
                nf3=mm['f3_faces'], f3_area_m2=mm['f3_area'],
                f3_area_stair=mm['f3_area_stair'], f3_pos_m=pm,
                f3_pos_dx=((pm - P0) / dx if (np.isfinite(pm) and P0 is not None)
                           else float('nan')),
                f3_std_m=mm['f3_std_n'], nslab_n=mm['nslab_n'],
                nf3_col=mm['nf3_col'], runs=mm['runs'].replace(',', '/'),
                ncomp_1=mm['ncomp_1'], ncomp_2=mm.get('ncomp_2', -1),
                n_1=mm['n_1'], w_1=mm['w_1'], a_1=mm['a_1'],
                n_2=mm.get('n_2', float('nan')), w_2=mm.get('w_2', float('nan')),
                a_2=mm.get('a_2', float('nan')),
                box_touch=int(mm['box_touch']),
                finite=int(np.all(np.isfinite(g.phi))))
            cw.writerow([row[c] for c in COLS]); csvf.flush()
            if it % a.snap_every == 0 or it == a.steps:
                np.savez_compressed(
                    os.path.join(outdir, 'snap_%05d.npz' % it),
                    phi=g.phi.astype(np.float32), region=reg,
                    step=it, nv=nv, gamma=gamma, N=N, L=L,
                    n_hab=n_hab, w_ax=w_ax, a_ax=a_ax, gap_nm=a.gap_nm,
                    norm_smooth=a.norm_smooth,
                    plate=np.array([plate['L'], plate['W'], plate['T']]))
            print('  [%4d] V1=%.4f V2=%.4f µm³ | nslab=%d nf3col=%d runs=%-14s | '
                  'F3面=%-5d 面积=%.4f µm² | Δpos=%+7.3f dx std=%5.1f nm | '
                  'nc1=%-5d n/w/a=%.0f/%.0f/%.0f nm | 壁=%d | %.2fs/步'
                  % (it, mm['vol_1'] * 1e18,
                     (mm.get('vol_2', float('nan')) * 1e18), mm['nslab_n'],
                     mm['nf3_col'], mm['runs'], mm['f3_faces'],
                     mm['f3_area'] * 1e12,
                     (row['f3_pos_dx'] if np.isfinite(row['f3_pos_dx']) else float('nan')),
                     (mm['f3_std_n'] * 1e9 if np.isfinite(mm['f3_std_n']) else float('nan')),
                     mm['ncomp_1'], mm['n_1'] * 1e9, mm['w_1'] * 1e9, mm['a_1'] * 1e9,
                     int(mm['box_touch']),
                     (np.mean(tstep[-a.every:]) if tstep else 0.0)))
    csvf.close()
    s = np.genfromtxt(os.path.join(outdir, 'series.csv'), delimiter=',',
                      names=True, dtype=None, encoding='utf-8')
    print('-' * 100)
    d = np.atleast_1d(s['f3_pos_dx'])
    ok = np.isfinite(d)
    print('  判决 %-9s：nslab_n %d→%d ；ncomp_1 %d→%d ；F3 面 %d→%d ；'
          't_sim=%.3e s ；Δpos = %s dx'
          % (name, s['nslab_n'][0], s['nslab_n'][-1], s['ncomp_1'][0],
             s['ncomp_1'][-1], s['nf3'][0], s['nf3'][-1], tsim,
             ('%+.3f' % d[ok][-1]) if ok.any() else 'NaN（从不接触）'))
    return dict(name=name, outdir=outdir, P0=P0, s=s, tsim=tsim, dt=dt,
                dx=dx, nv=nv, gamma=gamma, ms=a.norm_smooth)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--L-um', type=float, default=4.0)
    ap.add_argument('--steps', type=int, default=120)
    ap.add_argument('--every', type=int, default=10)
    ap.add_argument('--snap-every', type=int, default=40)
    ap.add_argument('--norm-smooth', type=int, default=4)
    ap.add_argument('--beta-h', type=float, default=3.5)
    ap.add_argument('--beta-w', type=float, default=2.3)
    ap.add_argument('--gap-nm', type=float, default=0.0)
    ap.add_argument('--plate-L', type=float, default=2400.0)
    ap.add_argument('--plate-W', type=float, default=640.0)
    ap.add_argument('--plate-T', type=float, default=250.0)
    ap.add_argument('--out', default='_exp/_bk_f3smoke')
    ap.add_argument('--tag', default=time.strftime('%m%d_%H%M%S'),
                    help='输出子目录后缀；**默认带时间戳 ⇒ 不覆盖历史数据**')
    ap.add_argument('--arms', default='main,ctrl_pos,ctrl_neg')
    ap.add_argument('--probe-only', action='store_true')
    a = ap.parse_args()
    argmin_normal_zero_strain_probe()
    if a.probe_only:
        return 0
    plate = dict(L=a.plate_L, W=a.plate_W, T=a.plate_T)
    # 臂表：(变体复制?, nv, gamma, norm_smooth, 说明)
    ARMS = {
        'main':     (True, 2, 0.15, 4, '主臂（R1 生产 m=4）'),
        'ns0':      (True, 2, 0.15, 0, 'm=0（无平滑）'),
        'ns1':      (True, 2, 0.15, 1, 'm=1'),
        'ns2':      (True, 2, 0.15, 2, 'm=2'),
        'ctrl_pos': (True, 2, 100.0, 4, '量具正对照（γ=100）'),
        'ctrl_neg': (False, 1, 0.15, 4, '量具负对照（nv=1 单场）'),
    }
    res = {}
    for name in [x for x in a.arms.split(',') if x]:
        if name not in ARMS:
            raise SystemExit('未知臂 %r（可选 %s）' % (name, sorted(ARMS)))
        dup, nv, gam, ms, why = ARMS[name]
        a.norm_smooth = ms
        print('\n>>> 臂 %s：%s' % (name, why))
        res[name] = run_arm(name, a, gam, nv, dup, plate, a.out)
    print()
    print('=' * 108)
    print('汇总（Δpos 单位 = Δx = %.1f nm）' % (a.L_um * 1e6 / a.N))
    print('=' * 108)
    print('  %-9s %-8s %-4s %-9s %-9s %-9s %-9s' %
          ('臂', 'γ', 'm', 'nslab初末', 'Δpos末', '解析上界', 'nc1末'))
    for k, r in res.items():
        s = r['s']
        d = s['f3_pos_dx']; ok = np.isfinite(d)
        dd = float(d[ok][-1]) if ok.any() else float('nan')
        pred = (MOB * np.exp(-a.beta_h) * r['gamma'] * (2.0 / r['dx'])
                * r['tsim']) / r['dx']
        print('  %-9s %-8.5g %-4d %-9s %+9.3f %+9.3f %-9d'
              % (k, r['gamma'], r['ms'], '%d→%d' % (s['nslab_n'][0], s['nslab_n'][-1]),
                 dd, pred, s['ncomp_1'][-1]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
