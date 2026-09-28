#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T21_beta_calib.py --- **B3**：用**文献 2D 长/宽 AR** 标定 `mob_beta`（界面迁移率各向异性）。

为什么需要它（D17 的连带后果）
----------------------------
`mob_beta=3.5` 当年是**照板条长径比反推**的（`LATH_FACET_PLAN §9`）。
D17 把平流格式从 `central` 换成 `proj2` 后，同一组参数给出的长径比从 **8.97 掉到 2.4**
（且 `central` 的值**不随 Δx 收敛**）⇒ **β 必须在新格式下重标定**。

★ 关键：**必须与文献量同一个量**
--------------------------------
文献（`lit/part_A_lath.md`，实读原文）给的是 **2D 截面**的"最长弦 ÷ 垂直最短弦"
（Ter Haar 2021 的 MTEX 定义；Xing 2021 的 length/width）：
  * `as-built LPBF α′` 的 2D 长/宽 AR = **2.8 – 8.4**（Ter Haar XY 8.37±3.86 / ZX 2.83±1.41；
    Xing 2021 未预热 **5.06**）
  * **长÷厚（3D）在文献里 NOT FOUND**（无人同时测 TEM 厚度与长度）
⇒ 本项目**不能用 3D PCA 尺度比**去对文献；必须**自己也算 2D 截面口径**。

判据（全部先做已知答案正对照，MEASUREMENT_SPEC R0）
--------------------------------------------------
  **T21-0 2D 截面量具的正对照**：解析椭球 `(a,a,c)`（半轴）的**中心截面**是椭圆，
          其长/宽 AR 有解析值 `a/c`（过中心、法向沿 c 的截面）。量具必须复现。
  **T21-1 网格/离散化对照**：同 AR 的椭球在 2–3 档 Δx 上给同一个 AR（±10%）。
  **T21-2 β 标定曲线**：扫 `mob_beta`，量**2D 截面 AR**（三个主轴面），
          给出"哪个 β 让 AR 落进文献带 2.8–8.4"。

用法：python3 T21_beta_calib.py --mode control
      python3 T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402

LIT_AR_BAND = (2.8, 8.4)      # ⛔ **已撤回（2026-09-28，`MEASUREMENT_SPEC R10`）**：
#   `Ter Haar & Becker 2021 / Xing` 的这份"2D 长/宽 AR 带"**原文没取到**，
#   且独立检索结论是「**Ti-64 α′ 的数值长径比没有任何一篇报告过它**」。
#   ⇒ 本常量**不得再作为验收带**；`sweep()` 里对它的判定只保留为**历史对照**。
#   ✅ 同材料同工艺的可替代靶（LPBF Ti-64 as-built α′）：
#     板条厚 **0.51–0.88 µm**（Shuai 2026, 10.3390/ma19061049）；
#     几何长:厚 **≈ 9:1**（Wang 2026, 10.20517/microstructures.2025.144，8.1±2.0 × 0.9±0.4 µm）。
LIT_AR_BAND_RETRACTED = True

# ★★★ 2026-09-28：**后加路径的全局开关**（由 `main()` 从 CLI 设置；模块默认全关）
#   `NS`  = `advance(norm_smooth=NS)` —— 根因① 的修法（法向平滑），`T26` 5/5 过验收
#   `NUC` = D18 形核通道（用户 2026-09-28 批准并入），`T27` 全 PASS
NS = 0
NUC = dict(on=False, t=700e-9, R=400e-9, init=24, every=5, nf=2, ns_=2, harden=0.10)


