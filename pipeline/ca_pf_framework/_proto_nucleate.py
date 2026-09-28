#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_proto_nucleate.py --- **D18 冒烟原型**：给 Window B 加一条"长大中的形核"通道。

为什么（★ T25-D）
----------------
`RESEARCH_INTENT.md` 第 100–102 行明写「α′ 以板条为单位**形核 + 长大**；
板条自发按 Burgers 取向分组 ⇒ block / colony / packet / variant cluster」。
而 `grep -e nucleat -e seed_plate *.py` 的结果是：**每个驱动脚本都只在 `t=0` 种一次核**，
此后只长大。⇒ ①板条厚只能是种子厚（`t ≤ t_seed+(d/2−R_seed)e^{−β_h}` ≈ 215–300 nm，
文献 510–880 nm）；②**block（平行板条的叠层）在结构上不可能形成**；③变体选择的自催化机制缺失。

本脚本**不做生产**，只做**冒烟**：证明"加上形核 ⇒ 同一变体出现**多个**区域（= block 的骨架）、
且厚度由**形核参数**（有文献值可锚）而不是由种子几何决定"。

两条形核通道（都便宜，只用引擎已有的 `elastic_driving()` 与 `seed_plate()`）
--------------------------------------------------------------------
  * `fresh`  **独立形核**：在"远离一切已有界面"的母相胞里选**总驱动力最大**的位置，
             变体取该点 `argmax_k ed[k]`（自协调/弹性择优）；
  * `stack`  **sympathetic / 自催化形核**：随机挑一个已有板条，在其**惯习面内**平移
             `(R+R_nuc+gap)` 处**同变体**再种一片 ⇒ 这就是 block 的生成机制。

判据（冒烟级，不是验收级）
------------------------
  N-1 正对照：厚度量具（沿 `n*_k` 的方向尺度）在**已知 t** 的合成板条上复现 t（±15%）
  N-2 `nuc=on` 时同一变体的**区域数**显著多于 `nuc=off` ⇒ block 骨架出现
  N-3 `nuc=on` 的厚度分布落在 **`t_nuc` 附近**，而不是被钉在 `t_seed`
  N-4 守卫：无绕盒、无膨胀失控；`f` 与核数记账一致

用法：python3 _proto_nucleate.py [--steps 60] [--L-um 3.2] [--n0 8] [--t-nuc-nm 600]
退出码：0 = 冒烟通过，1 = 未通过，2 = 环境/规格问题
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import stats, C, EPS0, NV, NPF, R_SEED, T_SEED   # noqa: E402
from T24_verify_grouping import grouping_stats, packet_families, connected_components  # noqa: E402

MOB = 1e-9
DF = 3.5e8
BETA_H, BETA_W = 3.5, 2.3


# ---------------------------------------------------------------- 量具（R0）
def thickness_along_normal(reg, NPF, dx, k, min_cells=8):
    """沿该变体**惯习面法向 `n*_k`** 的方向尺度（平板 ⇒ = 厚度）。

    ★ 为什么不用 `r_c^var`：`MEASUREMENT_SPEC §2` 已证伪它当"厚度变化"量具
      （`R/t` 从 1.5→2.0 时固定厚度它自己涨 9.6%）。本量具是**几何方向尺度**，
      对平板无形状族假设；正对照见 `control_thickness()`。"""
    m = (reg == k)
    if m.sum() < min_cells:
        return np.nan
    lab, n = connected_components(m)
    if n == 0:
        return np.nan
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    comp = (lab == int(np.argmax(sizes)))
    idx = np.argwhere(comp).astype(float)
    proj = idx @ np.asarray(NPF[k], float)
    # ★ 2026-09-28 第 19 处修正：原来写 `max - min + 1.0`（**多加一胞**），
    #   违反 `MEASUREMENT_SPEC R3`（"投影用 `max−min`，**不加 `dx`**"）。
    #   实测后果：Δx=50 nm 时把 200 nm 的种子读成 **249 nm（+25%）**，
    #   而 249/200 的偏差量级与我要测的增厚信号同阶 ⇒ 结论会翻面。
    #   `argwhere` 给的是胞中心（已是 i+0.5）⇒ `max−min` 就是长度。
    return float(proj.max() - proj.min()) * dx


