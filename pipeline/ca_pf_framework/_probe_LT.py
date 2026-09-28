#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_LT.py --- ★★★ **决定性诊断**：三方向长大速率比是否等于设计值 1 : e^{−β_w} : e^{−β_h}

为什么要做
---------
文献侧（子代理检索）给出一条改变诊断方向的算术：
    设计速度比  长 : 宽 : 厚 = 1 : e^{−β_w} : e^{−β_h} = 1 : 0.10 : 0.030  ⇒ 长:厚 = **33:1**
    ✅ **同材料同工艺靶（LPBF Ti-6Al-4V as-built α′）**：几何长:厚 **≈ 9:1**
       （Wang 2026, doi 10.20517/microstructures.2025.144，板条 8.1±2.0 × 0.9±0.4 µm）
    ⛔ **已剔除（跨材料）**：长:厚 **30:1**（Rezazadeh 2024 = **钢**）、
       **block:lath ≈ 26**（Morito 2009 = **钢**）、
       长:厚 **16:1**（Gullane 2022 —— **文献本身查不到**）
    ⚠ **可引用但必须带四条限定**：2D 截面 长/宽 AR 均值 8.37±3.86(XY) / 2.83±1.41(ZX)
       （Ter Haar 2021）——①样本**预筛为长度 >20 µm 的 primary 板条**（系统性偏长）
       ②**均值≠众数**（众数 6.27/4.83，差 1.3–1.7×）③"2.8–8.4"是**跨两截面的均值区间**
       ④期刊版 closed、未读到。详见 `MEASUREMENT_SPEC R10` 与 `docs/refcheck/REFERENCE_AUDIT.md`
⇒ **各向异性设计值已经比文献长径比还高** ⇒ "各向异性不够"很可能不是瓶颈。
而实测长径比只有 1.0–1.2 ⇒ **长大被提前截断，或各向异性根本没被数值实现**。

**一次就能定性**：单个孤立板条（**无邻居 ⇒ 无 impingement、无分量合并、无 `f` 歧义**），
同时画 `L(t)`（沿 `a`）、`W(t)`（沿 `w`）、`T(t)`（沿 `n*`），量**增量比**：
  * 若 `ΔL/ΔT ≈ 33`（且 `ΔW/ΔT ≈ 3.3`）⇒ 各向异性**实现正确**，问题在"长大被截断"
    （查 `Δf` 耗尽 / `−γκ` 项 / 尺寸不足 / 时间不够）；
  * 若 `ΔL/ΔT ≪ 33` ⇒ **各向异性没有被数值实现** ⇒ 重点转到实现
    （`n_orient` 与 `n*` 的对齐、`M(n)` 是否真按面法向取值、`proj2` 的投影是否抹平了方向差）。

判据
----
  P-1 量具正对照：三个方向尺在**已知** `(2R, 2R, t)` 的种子上复现（**用 `max−min`，不加 `dx`**，
      依据 `MEASUREMENT_SPEC R3`：加一胞会把薄板抬高 +25%——本探针第一版就是踩了这个坑）
  P-2 三方向速率比 `ΔL:ΔW:ΔT`（对时间线性拟合，报 R²）
  P-3 与设计值 1 : 0.100 : 0.030 的比较
  P-4 健康度：带内 `|∇φ|` 中位（应 ≈1）
  P-5 解析对照：`M0Δf·dt` = 每步位移；含 `ed` 时应放大约 1.4×

用法：python3 _probe_LT.py [--steps 60] [--L-um 3.2] [--dx-nm 50] [--r-nm 300] [--t-nm 200]
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB = 1e-9
DF = 3.5e8
BETA_H, BETA_W = 3.5, 2.3


def extent(reg, axis, dx, min_cells=8):
    """沿 `axis` 的方向尺度 = `max−min`（**不加 `dx`**；`MEASUREMENT_SPEC R3`）。"""
    m = (reg > 0)
    if m.sum() < min_cells:
        return np.nan
    idx = np.argwhere(m).astype(float)          # 胞中心 => 已是 (i+0.5)dx，故 max−min 即长度
    proj = idx @ np.asarray(axis, float)
    return float(proj.max() - proj.min()) * dx


