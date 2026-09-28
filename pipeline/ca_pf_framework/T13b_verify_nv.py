#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T13b_verify_nv.py --- **T13-A 重做**：板条厚 vs 形核数密度 `N_v`（原结论已撤回）。

为什么要重做
-----------
原 T13-A 报"厚度 ∝ `N_v^{−1/3}`（指数 −0.283）"，但**当时没有绕盒守卫**。
用逐变体口径复核（`T13_recheck_wrap.py`）后：三个采样点**全部已绕盒**，
复现指数变成 **+0.021** ⇒ 原 PASS **撤回**，改判 INCONCLUSIVE。
根因：`L = 3.2 µm` 只在每方向装 ~3 个核（`L/d = 2.9`），薄板面内长得极快，
`f ≈ 0.05–0.17` 就把盒子撑满。

本次修正（全部来自 D12 决策）
----------------------------
  * **盒子下限**：`L ≥ 4·ρ^{−1/3}`。对立方盒 `ρ = n/L³` ⇒ `ρ^{−1/3} = L/n^{1/3}`
    ⇒ 判据化简为 **`n ≥ 64`（每方向 4 个核）**。本脚本 `n = 64 / 128 / 256`
    ⇒ `L/d = 4.00 / 5.04 / 6.35` ✓
  * **逐变体绕盒守卫**（`wrap_axes_any()`；并集口径会把 impingement 误报成绕盒）
  * **膨胀守卫**（界面胞数相对 `f=0.5·目标` 时的增长 ≤1.5×）
  * **采样点 `f ≈ 0.10`**（"刚碰撞后"；`f_imp ≈ (π/4)(t/d)`）
  * 厚度用**已验证**的 `r_c^var`（变体标记相关长度；T13 正对照 5/5 在 ±25% 内）

R0 正对照
--------
  量具来自 `T16_verify_rve.stats()`（`r_c^var` 与 `M6p` 都已过正对照），
  本脚本**不新造量具**；另加一条**内部一致性**检查：`r_c^var` 与 `2f/Sv` 的
  比值应落在仓库已知的 0.63–0.88 带内（`2f/Sv` 已被证伪为绝对量，只能当对照）。

判据
----
  T13b-1 **定标**：`ln t` vs `ln N_v` 的斜率 = **−1/3**（±0.15）
  T13b-2 **守卫**：三个采样点都必须"未绕盒 + 未膨胀"
  T13b-3 **一致性**：`r_c^var/(2f/Sv)` ∈ [0.55, 0.95]

用法：python3 T13b_verify_nv.py [--L-um 6.4] [--dx-nm 50] [--ns 64,128,256]
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import stats, C, EPS0, NV, NPF               # noqa: E402

MOB = 1e-9
# ★ 2026-09-28：`Δf` 由 2.0e8 改为 **3.5e8**（= D7 文献 ΔG 在 298 K 的值）。
#   依据：`_probe_growth.py` 门控实测 —— 有弹性时 `Δf=2e8` 的 `dV/V0` 只有 0.170，
#   而**无弹性**是 1.587（弹性压低 ~9 倍）⇒ `f=0.10` 在 `Δf=2e8` 下不可达。
DF = 3.5e8
# ★★★ 2026-09-28 **D12d 的补丁：必要 ≠ 充分**。
#   `L ≥ 4ρ^(−1/3)` ⟺ `n ≥ 64` 是**必要**条件，但**不充分** —— 还必须保证
#   "**晶核在 t=0 时互不重叠**"，否则"形核数密度"这个自变量本身无意义
#   （碰撞在初始时刻就发生了）。
#   判据：`d = ρ^(−1/3) = L/n^(1/3)` 必须 ≥ **2.5 × 晶核面内直径 `2R_seed`**。
#   实测反例（T17 驱动器冒烟）：`L=1.6 µm, n=64 ⇒ d=0.4 µm` 而 `2R_seed=0.6 µm`
#   ⇒ `d/2R = 0.67` ⇒ **初始即重叠** ⇒ 采样到的其实是"已碰撞完"的态（f 直接跳到 0.10）。
#   ⇒ 现在**印出该比值并硬性拒绝**不满足的规格（不给静默无效的数）。
R_SEED, T_SEED = 3.0e-7, 2.0e-7
# ★★★ 2026-09-28 **约束链闭合后的最终规格**（五条约束的交集，全部有实测依据）：
#   ① **板条厚必须被解析** `t/Δx ≥ 3`：Δx=75 nm 时 t=100 nm 只有 **1.33 胞** ⇒ 实测板条
#      **假收缩到 25%**（`_t13b.log` 心跳：step=20 时 f=0.00034 vs f_seed=1.36e-3）。
#      ⇒ 取 **t = 200 nm** ⇒ `t/Δx = 4` ✓。（★ 顺带更**物理**：文献 as-built LPBF α′
#      的板条厚是 **0.51–0.88 µm**，200 nm 比原来的 100 nm 更接近文献。）
#   ② **晶核不得重叠** `d ≥ 2.5·2R_seed`（R9）：2R=600 nm ⇒ `d ≥ 1.5 µm`，取 **d = 1.6 µm** ✓
#   ③ **盒子下限** `L ≥ 4ρ^(−1/3)` ⟺ `n ≥ 64`（D12d）⇒ `L/d = n^{1/3}` = 4.0/5.04/6.35 ✓
#   ④ **生长可行** `Δf ≳ 3.5e8`（`_probe_growth.py`：弹性能把生长压低 ~9 倍）✓
#   ⑤ **成本** `∝ N^3.8`。
#   ★ **实验设计**：扫 `N_v` 时**固定 `d`**、让 `L = d·n^{1/3}` 随 `n` 长大 ——
#     这样 `d/2R` 与种子几何**逐档不变**，`N_v` 是唯一的自变量 ✓（比固定 L 更干净）。
MIN_D_OVER_SEED = 2.5
D_FIX = 1.6e-6          # ★ 固定的晶核间距（米）