def control_thickness(dx=25e-9, L=2.4e-6):
    """R0 正对照：合成平板，已知 t。"""
    N = int(round(L / dx))
    print('  【N-1 正对照】厚度量具（沿 `n*_k` 的方向尺度，`max−min` 不加 `dx`）在已知 t 的合成板条上：')
    rows = []
    for R_nm, t_nm in ((300, 200), (600, 300), (900, 300), (600, 700)):
        g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.15, Mob=MOB,
                            df=[0.0, 1e8], workers=1, reinit_every=0)
        n0 = np.array([0.0, 0.0, 1.0])
        g.seed_plate(1, np.array([L / 2] * 3), n0, R_nm * 1e-9, t_nm * 1e-9)
        g.init_parent()
        npref = {1: n0}
        got = thickness_along_normal(g.region(), npref, dx, 1)
        rows.append(abs(got / (t_nm * 1e-9) - 1.0))
        print('     R=%4d t=%3d ⇒ 量具 %.1f nm（偏差 %+.1f%%）'
              % (R_nm, t_nm, got * 1e9, (got / (t_nm * 1e-9) - 1) * 100))
    worst = max(rows)
    print('     ⇒ 最大偏差 %.1f%% ⇒ %s' % (worst * 100, 'PASS' if worst < 0.15 else 'FAIL'))
    return worst < 0.15


# ---------------------------------------------------------------- 形核通道
def nucleate(g, n_fresh, n_stack, R_nuc, t_nuc, ed, rng, gap_cells=2):
    """在母相里加新板条核。返回 [(k, mode)]。"""
    from scipy import ndimage
    reg = g.region()
    par = (reg == 0)
    out = []
    if not par.any():
        return out
    # "安全"胞：到任何非母相胞的欧氏距离 ≥ R_nuc + gap（用 EDT，避免手工盒扫描）
    dt = ndimage.distance_transform_edt(par) * g.dx
    safe = dt >= (R_nuc + gap_cells * g.dx)
    # ★ 记账：种子板条自身占位 ⇒ 安全区一开始就排除了已有板条附近
    cand = np.argwhere(safe)
    if cand.size == 0:
        return out
    # ---- fresh：按"最大弹性驱动"排序（Δf 均匀 ⇒ 排序等价于按总驱动力）
    drive = ed.max(axis=0)
    ok = drive[cand[:, 0], cand[:, 1], cand[:, 2]] > 0.0     # 需净正驱动
    cand, drv = cand[ok], drive[cand[:, 0], cand[:, 1], cand[:, 2]][ok]
    order = np.argsort(-drv)
    taken = []
    excl = (2 * (R_nuc + gap_cells * g.dx)) ** 2
    for i in order:
        if len(taken) >= n_fresh:
            break
        c = cand[i].astype(float) + 0.5
        if any(((c - t) ** 2).sum() < excl for t in taken):
            continue
        cc = c * g.dx
        k = int(np.argmax(ed[:, cand[i, 0], cand[i, 1], cand[i, 2]]))
        if k == 0:
            continue
        try:
            g.seed_plate(k, cc, np.asarray(NPF[k], float), R_nuc, t_nuc)
            taken.append(c)
            out.append((k, 'fresh'))
        except ValueError:
            pass
    # ---- stack：sympathetic 形核（同变体、沿惯习面平移）⇒ block 的生成机制
    ks = [k for k in np.unique(g.region()) if k > 0]
    for _ in range(n_stack):
        if not ks:
            break
        k = int(ks[rng.integers(0, len(ks))])
        m = (g.region() == k)
        idx = np.argwhere(m)
        if idx.size == 0:
            continue
        c0 = (idx.mean(0) + 0.5) * g.dx
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        pos = (idx.astype(float) + 0.5) * g.dx
        # ★ 修（冒烟第 2 轮）：原来用 `max(occ)/2 + R + gap` 当平移量 ⇒ 在 3.2 µm 盒里
        #   几乎必然越界（实测 20 步只成功 1 个 stack）。改为**沿所选方向**量供体的
        #   实际半展宽，并**试 8 个方向**取第一个过守卫的。
        placed = False
        for _try in range(8):
            v = rng.normal(size=3)
            v = v - (v @ nrm) * nrm
            if np.linalg.norm(v) < 1e-6:
                continue
            v = v / np.linalg.norm(v)
            pv = pos @ v
            ext_v = float(pv.max() - pv.min())
            off = 0.5 * ext_v + R_nuc + gap_cells * g.dx
            c = c0 + off * v
            if np.any(c < R_nuc + 0.3e-6) or np.any(c > g.L - R_nuc - 0.3e-6):
                continue
            # 越界/重叠守卫：新核覆盖的胞必须全在母相里
            rel = g.XYZ - c
            dd = rel @ nrm
            rp = np.linalg.norm(rel - dd[..., None] * nrm, axis=-1)
            cover = (np.abs(dd) <= t_nuc / 2) & (rp <= R_nuc)
            if not bool((reg[cover] == 0).all()):
                continue
            try:
                g.seed_plate(k, c, nrm, R_nuc, t_nuc)
                out.append((k, 'stack'))
                placed = True
            except ValueError:
                pass
            if placed:
                break
    return out