ap = argparse.ArgumentParser()
ap.add_argument('--steps', type=int, default=60)
ap.add_argument('--L-um', type=float, default=3.2)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--r-nm', type=float, default=300.0)
ap.add_argument('--t-nm', type=float, default=200.0)
ap.add_argument('--kv', type=int, default=1, help='用哪个 Burgers 变体（1..12）')
# ★★★ 2026-09-28：`elong` / `--flat-end` —— 直接检验 `windowB_surface.py:1044-1048` 的记账：
#   "椭圆种子的长轴端是**圆角** => 界面法向**从不接近 a** => 沿 a 的生长只能靠斜界面，
#    而斜界面同时增大 W/T => 三方向同比长大。**矩形棱柱的端面严格垂直 a**
#    => 它是唯一能'只增加 L'的面。"
#   ⇒ 若本选项能把实测长:厚从 8.45 推向 33，则"①各向异性对比被压缩"的根因是
#     **种子的长轴端是圆角**（可以用**初始条件**修，不必加密网格）。
ap.add_argument('--elong', type=float, default=1.0, help='面内长/宽比（>1 需配 --flat-end 才平端）')
ap.add_argument('--flat-end', action='store_true', help='长轴两端切成平端面（矩形棱柱）')
# ★★★ 2026-09-28：`--norm-smooth m` —— 对差分场的**梯度分量**做 `(2m+1)³` 盒式平滑
#   再归一化（`MEASUREMENT_SPEC R3` 记录的"对法向做平滑/粗 stencil"口径）。
#   目的：验证根因 ① 的机制假设 ——「`M(n)` 的**输入法向**被阶梯噪声污染 ⇒
#   噪声抬高慢方向的迁移率 ⇒ 各向异性对比被压缩」。若 `m=2` 能把长:厚 从 8.45
#   推向 33，则该假设成立，且 ① 有**不改物理、不加密网格**的修法。
ap.add_argument('--norm-smooth', type=int, default=0, help='法向平滑半径 m（0=不平滑）')
# ★★★ 2026-09-28 新增：**判别"成长减速"的元凶**（靶② 的中心问题）
#   实测（`_ana_LT_rate.py`，`R14` 滑窗口径）：ΔL/步 在 50 步滑窗上从 **48.07 → 19.44**（Δx=166.7）
#   与 **9.34 → 2.66**（Δx=25）⇒ **两套网格都减速 60–72%**，而 `ed` 在同一窗口内**基本恒定**
#   ⇒ 减速**不能**归因于弹性能的时间演化。剩下三条候选：
#     ① `−stk·κ`（Gibbs–Thompson，曲率项）  ② 几何（板条变长后尖端形状/曲率变化）  ③ 数值扩散
#   ⇒ **`--gamma0 0` 关掉曲率项** = 分离 ① 的**单因素实验**：
#      减速消失 ⇒ ① 成立；仍减速 ⇒ 排除 ①，查 ②/③。
ap.add_argument('--gamma0', type=float, default=None,
                help='曲率项系数（None=引擎默认 0.15）；**0 ⇒ 关掉 −γκ 曲率驱动**，用于判别减速元凶')
# ★★★ 2026-09-28 新增：**平流格式单因素**（判别"形状不紧凑"的元凶）
#   实测（`_ana_LT_rate.py` 新增的填充率）：`fill = V/(L·W·T)` 从种子的 **0.884**
#   一进入长大就塌到 **0.30–0.42** 并一直停留 ⇒ **产出的不是紧凑板条**。
#   假设 **H4**：D17 采用的 `proj2`（**保面积投影**）会**抑制突起的横向铺展** ⇒ 助长晶须。
#     它当初正是为压制球面粗化而选的（球粗糙度 2.237→0.998），但同一个投影
#     也可能压掉了板条所需的侧向生长。
#   ⇒ 与 `central`（D17 之前的默认）做单因素对照：**若 `central` 的 `fill` 明显更高 ⇒ H4 成立**。
ap.add_argument('--adv', default='proj2', choices=('central', 'upwind', 'proj', 'proj2'),
                help='平流格式（默认 proj2）。用 central 做 H4 对照')