def run(L, dx, nseed, f_target, adv='proj2', maxstep=900):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(nseed * 8):
        if ns >= nseed:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    nb_ref, out = None, None
    # ★★★ 2026-09-28 **固定 `f` 采样**（`MEASUREMENT_SPEC R4` 的补丁）：
    #   旧写法"第一个 `f ≥ f_target` 的样本就返回"会遇到两种污染：
    #     ① 采样间隔是 5 步 ⇒ 实际落点可能在 `f_target` 之上很多；
    #     ② 不同档的落点**各不相同** ⇒ 判据实际比的是"不同 `f` 上的统计量"，
    #        而 `f` 本身就是主控变量（实测 T17 冒烟：三档落点 0.1013/0.1188/0.1285）。
    #   ⇒ 现在**记录整条 `(f, 统计量)` 轨迹**，最后**对 `f` 线性插值到 `f_target`**；
    #     并报出插值用的两个夹逼样本的 `f`，据此给出"采样是否受控"的判据。
    hist = []
    _t0 = time.time()
    for it in range(1, maxstep + 1):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad=adv)
        # ★★ 记账：**心跳**（与 T16 同）。没有它时作业静默几小时、无法与"卡住"区分。
        if it % 20 == 0:
            _r0 = g.region()
            _f0 = 1.0 - float((_r0 == 0).sum()) / g.N ** 3
            print('       [心跳 n=%d] step=%-4d f=%.5f  步时=%.2f s  已用=%.1f min'
                  % (nseed, it, _f0, (time.time() - _t0) / it,
                     (time.time() - _t0) / 60.0), flush=True)
        if it % 5:
            continue
        regc = g.region()
        f_now = 1.0 - float((regc == 0).sum()) / g.N ** 3
        # ★★★ 2026-09-28 解耦：门槛原为 `max(0.5*f_target, 0.02)` —— 当
        #   `f_target <= 0.04` 时门槛恒为 0.02，而第一个样本落在 0.0202
        #   ⇒ **必然不夹逼**（实测 T13b Round 49、T21 Round 28-34 同一个陷阱）。
        #   ⇒ 去掉 0.02 地板，只留 `0.5*f_target`。
        if f_now < 0.5 * f_target:
            continue
        s = stats(g)
        if nb_ref is None:
            nb_ref = s['nb']
        infl = s['nb'] / max(nb_ref, 1)
        wv = g.wrap_axes_any()
        s['it'] = it
        s['ns'] = ns
        s['infl'] = infl
        if wv or infl > 1.5:
            s['guard'] = 'WRAP=%s INFL=%.2f' % (wv, infl)
            out = s
            break
        s['guard'] = 'ok'
        hist.append(s)
        out = s
        if s['f'] >= f_target * 1.15:      # 越过目标一定幅度后停（留出插值区间）
            break
    if not hist:
        return dict(f=np.nan, t=np.nan, nb=0, it=-1, ns=ns, guard='NEVER-REACHED',
                    m6p_p25=np.nan, Sv=np.nan, nvar=0, infl=np.nan,
                    f_lo=np.nan, f_hi=np.nan, f_span=np.nan)
    F = np.array([h['f'] for h in hist])
    keys = ('t', 'Sv', 'm6p_p10', 'm6p_p25', 'm6p_med', 'nb', 'nvar')
    o = np.argsort(F)
    res = dict(out)
    res['f_raw'] = float(F.max())
    prev = dict(res)
    for k in keys:
        V = np.array([h[k] for h in hist], float)
        res[k] = float(np.interp(f_target, F[o], V[o]))
    # 夹逼区间（用于"采样是否受控"判据）
    below = F[F <= f_target]
    above = F[F >= f_target]
    res['f_lo'] = float(below.max()) if below.size else np.nan
    res['f_hi'] = float(above.min()) if above.size else np.nan
    if np.isfinite(res['f_lo']) and np.isfinite(res['f_hi']):
        res['f_span'] = float(res['f_hi'] - res['f_lo'])
    else:
        res['f_span'] = np.nan
        # 未能夹逼 ⇒ **不外推**，直接标 INCONCLUSIVE（插值的两端必须真的跨过目标）
        if not (below.size and above.size):
            res['guard'] = 'NOT-BRACKETED(f_max=%.4f)' % F.max()
    # ★★★ 2026-09-28 记账（第 17 处修正，**纯报告层**）：`res` 是从 `out`（**最后一个样本**）
    #   拷贝的 ⇒ `res['it']` 是**跑到第几步才停**，**不是**插值点所在的那一步。
    #   实测把两者混用过：`_t13b.log` 报 `it=45`，而 `f=0.0160` 的夹逼样本其实是
    #   step 15 (f=0.0159) 与 step 20 (f=0.0164) ⇒ **插值点在 step≈19.5**，
    #   用 45 步去算"预算增厚"会把预报量算成 2.3 倍。
    i_lo = int(np.argmin(np.abs(F - res['f_lo']))) if np.isfinite(res['f_lo']) else -1
    i_hi = int(np.argmin(np.abs(F - res['f_hi']))) if np.isfinite(res['f_hi']) else -1
    res['it_lo'] = hist[i_lo]['it'] if i_lo >= 0 else -1
    res['it_hi'] = hist[i_hi]['it'] if i_hi >= 0 else -1
    res['it_last'] = res.get('it', -1)
    res['it'] = res['it_lo'] if res['it_lo'] > 0 else res.get('it', -1)
    res['f'] = float(f_target) if np.isfinite(res['f_span']) else res['f_raw']
    res['n_samples'] = len(hist)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-um', type=float, default=None,
                    help='不给则用「固定 d」设计：L = d·n^(1/3)')
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--ns', default='64,128,256')
    ap.add_argument('--f-target', type=float, default=0.10)
    ap.add_argument('--adv', default='proj2')
    ap.add_argument('--design', default='L', choices=('L', 'rho'),
                    help="L = 固定 d、让盒子长大（**只能查有限尺寸，不能查 N_v 定标**）；"
                         "rho = 固定 L、扫密度（**才是 N_v 定标**，但受 R1 预算门控）")
    ap.add_argument('--force', action='store_true', help='无视 R1 预算门控强行跑')
    ap.add_argument('--dry-run', action='store_true',
                    help='只打规格表 + 种子态自参照就退出（冒烟，不推进）')
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9
    ns = [int(s) for s in a.ns.split(',')]
    # ★★★★★ 2026-09-28 **设计错误修正（本轮第 15 处判据级修正）**
    #   原写法 `fix_d = (a.L_um is None)` ⇒ `L = d·n^{1/3}` ⇒
    #   **`d` 逐档固定 ⇒ `ρ = 1/d³` 逐档固定** ⇒ 三档的**形核密度完全相同**、
    #   只有**盒子大小**在变 ⇒ 统计上同构 ⇒ `t` 对 `L` 应当**平**。
    #   而 T13b-1 却拿它去比 `ln t` vs `ln N_v` 的 **−1/3** ⇒ **必然 FAIL，
    #   且 FAIL 会被误读成"模型违反 N_v 定标律"**。
    #   ⇒ 两种设计分开：
    #     `--design L`  ：固定 d、`L = d·n^{1/3}` ⇒ **有限尺寸检查**（t 对 L 应平）
    #     `--design rho`：固定 L、扫 n        ⇒ **密度扫描**（才是 −1/3 律）
    #   ★ 而 `rho` 设计受 **R1 预算门控**（见下）：五条约束把它夹成很窄的窗口。
    fix_d = (a.design == 'L')
    Ls = {n: (D_FIX * n ** (1 / 3.0) if fix_d else a.L_um * 1e-6) for n in ns}
    if a.design == 'rho' and a.L_um is None:
        print('  ✗ `--design rho` 必须显式给 `--L-um`（固定 L 才能扫密度）。')
        return 2

    # ---------------- R1 预算门控：`t ∝ N_v^(−1/3)` 在本机**能不能被看到**
    #   固定 L 扫 n 时：② `d = L/n^{1/3} ≥ 2.5·2R_seed = 1.5 µm` ⇒ `n ≤ (L/1.5µm)³`
    #                  ③ `L ≥ 4ρ^{−1/3}` ⟺ `n ≥ 64`
    #   ⇒ `n ∈ [64, (L/1.5µm)³]`。判据要分辨斜率 ±0.15 ⇒ `t` 至少得变 ×2（ρ 变 ×8）。
    if a.design == 'rho':
        Lr = a.L_um * 1e-6
        n_hi = int((Lr / (MIN_D_OVER_SEED * 2 * R_SEED)) ** 3)
        n_lo = 64
        Nmax = int(round(Lr / dx))
        print('  ── R1 预算门控（固定 L=%.2f µm ⇒ N=%d）──' % (Lr * 1e6, Nmax))
        print('     ② 不重叠 ⇒ n ≤ %d ； ③ 盒子下限 ⇒ n ≥ %d' % (n_hi, n_lo))
        if n_hi <= n_lo:
            print('     ✗ 可行窗口为空 ⇒ **INCONCLUSIVE (R1)**：本规格下"密度扫描"不存在。')
            if not a.force:
                return 3
        else:
            rho_span = n_hi / float(n_lo)
            t_span = rho_span ** (-1 / 3.0)
            print('     ⇒ ρ 可变范围 ×%.2f ⇒ 按 −1/3 律 `t` 只变 **×%.2f（即 %.0f%%）**'
                  % (rho_span, t_span, (1 - t_span) * 100))
            if rho_span < 8.0:
                # 要 `n_hi/n_lo = 8`（ρ ×8 ⇒ t ×0.5）⇒ `(L/1.5µm)³ = 8·n_lo` ⇒ `L = 1.5·(8n_lo)^{1/3}`
                L_need = 1.5 * (8.0 * n_lo) ** (1 / 3.0)
                N_need = int(round(L_need * 1e-6 / dx))
                print('     ✗ ρ 范围 ×%.2f ≪ 8 ⇒ **INCONCLUSIVE (R1)：本机预算内看不到该定标律**。'
                      % rho_span)
                print('       （要拉开 ρ 只能加大 L：需 `L ≈ %.1f µm` ⇒ `N=%d` ⇒ 步时 ×%.0f'
                      ' ⇒ 单档 ≈ %.1f h @ %.0f s/步）'
                      % (L_need, N_need, (N_need / max(Nmax, 1)) ** 3.8,
                         (N_need / max(Nmax, 1)) ** 3.8 * 120 * 400 / 3600.0, 15.0))
                if not a.force:
                    return 3
        print('     （`--force` 已给 ⇒ 继续，但结论只能标 INCONCLUSIVE。）')
    print('=' * 100)
    print('T13b —— **T13-A 重做**：板条厚 vs 形核数密度（五条约束闭合后的规格）')
    print('  约束链：① `t/Δx ≥ 3`（t=%.0f nm / Δx=%.0f nm ⇒ %.1f ✓）'
          % (T_SEED * 1e9, a.dx_nm, T_SEED / dx))
    print('          ② `d ≥ %.1f × 2R_seed=%.0f nm`；本设计 `--design %s`（%s）'
          % (MIN_D_OVER_SEED, 2 * R_SEED * 1e9, a.design,
             '固定 d、L=d·n^(1/3) ⇒ **ρ 逐档相同**，只能查有限尺寸'
             if fix_d else '固定 L、扫 n ⇒ **ρ 是自变量**'))
    print('          ③ `L ≥ 4ρ^(−1/3)` ⟺ `n ≥ 64`；④ `Δf ≳ 3.5e8`；⑤ 成本 ∝ N^3.8')
    print('  %-6s %-9s %-7s %-9s %-9s %s'
          % ('n', 'L(µm)', 'N', 'd(µm)', 'd/2R', '检查'))
    bad = []
    for n in ns:
        L = Ls[n]
        d = L / n ** (1 / 3.0)
        ratio = d / (2 * R_SEED)
        ok_r = (n >= 64) and (ratio >= MIN_D_OVER_SEED) and (T_SEED / dx >= 3.0)
        if not ok_r:
            bad.append((n, d, ratio))
        print('  %-6d %-9.2f %-7d %-9.4f %-9.2f %s'
              % (n, L * 1e6, int(round(L / dx)), d * 1e6, ratio, '✓' if ok_r else '✗ 违约'))
    if bad:
        print('  ✗ **拒绝运行**：%s ⇒ 规格违约（见约束链）。' % (bad,))
        return 2
    # ★★★★ 2026-09-28 **种子态自参照**（`MEASUREMENT_SPEC R0`）：同尺子、同形状族。
    #   便宜（只建场 + 种种子 + 一次 `stats`，不推进），但它是 T13b-3 唯一合法的参照。
    _n0 = ns[0]
    _g0 = W.LevelSetMulti(int(round(Ls[_n0] / dx)), Ls[_n0], C=C, eps0=EPS0, gamma=0.15,
                          Mob=MOB, df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                          reinit_dt=6.0e-7)
    _rng = np.random.default_rng(7)
    _c, _k = 0, 0
    while _k < _n0 and _c < _n0 * 8:
        _c += 1
        _ctr = _rng.random(3) * (Ls[_n0] - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        _kv = int(_rng.integers(1, NV + 1))
        _nv = np.asarray(NPF[_kv], float)
        try:
            _g0.seed_plate(_kv, _ctr, _nv / np.linalg.norm(_nv), R_SEED, T_SEED)
            _k += 1
        except ValueError:
            pass
    _g0.init_parent()
    _s0 = stats(_g0)
    _e1_0 = 2.0 * _s0['f'] / max(_s0['Sv'], 1e-30)
    seed_ratio = _s0['t'] / _e1_0
    print('  【种子态自参照】n=%d：`r_c^var`=%.1f nm，`2f/Sv`=%.1f nm，比值=**%.3f**；'
          '`f_seed`=%.5f，`M6p p25`=**%.1f°**'
          % (_n0, _s0['t'] * 1e9, _e1_0 * 1e9, seed_ratio, _s0['f'], _s0['m6p_p25']))
    print('  ★ 记账：`M6p` 在 **step=0 就是 0.0°**（`seed_plate` 按构造把宽面切成 ⊥`n*`）'
          '⇒ `M6p` 是**输入**，长大只会让它退化 ⇒ **不得当作"各向异性机制有效"的证据**。')
    if a.dry_run:
        print('  `--dry-run` ⇒ 到此退出（未推进任何一步）。')
        print('=' * 100)
        return 0
    print('-' * 100)
    print('  %-6s %-6s %-8s %-9s %-9s %-8s %-9s %-9s %s'
          % ('n', 'step', 'f', 't=r_c^var', '2f/Sv', '比', '绕盒', 'M6p p25', '守卫'))
    rows = []
    for n in ns:
        s = run(Ls[n], dx, n, a.f_target, a.adv)
        t2f = (2.0 * s['f'] / s['Sv']) if s.get('Sv') else np.nan
        ratio = s['t'] / t2f if (t2f and np.isfinite(t2f)) else np.nan
        rows.append((n, s, ratio))
        print('  %-6d %-6d %-8.4f %-9.1f %-9.1f %-8.3f %-9s %-9.1f %s'
              % (n, s['it'], s['f'], s['t'] * 1e9, t2f * 1e9, ratio,
                 s['guard'] if s['guard'] != 'ok' else 'ok',
                 s['m6p_p25'], s['guard']), flush=True)
        print('         ↳ **固定 f 采样**：插值区间 f ∈ [%s, %s]（跨度 %s）；'
              '轨迹样本数 %s；**夹逼步 %s–%s（插值点所在），末样本步 %s**'
              % ('%.4f' % s['f_lo'] if np.isfinite(s.get('f_lo', np.nan)) else '—',
                 '%.4f' % s['f_hi'] if np.isfinite(s.get('f_hi', np.nan)) else '—',
                 '%.4f' % s['f_span'] if np.isfinite(s.get('f_span', np.nan)) else '**未夹逼**',
                 s.get('n_samples', '—'), s.get('it_lo', '—'), s.get('it_hi', '—'),
                 s.get('it_last', '—')))
    print('-' * 100)
    ok_split = all(np.isfinite(r[1].get('f_span', np.nan)) for r in rows)
    print('  T13b-0 **采样受控**（每档都被 `f_target` 夹逼 ⇒ 插值有效）：%s'
          % ('PASS' if ok_split else 'FAIL（有档未夹逼 ⇒ 该档不外推、标 INCONCLUSIVE）'))
    good = [r for r in rows if r[1]['guard'] == 'ok' and np.isfinite(r[1]['t'])]
    ok2 = len(good) == len(rows)
    # ★★★★★ 2026-09-28 修正：判据必须**跟着设计走**（原版对两种设计套同一个 −1/3，
    #   是判据级错误 —— `--design L` 下 ρ 逐档相同，`t` 对 `L` 本就应当**平**）。
    if a.design == 'L':
        xs = [r[1]['L'] if 'L' in r[1] else Ls[r[0]] for r in good]
        if len(good) >= 3:
            x = np.log(xs)
            y = np.log([r[1]['t'] for r in good])
            sl, ic = np.polyfit(x, y, 1)
            pred = ic + sl * x
            r2 = 1 - float(np.sum((y - pred) ** 2)) / max(float(np.sum((y - y.mean()) ** 2)), 1e-30)
            ok1 = abs(sl) < 0.10
            print('  T13b-1 **[有限尺寸]** `ln t` vs `ln L` 斜率 = **%.3f**'
                  '（固定 ρ ⇒ 期望 **0**，判据 |slope|<0.10） R²=%.4f ⇒ %s'
                  % (sl, r2, 'PASS（厚度不随盒子大小变 ⇒ RVE 够用）' if ok1 else
                     'FAIL（有有限尺寸效应 ⇒ 盒子仍偏小）'))
        else:
            ok1 = False
            print('  T13b-1 [有限尺寸]：INCONCLUSIVE（可用采样点只有 %d 个）' % len(good))
    else:
        ok1 = False
        print('  T13b-1 **[密度定标 −1/3]**：**INCONCLUSIVE (R1)** —— 见上方预算门控；'
              '本机可达的 ρ 范围不足以分辨该斜率（`--force` 下跑出来的斜率不得当证据）。')
    print('  T13b-2 守卫：%s' % ('PASS' if ok2 else 'FAIL（有采样点绕盒/膨胀）'))
    rr = [r[2] for r in rows if np.isfinite(r[2])]
    # ★★★★★ 2026-09-28 修正（第 16 处判据级修正）：原带 `[0.55,0.95]` **把比值倒过来了**。
    #   依据（全部实测，`_t13cal.log` + `_probe_seedstat.log` §A）：
    #     `2f/Sv / t` 随 R/t 变：0.878(R/t=10) / 0.705(5) / 0.771(2.5) / 0.784(5) / 0.629(2.5)
    #                             / **0.515(R/t=1.5)** ← 本实验的工况点
    #     `r_c^var / t` 随 R/t 变：0.915 / 0.893 / 0.996 / 0.847 / 0.760 / **0.839(1.5)**
    #   ⇒ 比值 = (r_c^var/t)/(2f/Sv/t) 在 R/t∈[2.5,10] 上是 **1.04–1.29**，
    #     R/t=1.5 时是 **1.63**。**不是 0.55–0.95。**
    #   ⇒ 判据改成**对种子态自参照**：同工况下先量一次种子的比值，再要求长成态落在
    #     其 ±35% 内（`MEASUREMENT_SPEC R0`：同尺子、同形状族，偏差自然抵消）。
    print('  T13b-3 一致性 `r_c^var/(2f/Sv)`：实测 %s'
          % (['%.3f' % v for v in rr] or ['—']))
    ok3 = bool(rr) and all(abs(v / seed_ratio - 1.0) <= 0.35 for v in rr)
    print('     种子态自参照 = **%.3f** ⇒ 判据 |比/参照 − 1| ≤ 0.35：%s'
          % (seed_ratio, 'PASS' if ok3 else
             'FAIL（形状族在长大中改变 ⇒ 说明 `R/t` 漂出标定区，须改口径）'))
    print('     （参考实测带：R/t∈[2.5,10] ⇒ 1.04–1.29；R/t=1.5 ⇒ 1.63；'
          '**旧判据 `[0.55,0.95]` 是倒过来的，已废**）')
    print('-' * 100)
    print('  ⇒ T13b %s' % ('PASS' if (ok1 and ok2 and ok3) else 'FAIL'))
    print('=' * 100)
    return 0 if (ok1 and ok2 and ok3) else 1


if __name__ == '__main__':
    sys.exit(main())