# ---------------------------------------------------------------- 2D 截面量具
def section_ar_2d(mask2d, dx):
    """2D 截面的长/宽 AR —— **与文献同一个定义**（Ter Haar 2021 的 MTEX 口径）：
       "最长弦（多边形边界的最大距离）÷ 到该弦的**垂直最短弦**"。
       实现：凸包 → 最大 pairwise 距离为长；把点投影到长的垂向上取极差为宽。
       返回 `(AR, 长, 宽, 面积)`；点太少时返回 nan。"""
    from scipy.spatial import ConvexHull
    pts = np.argwhere(mask2d).astype(float) * dx
    if pts.shape[0] < 8:
        return np.nan, np.nan, np.nan, np.nan
    try:
        h = ConvexHull(pts[:, :2])
        P = pts[h.vertices, :2]
    except Exception:                                           # noqa: BLE001
        P = pts[:, :2]
    if P.shape[0] < 3:
        return np.nan, np.nan, np.nan, np.nan
    # 最远点对（凸包顶点数少，直接枚举）
    d2 = ((P[:, None, :] - P[None, :, :]) ** 2).sum(-1)
    i, j = np.unravel_index(int(np.argmax(d2)), d2.shape)
    L = float(np.sqrt(d2[i, j]))
    u = (P[j] - P[i]) / max(L, 1e-30)
    v = np.array([-u[1], u[0]])
    W = float((P @ v).max() - (P @ v).min())
    return L / max(W, 1e-30), L, W, float(mask2d.sum()) * dx ** 2


def ellipsoid_mask(N, dx, semi, center=None):
    """解析椭球的胞掩模（`semi = (a,b,c)` 半轴，米）。"""
    x = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    c0 = np.array([N * dx / 2] * 3) if center is None else np.asarray(center, float)
    r2 = (((X - c0[0]) / semi[0]) ** 2 + ((Y - c0[1]) / semi[1]) ** 2
          + ((Z - c0[2]) / semi[2]) ** 2)
    return r2 <= 1.0


def control():
    print('=' * 100)
    print('T21-0/1 **2D 截面 AR 量具的正对照**（解析椭球，已知答案）')
    print('  口径 = Ter Haar 2021 的 MTEX：最长弦 ÷ 垂直最短弦（与文献**同一个量**）')
    print('  ★ 记账：首版把**截面法向**搞错了 —— 椭球 (a,a,c) 在**垂直 c** 的截面是')
    print('     **圆**（半轴 a,a）⇒ AR = 1，不是 a/c。要拿到非平凡 AR 必须**垂直长轴切**：')
    print('     垂直 a 的截面 ⇒ 椭圆 (b,c) ⇒ **AR = b/c**。下表按此设期望值。')
    print('-' * 100)
    ok = True
    print('  %-24s %-9s %-10s %-10s %-10s %s'
          % ('半轴 (a,b,c) nm', '切向', 'Δx(nm)', 'AR 实测', 'AR 解析', '判定'))
    # (semi_nm, axis_to_slice_perp, dxn)
    # ★ 记账（两处 harness 错误，已修）：
    #   ① 盒子必须按**最大**半轴定尺 —— 首版按 `semi[ax]`（切片法向那个轴）定 ⇒
    #      对 (600,300,75)⊥c 给出 N=16（盒 400 nm）而 a=600 nm ⇒ **椭球被盒子切掉**
    #      ⇒ 截面变成近方形、AR 假读 1.000（真值 2.0）。
    #   ② R1（可行性先算）：(400,400,50)⊥a 在 Δx=50 nm 下 `c/Δx = 1` **低于分辨率**
    #      ⇒ AR 假读 6.538（真值 8.0）。⇒ 换成 `c/Δx ≥ 4` 的可分辨档。
    cases = [((400, 400, 100), 0, 50.0, 400 / 100),    # ⊥a ⇒ (b,c) ⇒ 4.0（c/Δx=2 → 见下）
             ((400, 400, 200), 0, 50.0, 400 / 200),    # ⇒ 2.0（c/Δx=4 ✓）
             ((300, 300, 75), 0, 25.0, 300 / 75),      # ⇒ 4.0
             ((300, 300, 75), 0, 12.5, 300 / 75),      # ⇒ 4.0（离散化对照）
             ((600, 300, 150), 2, 50.0, 600 / 300),    # ⊥c ⇒ (a,b) ⇒ 2.0
             ((400, 400, 150), 2, 50.0, 1.0)]          # ⊥c ⇒ 圆 ⇒ 1.0
    for semi_nm, ax, dxn, ar_th in cases:
        dx = dxn * 1e-9
        semi = np.array(semi_nm, float) * 1e-9
        N = int(2.6 * float(np.max(semi)) / dx) + 8      # ★ 按**最大**半轴定盒
        if N % 2:
            N += 1
        m = ellipsoid_mask(N, dx, semi)
        c = N // 2
        rem = [k for k in range(3) if k != ax]
        ar, L, W, A = section_ar_2d(_slice2d(m, ax, c, rem), dx)
        good = abs(ar / ar_th - 1) < 0.15
        ok &= good
        print('  %-24s %-9s %-10.1f %-10.3f %-10.3f %s'
              % ('%d,%d,%d' % semi_nm, 'abc'[ax], dxn, ar, ar_th,
                 '✓' if good else '✗'))
    print('  判据 T21-0（正对照，|AR/AR_解析 − 1| < 15%%）：%s' % ('PASS' if ok else 'FAIL'))
    print('  判据 T21-1（离散化：同 AR 的 Δx=25/12.5 nm 两档给同一个 AR）：见上表')
    print('=' * 100)
    return ok