# ★★★ 2026-09-28 新增：**各向异性强度扫描**（判别"形状不紧凑"的元凶 ③）
#   实测（`_ana_LT_rate.py` 的填充率）：`fill` 从种子的 **0.884** 一长大就塌到 **0.30–0.42**。
#   已排除：① 曲率项（`γ=0` 只差 3.3%）、② `ed`（尖端净驱动力最大）、
#            H4 平流格式（`central` 的 fill 崩到 **0.04–0.07**，比 `proj2` 更糟 ⇒ **D17 平反**）。
#   剩下两条候选必须分开：
#     **③-a `M(n)` 本身**：强各向异性让"法向朝 a 的界面"跑得最快 ⇒ **天然倾向长晶须**
#        ⇒ 若如此，**β→0 时 `fill` 应回到 ≈0.8**（各向同性 ⇒ 紧凑团块）。
#     **③-b 数值扩散**：界面弥散导致"泄漏/分枝" ⇒ 若如此，**β→0 时 `fill` 仍应 ≈0.35**。
#   ⇒ 本开关 = **该判别的单因素**：`--beta-h 0 --beta-w 0` 就是各向同性正对照。
ap.add_argument('--beta-h', type=float, default=None, help='M(n) 法向钉扎强度（None=脚本默认 3.5）')
ap.add_argument('--beta-w', type=float, default=None, help='M(n) 第二钉扎轴强度（None=脚本默认 2.3）')
a_ap = ap.parse_args()
dx = a_ap.dx_nm * 1e-9
L = a_ap.L_um * 1e-6
N = int(round(L / dx))

print('=' * 100)
print('_probe_LT —— 单板条三方向长大速率比（决定性诊断）')
print('=' * 100)
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
K = a_ap.kv
n_hab = np.asarray(NPF[K], float)
n_hab = n_hab / np.linalg.norm(n_hab)
w_ax = np.asarray(g.wtab[K], float)
a_ax = np.asarray(g.atab[K], float)
w_ax = w_ax / np.linalg.norm(w_ax)
a_ax = a_ax - (a_ax @ n_hab) * n_hab
a_ax = a_ax / np.linalg.norm(a_ax)
print('变体 V%d：`n*`=[%+.3f %+.3f %+.3f]  `a`=[%+.3f %+.3f %+.3f]  `w`=[%+.3f %+.3f %+.3f]'
      % (K, *n_hab, *a_ax, *w_ax))
print('  正交性检查：|n*·a|=%.4f  |n*·w|=%.4f  |a·w|=%.4f'
      % (abs(n_hab @ a_ax), abs(n_hab @ w_ax), abs(a_ax @ w_ax)))

g.seed_plate(K, np.array([L / 2] * 3), n_hab, a_ap.r_nm * 1e-9, a_ap.t_nm * 1e-9,
             elong=a_ap.elong, along=(a_ax if a_ap.elong > 1.0 else None),
             flat_end=bool(a_ap.flat_end))
g.init_parent()
reg = g.region()
L0, W0, T0 = (extent(reg, a_ax, dx), extent(reg, w_ax, dx), extent(reg, n_hab, dx))
_expL = 2 * a_ap.r_nm * a_ap.elong
print('\n【P-1 量具正对照】种子：设计 (2·elong·R, 2R, t) = (%.0f, %.0f, %.0f) nm'
      '（elong=%.1f, flat_end=%s）' % (_expL, 2 * a_ap.r_nm, a_ap.t_nm, a_ap.elong,
                                      a_ap.flat_end))
print('   实测 `L0=%s nm  W0=%s nm  T0=%s nm`'
      % tuple('%.1f' % (v * 1e9) if np.isfinite(v) else 'nan' for v in (L0, W0, T0)))
ok1 = (abs(T0 / (a_ap.t_nm * 1e-9) - 1) < 0.06 and abs(L0 / (_expL * 1e-9) - 1) < 0.08)
print('   ⇒ 厚度偏差 %+.1f%%，长度偏差 %+.1f%% ⇒ %s'
      % ((T0 / (a_ap.t_nm * 1e-9) - 1) * 100, (L0 / (_expL * 1e-9) - 1) * 100,
         'PASS' if ok1 else 'FAIL'))

dt = 0.15 * dx / (MOB * DF)
print('\n【P-5 解析对照】dt=%.3e s  标称 `M0Δf·dt` = %.3f nm/步 ⇒ 预期 长:宽:厚 = 1 : %.3f : %.3f'
      % (dt, MOB * DF * dt * 1e9, np.exp(-BETA_W), np.exp(-BETA_H)))