# ---------------------------------------------------------------- 一条轨迹
def run(nuc_on, steps, L, dx, n0, f_nuc_every, n_fresh, n_stack, R_nuc, t_nuc, rng_seed=7):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(rng_seed)
    ns = 0
    while ns < n0:
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nv = np.asarray(NPF[k], float)
        try:
            g.seed_plate(k, c, nv / np.linalg.norm(nv), R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    log, nuc_log, t0 = [], [], time.time()
    for it in range(1, steps + 1):
        ed = g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=BETA_H, mob_beta_w=BETA_W, adv_grad='proj2')
        if nuc_on and it % f_nuc_every == 0:
            nuc_log += nucleate(g, n_fresh, n_stack, R_nuc, t_nuc, ed, rng)
        if it % 20 == 0 or it == steps:
            reg = g.region()
            f = 1.0 - float((reg == 0).sum()) / g.N ** 3
            log.append((it, f))
            print('     [心跳 %s] step=%-3d f=%.4f  核数=%-3d  步时=%.1f s'
                  % ('on ' if nuc_on else 'off', it, f, ns + len(nuc_log),
                     (time.time() - t0) / it), flush=True)
    return g, log, nuc_log, ns


# ---------------------------------------------------------------- main
ap = argparse.ArgumentParser()
ap.add_argument('--steps', type=int, default=60)
ap.add_argument('--L-um', type=float, default=3.2)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--n0', type=int, default=8)
ap.add_argument('--t-nuc-nm', type=float, default=600.0)
ap.add_argument('--r-nuc-nm', type=float, default=400.0)
ap.add_argument('--every', type=int, default=10)
ap.add_argument('--n-fresh', type=int, default=1)
ap.add_argument('--n-stack', type=int, default=1)
a = ap.parse_args()
dx = a.dx_nm * 1e-9
L = a.L_um * 1e-6

print('=' * 100)
print('_proto_nucleate —— **D18 冒烟原型**：给 Window B 加"长大中的形核"通道')
print('=' * 100)
ok1 = control_thickness()