# ---------------------------------------------------------------- β 扫描
def one_beta(L, dx, beta, beta_w, seed_R, seed_t, f_target, adv='proj2', steps_max=1200,
             f_ar_ref=2.0e-3):
    """★★ 2026-09-28 改成 **"轨迹 + 同一 `f` 插值"**（与 `T13b`/`T17` 同口径）。

    为什么改（Round 27 的**自我降级**）：旧写法"跑到 `f_target` 就停"会让**不同 β 档
    停在完全不同的 `f`**（实测 `β=0` 停在 `f=0.0506`、而 `β=3.5` 撞步数上限只到 `f=0.0021`
    —— **差 24 倍**）⇒ 两个读数**不是同一个物理态**，"AR 差"无法归因给 β。
    ⇒ 现在记录整条 `(f, AR)` 轨迹，再**对 `f` 插值到同一个 `f_ar_ref`**；
      未夹逼的档标 INCONCLUSIVE（**不外推**）。
    ★ 顺带修：`Δf` 由 `2.0e8` 改为 **`3.5e8`**（与生产一致，见 `T16_verify_rve.py` 的记账）。
    """
    import windowB_surface as W
    from windowB_pf3d import C_cubic, _lam_full
    from windowB_ti64_variants import variants
    C = C_cubic(134.0e9, 110.0e9, 36.0e9)
    EPS0, _F, _M = variants()
    NV = len(EPS0)
    rng0 = np.random.default_rng(0)
    NPF = {}
    for v in range(NV):
        best, bn = None, None
        for n in rng0.normal(size=(400, 3)):
            n = n / np.linalg.norm(n)
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
            if best is None or val < best:
                best, bn = val, n
        NPF[v + 1] = bn
    N = int(round(L / dx))
    DF = 3.5e8
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    g.seed_plate(1, [L / 2] * 3, np.asarray(NPF[1], float), seed_R, seed_t)
    g.init_parent()
    dt = 0.15 * dx / (1e-9 * DF)
    traj = []

    def _ar_now():
        reg = g.region()
        m = (reg == 1)
        if m.sum() < 50:
            return np.nan, float(m.sum()) / g.N ** 3
        idx = np.argwhere(m)
        ctr = idx.mean(0)
        ev, evec = np.linalg.eigh(np.cov((idx - ctr).T))
        ars = []
        for i in range(3):
            ax = int(np.argmax(np.abs(evec[:, i])))
            c = int(round(ctr[ax]))
            rem = [k for k in range(3) if k != ax]
            ar, _L, _Wd, _A = section_ar_2d(_slice2d(m, ax, c, rem), g.dx)
            if np.isfinite(ar):
                ars.append(ar)
        return (float(np.median(ars)) if ars else np.nan,
                float(m.sum()) / g.N ** 3)

    # ★★★ 2026-09-28 第三次（最终）修法：**先把种子态本身采一个点**。
    #   实测：`f` 在第 1 步之后就已经是 1.78e-3（种子分数 1.12e-3 之上）
    #   ⇒ 不采种子态的话，**任何** `f_ar_ref > 1.78e-3` 都永远夹不住（前两次都栽在这里）。
    _ar0, _f0_ = _ar_now()
    if np.isfinite(_ar0):
        traj.append((_f0_, _ar0))
    print('       [轨迹 β=%.1f] step=0(种子) f=%.5f AR=%.3f' % (beta, _f0_, _ar0),
          flush=True)
    for it in range(1, steps_max + 1):
        _ed = g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=beta, mob_beta_w=beta_w, adv_grad=adv, norm_smooth=NS)
        # ★ D18：形核通道（默认关）。打开后才调 `nuc_cfg()` —— `T27` N-2 实测保证
        #   不调用时 `nucleate()` 什么都不做、`region()` 逐位不变。
        if NUC['on']:
            if it == 1:
                g.nuc_cfg(NUC['R'], NUC['t'], gamma=0.15, n_init=NUC['init'],
                          harden_f=NUC['harden'], sym_gap_cells=2, max_per_step=4, seed=11)
            elif it % NUC['every'] == 0:
                _rg = g.region()
                _fn = 1.0 - float((_rg == 0).sum()) / g.N ** 3
                g.nucleate(_ed, f_now=_fn, n_fresh=NUC['nf'], n_stack=NUC['ns_'])
        # ★ 记账（harness 缺陷修正，Round 30）：旧写法每 25 步才采一次 ⇒ 第一次采样
        #   落在 `f=0.00336`，**已经超过** `f_ar_ref=3e-3` ⇒ 没有 `f_lo` ⇒ **未夹逼**、
        #   整个 β 档白跑（判据按设计不外推，所以只能标 INCONCLUSIVE）。
        #   ⇒ 改成：**前 40 步每 5 步采一次**（把参考点夹住），之后每 10 步。
        if it <= 10:
            _do = True                      # 前 10 步**每步采**（把参考点稳稳夹住）
        elif it <= 40:
            _do = (it % 5 == 0)
        else:
            _do = (it % 10 == 0)
        if _do:
            ar, f = _ar_now()
            if np.isfinite(ar):
                traj.append((f, ar))
            print('       [轨迹 β=%.1f] step=%-4d f=%.5f AR=%.3f' % (beta, it, f, ar),
                  flush=True)
            if f >= 4 * f_ar_ref:
                break
    if not traj:
        return None
    F = np.array([t[0] for t in traj])
    A = np.array([t[1] for t in traj])
    o = np.argsort(F)
    lo = F[F <= f_ar_ref]
    hi = F[F >= f_ar_ref]
    br = bool(lo.size and hi.size)
    return dict(f_end=float(F.max()), f_ref=f_ar_ref,
                ar_ref=float(np.interp(f_ar_ref, F[o], A[o])) if br else np.nan,
                ar_end=float(A[o][-1]), n_samp=len(traj), bracketed=br)