ts, Ls, Ws, Ts = [0], [L0], [W0], [T0]
t0 = time.time()
every = max(5, a_ap.steps // 12)


def ed_by_facet(reg, ed_all, surf=None):
    """把**界面胞**按"离哪个面最近"分成三槽，返回各槽内 `ed[K]` 的均值。

    ★ 目的（根因报告 §1.3 的开放项）：厚向实测 1.35×标称（⇒ 宽面 `ed ≈ +1.2e8`），
      而长向只有 0.28×标称 ⇒ 若 `ed` 相同长向应为 1.35×
      ⇒ **反推尖端 `ed_a ≈ −2.1e8 J/m³`**（弹性自应力顶住尖端）。
      本函数直接把这个量读出来，判定 ① 到底是"网格"还是"弹性顶住"。
    ⚠ 第 1 版取的是"极值带内**所有**变体胞"（含内部），噪声大且不是界面；
      现改为**只取界面胞**（6 邻域内有异区的胞，`surface_band()`）。"""
    m = (reg > 0)
    if surf is not None:
        m = m & surf
    if m.sum() < 20:
        return {}
    idx = np.argwhere(m).astype(float)
    pa = idx @ a_ax
    pw = idx @ w_ax
    pn = idx @ n_hab
    out = {}
    for name, (p, lo_hi) in (('tip  (a 端)', (pa, 1)), ('side (w 侧)', (pw, 1)),
                             ('face (n* 面)', (pn, 0))):
        rng_ = p.max() - p.min()
        if rng_ <= 0:
            continue
        if lo_hi == 1:      # 取两端各 15% 的极值带
            sel = (p <= p.min() + 0.15 * rng_) | (p >= p.max() - 0.15 * rng_)
        else:               # 取中间 15% 的带（宽面所在）
            sel = np.abs(p - 0.5 * (p.max() + p.min())) <= 0.075 * rng_
        if sel.sum() < 5:
            continue
        vals = ed_all[K][idx[sel, 0].astype(int), idx[sel, 1].astype(int),
                        idx[sel, 2].astype(int)]
        out[name] = (float(np.mean(vals)), int(sel.sum()))
    return out


ed_log = {}
for it in range(1, a_ap.steps + 1):
    ed = g.elastic_driving()
    _bh = BETA_H if a_ap.beta_h is None else float(a_ap.beta_h)
    _bw = BETA_W if a_ap.beta_w is None else float(a_ap.beta_w)
    g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
              mob_beta=_bh, mob_beta_w=_bw, adv_grad=a_ap.adv,
              norm_smooth=a_ap.norm_smooth, gamma0=a_ap.gamma0)
    if it % every == 0 or it == a_ap.steps:
        reg = g.region()
        ts.append(it)
        Ls.append(extent(reg, a_ax, dx))
        Ws.append(extent(reg, w_ax, dx))
        Ts.append(extent(reg, n_hab, dx))
        # ★★★ 2026-09-28 新增：**分量诊断**（回答"L 冻结"是真是假）
        #   实测异常（`_w2_box16.log`）：step 150→175 的 `L` **逐位不变**（4860.0），
        #   而按滑窗速率 19.4 nm/步 应涨 ≈485 nm ≈ 2.9 胞 ⇒ **应该跳 2–3 次**。
        #   两种可能必须分开：① 长大**真的**在长向停了；② `extent()` 的 `max−min` 把
        #   **多个不相连的分量**一起框进去（或漏掉），使读数脱离真实主体。
        #   ⇒ 报"分量数 + 最大分量的三向尺度"，与全体口径并列。**判据：两者若不同，以最大分量为准。**
        try:
            from scipy import ndimage as _nd
            lab, ncomp = _nd.label(reg > 0)
            if ncomp > 1:
                sizes = _nd.sum(np.ones_like(lab), lab, index=range(1, ncomp + 1))
                big = int(np.argmax(sizes)) + 1
                regb = (lab == big).astype(np.int8)
                Lb, Wb, Tb = (extent(regb, a_ax, dx), extent(regb, w_ax, dx),
                              extent(regb, n_hab, dx))
                flag = '  ⚠ 分量>1 ⇒ 全体口径不可靠' if ncomp > 3 else ''
                print('        [分量] n=%d 最大分量占胞 %.1f%% ；最大分量 L=%.1f W=%.1f T=%.1f nm%s'
                      % (ncomp, 100.0 * sizes.max() / max(sizes.sum(), 1),
                         Lb * 1e9, Wb * 1e9, Tb * 1e9, flag), flush=True)
            else:
                print('        [分量] n=1 ⇒ 全体口径 = 最大分量口径（读数可信）', flush=True)
        except Exception as _e:
            print('        [分量] 诊断跳过：%s' % _e, flush=True)
        # ★★★ 2026-09-28 新增：**三把独立的长度尺子**（判"L 减速"是物理还是口径饱和）
        #   动机（`_ana_LT_rate.py` 实测）：`ΔL/步` 在 50 步滑窗上从 48.07 降到 11.44（−76%），
        #   而**同窗口的 `ΔT/步` 与 `ΔW/步` 都是 0**（受胞投影量子限制）
        #   ⇒ **减速是"长向独有"的**。两种可能必须分开：
        #     ① 长向长大**真的**在减速（尖端 faceting / `−γκ` / `ed` 顶住）；
        #     ② **`max−min` 口径本身在板条变长后饱和**（极值胞不再更新）⇒ 读数脱离主体。
        #   ⇒ 用**两把与 `max−min` 无关的尺子**交叉验证（`MEASUREMENT_SPEC` 的"同量多尺"纪律）：
        #     `L_vol = V / (W·T)`（体积等效）与 `L_gyr`（回转张量主轴，= √(12λ) 对均匀长方体）。
        m = (reg > 0)
        ncell = int(m.sum())
        Vol = ncell * dx ** 3
        Lv = Vol / max(Ws[-1] * Ts[-1], 1e-30)
        idx = np.argwhere(m).astype(float) + 0.5
        if len(idx) > 10:
            cen = idx.mean(0)
            d = (idx - cen) * dx
            G = (d.T @ d) / len(idx)                      # 回转张量（m²）
            ev = np.sort(np.linalg.eigvalsh(G))[::-1]
            # 对均匀长方体，沿主轴的"全长" = sqrt(12·λ)
            Lg = float(np.sqrt(12.0 * ev[0]))
            Wg = float(np.sqrt(12.0 * ev[1]))
            Tg = float(np.sqrt(12.0 * ev[2]))
        else:
            Lg = Wg = Tg = float('nan')
        print('        [三把尺子] 胞数=%d  V=%.3e m³  ；`max−min` L=%.1f  **`L_vol`=%.1f**  '
              '**`L_gyr`=%.1f** nm ；`W_gyr`=%.1f `T_gyr`=%.1f nm'
              % (ncell, Vol, Ls[-1] * 1e9, Lv * 1e9, Lg * 1e9, Wg * 1e9, Tg * 1e9), flush=True)
        # ★★★ 2026-09-28 新增：**包围盒填充率**（紧凑度）—— 每步都报，让"形状是不是板条"可见
        #   实测（`BOX16d`）：种子 0.884 ⇒ 一长大就塌到 0.30–0.42 并停留 ⇒ **不是紧凑板条**。
        #   ⚠ 口径：三向跨度是**投影**，乘积是不规则形状包围盒的**上界** ⇒ 本值是**下界**。
        _fill = Vol / max(Ls[-1] * Ws[-1] * Ts[-1], 1e-30)
        print('        [紧凑度] `fill = V/(L·W·T)` = **%.3f**（紧凑板条约 0.8–0.9；%s）'
              % (_fill, '**形状不紧凑** ⚠' if _fill < 0.6 else '尚可'), flush=True)
        print('   step=%-4d  L=%.1f  W=%.1f  T=%.1f nm   步时=%.2f s'
              % (it, Ls[-1] * 1e9, Ws[-1] * 1e9, Ts[-1] * 1e9, (time.time() - t0) / it), flush=True)
        if it >= a_ap.steps // 3:
            e = ed_by_facet(reg, ed, surf=g.surface_band())
            if e:
                ed_log[it] = e
                print('        `ed[V%d]` **界面胞**分面均值：%s'
                      % (K, '  '.join('%s=%+.3e J/m³(n=%d)' % (k, v[0], v[1])
                                      for k, v in e.items())), flush=True)

