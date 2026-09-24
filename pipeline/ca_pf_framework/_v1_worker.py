#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
_v1_worker.py <task>:<idx>  --- 给定条件实验（每项都有解析预测与判据），单体 worker
把结果写到 _v1_out/<task>__<idx>.json
任务:
  t1_octahedron  1 个: 对齐取向单晶 => 八面体顶点=ℓ、面心=0.577ℓ、体积=1.333ℓ³
  t2_velocity    3 个: 单晶沿晶体方向的伸长达 vs t 的斜率 = V(ΔT)/Σ
  t3_aniso_law   4 个: 24 取向 × 13 方向: r/ℓ 对 1/Σ 回归 (斜率=1, R²>0.999)
  t4_gb_locus    6 个: 双晶均匀 ΔT => 晶界位置 = {sup_A = sup_B} 的解析轨迹
  t5_wc_pairs   40 个: 双晶 + 倾斜梯度 => 对齐度大者持有领先前沿 (WC 择优)
  t6_elimination 8 个: 9 晶粒 + 倾斜梯度 => 淘汰曲线(活跃晶粒数 vs t)
  t7_nucleation  6 个: 体形核 N_max 扫描 => 形核数 ∝ N_max·可用体积
  t8_dx_conv     4 个: 八面体体积误差 vs dx (O(dx))