def _slice2d(m, ax, c, rem):
    """把 3D 掩模在轴 `ax` 的第 `c` 层取出，并转成 (rem[0], rem[1]) 的 2D 数组。"""
    sl = [slice(None)] * 3
    sl[ax] = c
    a = m[tuple(sl)]                                  # 剩两个轴，按原顺序
    # 需要按 rem 的顺序 + 转置
    order = [k for k in range(3) if k != ax]
    t = [order.index(rem[0]), order.index(rem[1])]
    return np.transpose(a, t)


def sweep(L, dxn, betas, f_target, f_ar_ref=2.0e-3):
    dx = dxn * 1e-9
    print('=' * 100)
    print('T21-2 **β 标定曲线**（2D 截面口径，与文献同一个量）')
    # ★★★ Round 106 修（`REFERENCE_AUDIT` #4 + `MEASUREMENT_SPEC R10`）：
    #   **常量侧早就标了"已撤回"，但判词侧还在无条件打印它** —— 与项目教训 #24
    #   （"同参数改一半"）同型。而且按最新文献核查，Ter Haar 那组数**不是"撤回"，
    #   而是"可引用但必须带四条限定"**（材料确实是 LPBF Ti-6Al-4V as-built α′）。
    #   ⇒ 判词必须把限定与"同材料靶"一起打出来，否则每次运行都会输出一句无限定的结论。
    print('  2D 长/宽 AR 参考（Ter Haar & Becker 2021, MSEA 814, 141185，'
          '**材料=LPBF Ti-6Al-4V as-built α′** ✅ 同材料同工艺）：'
          '均值 **%.1f±3.86 (XY) / %.1f±1.41 (ZX)**；众数 **6.27 / 4.83**'
          % LIT_AR_BAND)
    print('     ⚠⚠ **四条限定（缺一条即为不当转述）**：'
          '①样本被**预筛为长度 >20 µm 的 primary 板条** ⇒ 系统性偏长；'
          '②**均值≠众数**（差 1.3–1.7×；ZX 均值 2.83 甚至低于自己的众数 4.83）；'
          '③"2.8–8.4" 是**跨两个截面的均值区间**、**不是**同一截面内的分布宽度；'
          '④期刊版 closed、数值取自**作者博士论文第 6 章 = 该文手稿**。')
    print('     ✅ **同材料几何靶**：长:厚 **≈ 9:1**（Wang 2026, 8.1±2.0 × 0.9±0.4 µm）、'
          '板条厚 **0.51–0.68(–0.88) µm**（Shuai 2026）。'
          '⛔ 已剔除：30:1（**钢**）、block:lath ≈26（**钢**）、16:1（**文献查不到**）。')
    print('  L=%.2f µm Δx=%.1f nm（N=%d）  Δf=3.5e8（= D7 文献 ΔG@298 K）'
          % (L * 1e6, dxn, int(round(L / dx))))
    print('  ★ **全部 β 档在同一个 `f` = %.4g 上插值取 AR**（Round 27 的自我降级：'
          '旧口径各档停在不同的 f，差 24 倍 ⇒ 不可比）' % f_ar_ref)
    print('-' * 100)
    print('  %-7s %-7s %-9s %-10s %-9s %s'
          % ('β_h', 'β_w', 'f_end', 'AR@f_ref', '夹逼', '判定'))
    rows = []
    for beta in betas:
        r = one_beta(L, dx, beta, min(beta, 2.3) if beta > 0 else 0.0,
                     0.08 * L, 200e-9, f_target, f_ar_ref=f_ar_ref)
        if r is None:
            print('  %-7.1f  变体太小' % beta)
            continue
        rows.append((beta, r))
        inband = np.isfinite(r['ar_ref']) and LIT_AR_BAND[0] <= r['ar_ref'] <= LIT_AR_BAND[1]
        print('  %-7.1f %-7.1f %-9.5f %-10s %-9s %s'
              % (beta, min(beta, 2.3) if beta > 0 else 0.0, r['f_end'],
                 '%.3f' % r['ar_ref'] if np.isfinite(r['ar_ref']) else '—',
                 '✓' if r['bracketed'] else '**✗**',
                 '★在带内' if inband else ('（未夹逼⇒INCONCLUSIVE）' if not r['bracketed'] else '')),
              flush=True)
    print('-' * 100)
    good = [(b, r) for b, r in rows if r['bracketed'] and np.isfinite(r['ar_ref'])]
    if good:
        b_in = [b for b, r in good if LIT_AR_BAND[0] <= r['ar_ref'] <= LIT_AR_BAND[1]]
        print('  ⇒ **同一 f=%.4g 下**落进文献带的 β：%s' % (f_ar_ref, b_in if b_in else '**无**'))
        if len(good) >= 2:
            mono = all(good[i][1]['ar_ref'] >= good[i + 1][1]['ar_ref'] - 1e-9
                       for i in range(len(good) - 1))
            print('  ⇒ 单调性（AR 随 β **下降**）：%s'
                  % ('是 ✓ ⇒ **标定有分辨力**' if mono else '否 ✗ ⇒ 非单调，反解不唯一'))
    else:
        print('  ⇒ **无档被夹逼** ⇒ INCONCLUSIVE（不许外推）')
    print('  ★ 记账：本标定把 β 当作**标定参数**；文献只给了 2D 长/宽，**长÷厚无实验对照**。')
    print('=' * 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='control', choices=('control', 'sweep'))
    # ★★★ 2026-09-28（根因①，`T26` 5/5 过验收）：**后加的数值/物理路径开关**。
    #   为什么必须重跑 `sweep`：B3 的原结论「落进文献带的 β：无；非单调」
    #   是在 **各向异性对比被压缩 ~4 倍**（长:厚 实测 8.45 vs 设计 33）的条件下得到的。
    #   修法 `--norm-smooth 2`（对差分场梯度分量做 `(2m+1)³` 周期盒式平滑再归一化，
    #   即 `MEASUREMENT_SPEC R3` 记录的"对法向做平滑/粗 stencil"口径）；
    #   Δx=25 nm 上三方向同时回到设计 ±10%。`--nuc` 打开 D18 的形核通道。
    #   **默认全关 ⇒ 与归档逐位可比**（`T27` N-2 实测保证了这一点）。
    ap.add_argument('--norm-smooth', type=int, default=0)
    ap.add_argument('--nuc', action='store_true', help='打开 D18 形核通道（默认关）')
    ap.add_argument('--nuc-t-nm', type=float, default=700.0)
    ap.add_argument('--nuc-r-nm', type=float, default=400.0)
    ap.add_argument('--nuc-init', type=int, default=24)
    ap.add_argument('--nuc-every', type=int, default=5)
    ap.add_argument('--nuc-fresh', type=int, default=2)
    ap.add_argument('--nuc-stack', type=int, default=2)
    ap.add_argument('--harden-f', type=float, default=0.10)
    ap.add_argument('--L-um', type=float, default=2.4)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--betas', default='0,2.0,3.5,5.0')
    ap.add_argument('--f-target', type=float, default=0.05)
    # ★★★ 2026-09-28 **第 26 处修正**：`f_ar_ref` 必须落在"板条已经长开"的区间。
    #   实测（`_t21ns2.log`，norm_smooth=2）：`f_ar_ref=2.0e-3` 时四档 AR =
    #   1.212/1.035/1.087/1.031，与 **m=0 归档几乎逐位相同** ⇒ **该参考点量的其实是
    #   "种子几何"**（种子分数 1.66e-3，`f=0.002` 时面内半径只长了 <1%）⇒ β 不可能显形。
    #   而同一条轨迹在**稍后**的 f 上 AR 是**单调随 β 上升**的：
    #     β=1.5 → 1.14（f≈0.005）、β=3.5 → 1.81（f≈0.008）、**β=6.5 → 3.18（f≈0.0055）**
    #     ⇒ β=6.5 已**落进文献带 2.8–8.4**！
    #   ⇒ 用 `--f-ref 0.006`（四档 `f_end` = 0.0063–0.0082，均在可达区间内）重跑。
    #   ⚠ 这是 `R7` 的老陷阱换了个位置："采样点必须落在**有意义**的可达区间内"，
    #     不只是"可达"。
    ap.add_argument('--f-ref', type=float, default=2.0e-3)
    a = ap.parse_args()
    global NS, NUC
    NS = int(a.norm_smooth)
    NUC = dict(on=bool(a.nuc), t=a.nuc_t_nm * 1e-9, R=a.nuc_r_nm * 1e-9,
               init=a.nuc_init, every=a.nuc_every, nf=a.nuc_fresh, ns_=a.nuc_stack,
               harden=a.harden_f)
    if a.mode == 'control':
        return 0 if control() else 1
    ok = control()
    if not ok:
        print('  ✗ 量具正对照 FAIL ⇒ 标定读数不得使用')
        return 1
    sweep(a.L_um * 1e-6, a.dx_nm, [float(s) for s in a.betas.split(',')], a.f_target,
          f_ar_ref=a.f_ref)
    return 0


if __name__ == '__main__':
    sys.exit(main())