ts = np.array(ts, float)
def slope(y):
    y = np.array(y, float)
    ok = np.isfinite(y)
    if ok.sum() < 3:
        return np.nan, np.nan
    p = np.polyfit(ts[ok], y[ok], 1)
    pred = np.polyval(p, ts[ok])
    r2 = 1 - np.sum((y[ok] - pred) ** 2) / max(np.sum((y[ok] - y[ok].mean()) ** 2), 1e-30)
    return float(p[0]) / dx, r2      # 每步位移（Δx 为单位）

vL, rL = slope(Ls)
vW, rW = slope(Ws)
vT, rT = slope(Ts)
print('\n' + '=' * 100)
print('【P-2 三方向速率（线性拟合，单位 nm/步）】')
print('   长 `dL/dt` = %+.4f nm/步 (R²=%.4f)' % (vL * dx * 1e9, rL))
print('   宽 `dW/dt` = %+.4f nm/步 (R²=%.4f)' % (vW * dx * 1e9, rW))
print('   厚 `dT/dt` = %+.4f nm/步 (R²=%.4f)' % (vT * dx * 1e9, rT))
print('\n【P-3 与设计值比较】')
if np.isfinite(vT) and abs(vT) > 1e-12:
    print('   实测 长:厚 = **%.2f : 1**（设计 **33.0**）' % (vL / vT))
    print('   实测 宽:厚 = **%.2f : 1**（设计 **3.32**）' % (vW / vT))
    print('   实测 厚向速率 / 标称 = **%.2f×**（含 `ed` 时应 ≈1.4×）'
          % (vT * dx / (MOB * DF * dt * np.exp(-BETA_H))))
    r = vL / vT
    if r < 5:
        print('   ⇒ **长向被严重压制（%.1f ≪ 33）⇒ 各向异性没有被数值实现**' % r)
        print('      重点查：`n_orient` 与 `n*` 的对齐、`M(n)` 是否真按面法向取值、'
              '`proj2` 的单一矢量场是否抹平了方向差')
    elif r < 20:
        print('   ⇒ 长向被部分压制（%.1f vs 33）⇒ 兼有实现损失与截断' % r)
    else:
        print('   ⇒ 各向异性**实现正确**（%.1f ≈ 33）⇒ 组织差要从"长大被截断"找' % r)