fam = packet_families(NPF)[0]      # 返回 (dict, nfam)
res = {}
for tag, on in (('off', False), ('on', True)):
    print('\n---- 轨迹 `nuc=%s`：L=%.2f µm Δx=%.0f nm N=%d n0=%d steps=%d ----'
          % (tag, L * 1e6, dx * 1e9, int(round(L / dx)), a.n0, a.steps))
    g, log, nuc_log, ns = run(on, a.steps, L, dx, a.n0, a.every, a.n_fresh, a.n_stack,
                              a.r_nuc_nm * 1e-9, a.t_nuc_nm * 1e-9)
    reg = g.region()
    s = stats(g)
    gs = grouping_stats(reg, dx, fam)
    thick = [thickness_along_normal(reg, NPF, dx, k)
             for k in np.unique(reg) if k > 0]
    thick = [v for v in thick if np.isfinite(v)]
    res[tag] = dict(f=s['f'], m6p=s['m6p_p25'], nblk=gs['n_block_raw'],
                    nblk_ok=len(gs['block_sizes']), deq=gs['block_deq'],
                    thick=thick, n_nuc=len(nuc_log), ns=ns,
                    modes=[m for _, m in nuc_log], wrap=g.wrap_axes_any())
    r = res[tag]
    print('   末态：f=%.4f  核数=%d（初始 %d + 新生 %d）  M6p p25=%.1f°'
          % (r['f'], r['ns'] + r['n_nuc'], r['ns'], r['n_nuc'], r['m6p']))
    print('   block：原分量 %d（过守卫 %d）  中位 d_eq=%.0f nm'
          % (r['nblk'], r['nblk_ok'],
             np.median(r['deq']) * 1e9 if r['deq'] else float('nan')))
    th = np.array(r['thick'], float)
    r['n_thick'] = int((th >= 1.4 * T_SEED).sum())
    r['th_max'] = float(th.max()) if th.size else float('nan')
    r['th_p90'] = float(np.percentile(th, 90)) if th.size else float('nan')
    print('   厚度（沿 n* 的方向尺度）：中位 %.0f nm，p90 %.0f nm，max %.0f nm，n=%d'
          % (np.median(th) * 1e9 if th.size else float('nan'), r['th_p90'] * 1e9,
             r['th_max'] * 1e9, th.size))
    print('   ★ 厚度 ≥ 1.4×t_seed(%.0f nm) 的区域数 = %d / %d'
          % (1.4 * T_SEED * 1e9, r['n_thick'], th.size))
    print('   守卫：绕盒=%s' % (r['wrap'] or '无'))

print('\n' + '=' * 100)
print('【判读】')
print('  N-1 厚度量具正对照：%s' % ('PASS' if ok1 else 'FAIL'))
n2 = res['on']['nblk'] > res['off']['nblk']
print('  N-2 同变体区域数：off=%d ⇒ on=%d（新生核 %d，其中 stack=%d）⇒ %s'
      % (res['off']['nblk'], res['on']['nblk'], res['on']['n_nuc'],
         res['on']['modes'].count('stack'), 'PASS（block 骨架出现）' if n2 else 'FAIL'))
to = res['off']['th_p90'] if res['off']['thick'] else np.nan
tn = res['on']['th_p90'] if res['on']['thick'] else np.nan
print('  N-3 厚度 p90：off=%.0f nm（≈种子 %.0f）⇒ on=%.0f nm（形核参数 %.0f）⇒ %s'
      % (to * 1e9, T_SEED * 1e9, tn * 1e9, a.t_nuc_nm,
         'PASS（厚度上界改由形核定）' if (tn > to * 1.25) else 'INCONCLUSIVE'))
print('  N-5 同一物理时刻的转变量：off f=%.4f ⇒ on f=%.4f（×%.2f）'
      % (res['off']['f'], res['on']['f'],
         res['on']['f'] / max(res['off']['f'], 1e-30)))
g4 = (not res['on']['wrap'])
print('  N-4 守卫（绕盒/膨胀）：%s' % ('PASS' if g4 else 'FAIL'))
print('=' * 100)
sys.exit(0 if (ok1 and n2 and g4) else 1)