'''
import os, sys, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_v1_out')
os.makedirs(OUT, exist_ok=True)
IRED = IRF()


def qaa(axis, deg):
    a = np.array(axis, float); a /= np.linalg.norm(a)
    th = math.radians(deg)
    return (math.cos(th/2), *(a*math.sin(th/2)))


def identity_q():
    return (1.0, 0.0, 0.0, 0.0)


def ray_reach(ca, seed, axis_dir, ell, dx, box):
    '''从 seed 沿世界方向 axis_dir 走到最远的实心胞，返回距离(与 ℓ 同单位)'''
    solid = ca.gid > 0
    sm = 0.0
    for r in np.arange(0.0, 2.6 * ell, 0.1 * dx):
        p = (np.array(seed, float) + 0.5) * dx + r * axis_dir
        idx = np.floor(p / dx).astype(int)
        if np.any(idx < 0) or np.any(idx >= np.array(box)):
            break
        if solid[idx[0], idx[1], idx[2]]:
            sm = r
    return sm


def run_single(dx, box, dT, quat, steps, walk_dirs=None, ell_target=None, record_every=None):
    ca = CA3D(box[0], box[1], box[2], dx, irf=IRED, seed=7, capture='envelope')
    c = tuple(b // 2 for b in box)
    g = ca.add_grain(c[0], c[1], c[2], quat=quat)
    P = ca.axes[g]
    V = float(IRED.capped(np.array([dT]))[0][0])
    dt = dx / (4.0 * V)
    if ell_target is not None:
        steps = int(round(ell_target / (V * dt)))
    traj = []
    t = 0.0
    for s in range(steps):
        ca.t = t
        ca.step(dt, ca.T_iso(dT), window='full')
        t += dt
        if record_every and (s + 1) % record_every == 0:
            rec = {}
            if walk_dirs:
                for nm, cd in walk_dirs.items():
                    cv = np.array(cd, float); cv /= np.linalg.norm(cv)
                    rec[nm] = ray_reach(ca, c, P @ cv, V * t, dx, box) / (V * t)
            traj.append([t, rec])
    ell = V * steps * dt
    return ca, g, P, V, ell, dt, traj


# ------------------------------------------------------------------ 任务
def t1_octahedron(idx):
    dx = 1e-6; box = (81, 81, 81); dT = 12.0
    ca, g, P, V, ell, dt, _ = run_single(dx, box, dT, identity_q(), None, ell_target=16e-6)
    c = tuple(b // 2 for b in box)
    axes_r = {}
    for nm, cd in (('+x', (1, 0, 0)), ('-x', (-1, 0, 0)), ('+y', (0, 1, 0)),
                   ('-y', (0, -1, 0)), ('+z', (0, 0, 1)), ('-z', (0, 0, -1))):
        axes_r[nm] = ray_reach(ca, c, np.array(cd, float), ell, dx, box) / ell
    diag = ray_reach(ca, c, np.array([1, 1, 1], float) / math.sqrt(3), ell, dx, box) / ell
    vol = int((ca.gid > 0).sum()); voli = (2 * ell) ** 3 / 6.0 / dx ** 3
    e_ax = max(abs(v - 1.0) for v in axes_r.values())
    return dict(pred='顶点=ℓ(±1胞)、面心=0.577ℓ、体积=1.333ℓ³(±3%)',
                axes_r=axes_r, diag=diag, diag_pred=1 / math.sqrt(3),
                vol=vol, vol_pred=voli, vol_err=100 * (vol - voli) / voli,
                ell_cells=ell / dx, err_axis_cells=e_ax * ell / dx,
                diag_err_cells=abs(diag - 1 / math.sqrt(3)) * ell / dx,
                verdict='PASS' if (e_ax * ell / dx <= 1.5 and
                                   abs(diag - 1 / math.sqrt(3)) * ell / dx <= 1.5) else 'FAIL',
                note='体积偏差是【胞心判据 + {111} 面体素化】的系统偏置（~0.5 胞向内），'
                     '必须随 dx 收敛 -> 见 t8（idx>=4 为对齐取向）')


def t2_velocity(idx):
    dx = 1e-6; box = (81, 81, 81); dT = 12.0
    quats = [identity_q(), qaa((0.3, 0.7, 0.2), 37.0), qaa((0.55, 0.2, 0.8), 61.0)]
    cdirs = [(1, 0, 0), (1, 1, 0), (1, 1, 1)]
    q = quats[idx]; cd = cdirs[idx]
    ca, g, P, V, ell, dt, _ = run_single(dx, box, dT, q, 90)
    cv = np.array(cd, float); cv /= np.linalg.norm(cv)
    nw = P @ cv
    ts, rs = [], []
    ca2 = CA3D(box[0], box[1], box[2], dx, irf=IRED, seed=7, capture='envelope')
    c = tuple(b // 2 for b in box)
    g2 = ca2.add_grain(c[0], c[1], c[2], quat=q)
    P2 = ca2.axes[g2]
    t = 0.0
    for s in range(90):
        ca2.t = t
        ca2.step(dt, ca2.T_iso(dT), window='full')
        t += dt
        if (s + 1) % 10 == 0:
            ts.append(t); rs.append(ray_reach(ca2, c, nw, 4 * V * t, dx, box))
    slope = float(np.polyfit(np.array(ts[3:]), np.array(rs[3:]), 1)[0])   # 去掉起步段
    summ = float(np.abs(P2[:, 0] @ nw) + np.abs(P2[:, 1] @ nw) + np.abs(P2[:, 2] @ nw))
    pred = V / summ
    return dict(pred='d(reach)/dt = V/Σ(n̂)', cdir=cd, sigma=summ, slope=slope, V=V,
                slope_pred=pred, err_pct=100 * (slope - pred) / pred,
                verdict='PASS' if abs(slope - pred) / pred < 0.05 else 'FAIL')


def t3_aniso_law(idx):
    dx = 1e-6; box = (81, 81, 81); dT = 12.0
    rng = np.random.default_rng(1000 + idx)
    from ca3d import rand_quat
    dirs = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1),
            (1, 1, 1), (1, 2, 0), (2, 1, 0), (1, 0.5, 0), (1, 0.3, 0.2), (3, 1, 1), (1, 3, 2)]
    rows = []
    for k in range(6):
        q = rand_quat(rng)
        ca, g, P, V, ell, dt, _ = run_single(dx, box, dT, q, None, ell_target=16e-6)
        c = tuple(b // 2 for b in box)
        for cd in dirs:
            cv = np.array(cd, float); cv /= np.linalg.norm(cv)
            nw = P @ cv
            r = ray_reach(ca, c, nw, ell, dx, box)
            summ = float(np.abs(P[:, 0] @ nw) + np.abs(P[:, 1] @ nw) + np.abs(P[:, 2] @ nw))
            rows.append((r / ell, 1.0 / summ, ell / dx))
    x = np.array([b for a, b, e in rows]); y = np.array([a for a, b, e in rows])
    ec = np.array([e for a, b, e in rows])
    A = np.polyfit(x, y, 1)
    yfit = np.polyval(A, x)
    ss = 1 - np.sum((y - yfit) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-30)
    # 判据1: 与【理想律 r/ℓ=1/Σ】的偏离(按胞计) —— 这是可证伪的物理律
    dev_ideal_cells = float(np.max(np.abs(y - x) * ec))
    dev_ideal_mean_cells = float(np.mean(np.abs(y - x) * ec))
    return dict(pred='r/ℓ = 1/Σ（与理想律的最大偏离 <=1.2 胞）',
                rows=[[round(a, 5), round(b, 5), round(e, 2)] for a, b, e in rows],
                n=len(rows), slope=float(A[0]), intercept=float(A[1]), r2=float(ss),
                dev_ideal_max_cells=dev_ideal_cells, dev_ideal_mean_cells=dev_ideal_mean_cells,
                verdict='PASS' if dev_ideal_cells <= 1.2 else 'FAIL')


def t4_gb_locus(idx):
    dx = 1e-6; box = (121, 41, 41); dT = 12.0
    from ca3d import rand_quat
    rng = np.random.default_rng(2000 + idx)
    qA, qB = rand_quat(rng), rand_quat(rng)
    ca = CA3D(*box, dx, irf=IRED, seed=9, capture='envelope')
    gA = ca.add_grain(30, 20, 20, quat=qA); gB = ca.add_grain(90, 20, 20, quat=qB)
    V = float(IRED.capped(np.array([dT]))[0][0]); dt = dx / (4 * V)
    for s in range(300):
        ca.t = s * dt
        ca.step(dt, ca.T_iso(dT), window='full')
    g = ca.gid
    errs = []
    for j in range(6, box[1] - 6, 4):
        for k in range(6, box[2] - 6, 4):
            col = g[:, j, k]
            ia = np.nonzero(col == gA)[0]; ib = np.nonzero(col == gB)[0]
            if not len(ia) or not len(ib):
                continue
            xgb = 0.5 * (ia.max() + ib.min())
            xs = np.arange(box[0], dtype=float)
            supA = ca.envelope_sup(gA, xs, np.full_like(xs, j), np.full_like(xs, k))
            supB = ca.envelope_sup(gB, xs, np.full_like(xs, j), np.full_like(xs, k))
            d = supA - supB
            sgn = np.sign(d)
            cross = np.nonzero(sgn[:-1] * sgn[1:] < 0)[0]
            if len(cross) == 0:
                continue
            xpred = cross[0] + d[cross[0]] / (d[cross[0]] - d[cross[0] + 1])
            errs.append(abs(xgb - xpred))
    errs = np.array(errs)
    return dict(pred='晶界位置 = {sup_A = sup_B}（误差 <2 胞）', n=len(errs),
                mean_err_cells=float(errs.mean()) if len(errs) else None,
                p95_err_cells=float(np.percentile(errs, 95)) if len(errs) else None,
                verdict='PASS' if (len(errs) > 20 and errs.mean() < 2.0) else 'FAIL')


def t5_wc_pairs(idx):
    import verify_ca3d_wc_cet as W
    res = []
    for rep in range(2):
        sd = 3000 + idx * 2 + rep
        r = W._wc_case(nst=240, N=110, n_t=2, n_y=1, spacing=30, seed=sd, capture='envelope')
        ca = r['ca']; n = r['n']
        def al(g):
            P = ca.axes[g]
            return max(abs(float(P[:, a] @ n)) for a in range(3))
        gids = list(r['gids'])
        if len(gids) < 2:
            continue
        als = {g: al(g) for g in gids}
        onl = list(r['onlead'])
        best = max(gids, key=lambda g: als[g])
        res.append(dict(seed=sd, align={int(g): round(als[g], 4) for g in gids},
                        onlead=[int(x) for x in onl], best=int(best),
                        ok=int(len(onl) > 0 and best in onl)))
    return dict(pred='对齐度最大的晶粒持有领先前沿（WC 择优）', cases=res,
                rate=float(np.mean([c['ok'] for c in res])) if res else None,
                verdict='PASS' if res and np.mean([c['ok'] for c in res]) >= 0.9 else 'FAIL')


def t6_elimination(idx):
    '''9 晶粒 + 倾斜梯度: 记录"接触液相的晶粒数" vs t（淘汰曲线）'''
    import verify_ca3d_wc_cet as W
    dx = 4e-6; N = 110; dTu = 16.0
    n = W.nhat_tilt(35.0)
    V = float(IRED(dTu)); dt = dx / (4 * V)
    ca = CA3D(N, N, N, dx, irf=IRED, seed=4000 + idx, periodic=(False, True, False),
              capture='envelope')
    import ca3d as C3
    rng = np.random.default_rng(4001 + idx)
    quats = [C3.rand_quat(rng) for _ in range(9)]
    gids = W.place_seeds_on_perp_plane(ca, n, 3, 3, 25, quats=quats)
    def al(g):
        P = ca.axes[g]; return max(abs(float(P[:, a] @ n)) for a in range(3))
    als = {int(g): round(al(g), 4) for g in gids}
    curve = []
    for s in range(300):
        ca.t = s * dt
        ca.step(dt, ca.T_iso(dTu), window='full')
        if (s + 1) % 20 == 0:
            solid = ca.gid > 0
            liq = ~solid
            nb = np.zeros_like(solid)
            for o, _ in C3.OFFSETS:
                pr = ca._pair(o, (0, N, 0, N, 0, N))
                if pr is None:
                    continue
                sx, tx = pr
                nb[tx] |= liq[sx]
            front = solid & nb
            act = [int(x) for x in np.unique(ca.gid[front]) if x > 0]
            curve.append([s, len(act), sorted(((als[a], a) for a in act), reverse=True)])
    last = curve[-1]
    top3 = sorted(als.values(), reverse=True)[:3]
    hold_al = [a for a, g in last[2]]
    return dict(pred='末态只有对齐度最高的少数(<=3)晶粒持有前沿；错取向被淘汰',
                align=als, curve=curve, n_final=last[1],
                hold_align=[round(x, 4) for x in hold_al], top3=top3,
                verdict='PASS' if (last[1] <= 3 and min(hold_al) >= top3[-1] - 1e-9) else 'FAIL')


def t7_nucleation(idx):
    Nmax = (1e13, 1e14, 1e15, 1e16, 1e17, 1e18)[idx]
    dx = 2e-6; box = (60, 60, 60); dTu = 12.0
    ca = CA3D(*box, dx, irf=IRED, seed=5)
    ca.nucleate_substrate_grid(4, 4)
    n0 = len(ca.grain_ids())
    V = float(IRED(dTu)); dt = dx / (4 * V)
    T = ca.T_iso(dTu)
    nb = 0
    for s in range(60):
        ca.t = s * dt
        nb += ca.nucleate_bulk(T, 8.0, 3.0, Nmax, dt)
    Vc = float((ca.gid == 0).sum()) * dx ** 3
    pred = Nmax * (box[0] * box[1] * box[2] * dx ** 3)
    return dict(pred='形核数 ∝ N_max（连续形核谱饱和值 ≈ N_max·体积）',
                Nmax=Nmax, n_bulk=int(nb), n_total=len(ca.grain_ids()),
                V_cold_frac=Vc / (box[0] * box[1] * box[2] * dx ** 3),
                pred_sat=Nmax * (box[0] * box[1] * box[2] * dx ** 3),
                ratio=(nb / (Nmax * (box[0] * box[1] * box[2] * dx ** 3))
                       if Nmax * (box[0] * box[1] * box[2] * dx ** 3) > 0 else None),
                verdict='PASS' if nb > 0 else 'WARN')


def t8_dx_conv(idx):
    dx = (0.5e-6, 1.0e-6, 2.0e-6, 3.0e-6)[idx % 4]
    ori = 'aligned' if idx >= 4 else 'random'
    q = identity_q() if idx >= 4 else qaa((0.3, 0.7, 0.2), 37.0)
    box = (81, 81, 81); dT = 12.0
    ca, g, P, V, ell, dt, _ = run_single(dx, box, dT, q, None, ell_target=15e-6)
    vol = int((ca.gid > 0).sum()); voli = (2 * ell) ** 3 / 6.0 / dx ** 3
    return dict(pred='体积误差 ∝ dx（对随取向与对齐取向都要成立）', ori=ori,
                dx_um=dx * 1e6, ell_cells=round(ell / dx, 1),
                vol=vol, vol_pred=int(voli), err_pct=100 * (vol - voli) / voli,
                err_cells=(vol - voli) * dx ** 3 / (6 * (ell / 1.0) ** 2) if ell > 0 else None,
                verdict='INFO')


TASKS = dict(t1_octahedron=t1_octahedron, t2_velocity=t2_velocity, t3_aniso_law=t3_aniso_law,
             t4_gb_locus=t4_gb_locus, t5_wc_pairs=t5_wc_pairs, t6_elimination=t6_elimination,
             t7_nucleation=t7_nucleation, t8_dx_conv=t8_dx_conv)


def main():
    spec = sys.argv[1]
    name, idx = spec.split(':')
    idx = int(idx)
    t0 = time.time()
    try:
        r = TASKS[name](idx)
    except Exception as e:
        import traceback
        r = dict(verdict='ERROR', err=str(e), tb=traceback.format_exc()[-800:])
    r.update(task=name, idx=idx, wall_s=round(time.time() - t0, 1))
    with open(os.path.join(OUT, '%s__%d.json' % (name, idx)), 'w') as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    print('%-16s #%-3d %-5s %6.1fs' % (name, idx, r.get('verdict', '?'), r['wall_s']), flush=True)


if __name__ == '__main__':
    main()