else:
    print('   厚向速率不可分辨（可能为负）⇒ INCONCLUSIVE')
gd = np.gradient(g.phi[K], dx, edge_order=2)
gn = np.sqrt(sum(t ** 2 for t in gd))
band = np.abs(g.phi[K]) <= 2 * dx
print('\n【P-4 健康度】带内 |∇φ| 中位 = %.3f（应 ≈1）'
      % (float(np.median(gn[band])) if band.any() else float('nan')))

# ---------------- P-6 `ed` 分面读数 ⇒ 判定 ① 是"网格"还是"弹性顶住"
if ed_log:
    print('\n【P-6 `ed` 分面（把实测速率反解成"有效驱动力"再与 `ed` 相减）】')
    last = ed_log[max(ed_log)]
    for name in ('tip  (a 端)', 'side (w 侧)', 'face (n* 面)'):
        if name in last:
            print('   %s  `ed` = %+.3e J/m³' % (name, last[name][0]))
    # 实测每步位移 ⇒ 有效驱动力 `Δf_eff = v/(M0)`（`v` 已是 Δx/步 ⇒ `v·Δx/dt`）
    # ⚠ 第 1 版少乘 1e9（`conv` 里多写了一个 `1e-9`）⇒ 印出 3.14e-1 这种荒谬值。已修。
    conv = 1.0 / (MOB * dt)
    print('   实测速率换算 `Δf_eff`（含毛细项）：长 %+.3e / 宽 %+.3e / 厚 %+.3e J/m³'
          % (vL * dx * conv, vW * dx * conv, vT * dx * conv))
    print('   标称 `Δf` = %+.3e J/m³；`Δf_eff/Δf` = 长 %.2f / 宽 %.2f / 厚 %.2f'
          % (DF, vL * dx * conv / DF, vW * dx * conv / DF, vT * dx * conv / DF))
    if 'tip  (a 端)' in last:
        net_t = vL * dx * conv - last['tip  (a 端)'][0]
        net_f = vT * dx * conv - last['face (n* 面)'][0]
        print('   ⇒ 扣掉 `ed` 后的净驱动力（= `Δf − 毛细项`）：尖端 %+.3e / 宽面 %+.3e J/m³'
              % (net_t, net_f))
        print('     （两者应接近同一个 `Δf`；若尖端显著更小 ⇒ 毛细/曲率项在尖端吃掉驱动力；'
              '若接近 ⇒ `ed` 的自应力就是卡住长向的原因）')
print('  P-1 量具正对照：%s' % ('PASS' if ok1 else 'FAIL'))
print('=' * 100)
