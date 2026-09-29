#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_surface.py --- **Gibbs 面场（level-set）+ 体相场** 的混合实现

与 `windowB_hybrid.py` 的区别（必须记账）:
  windowB_hybrid.py 的"相"状态是**每胞整数标签 + 随机翻转** ⇒ 那是格点 KMC/Potts，
  **不是相场也不是面场** ✗（我在用户指出后确认）。本文件把它换成正确表示：
     · 体相: **连续场**（成分 c、微弹性），按 **PDE** 演化
     · 界面: **level-set 函数 φ(x)**（连续、有符号距离），按
                 ∂φ/∂t + v_n |∇φ| = 0,   v_n = M[ [[Δf]] + Ω γ(n) κ ]
       推进（Gibbs–Thomson），速度由界面**扩展**到带上（nearest-interface-point）
     · 面上量: Γ_i 定义在界面带上，走 ∂Γ/∂t + ∇_s·(D_s∇_sΓ) = 体相通量差
     · 无任何随机翻转 ✗

本文件先实现【面场骨架 + 两个解析判据】:
  S0 曲率正对照：level-set 的 κ = ∇·(∇φ/|∇φ|) 对理想球应给 2/R
  S1 Gibbs–Thomson：孤球收缩应满足 d(R²)/dt = -4 M γ Ω（Ω 并入 M）
（H3 偏析平衡 / H4 守恒沿用 `windowB_hybrid.py` 的验法，下一步搬过来。）
"""
import os
import numpy as np
from scipy import fft as sfft
from scipy.ndimage import distance_transform_edt, gaussian_filter


def upwind_grad(phi, sgn, dx):
    """|∇φ| 的 Godunov 迎风离散（一阶）；sgn 为逐点符号场（+1/−1）：
         sgn>0: |∇φ|²ᵢ = max(max(D⁻φ,0)², min(D⁺φ,0)²)
         sgn<0: |∇φ|²ᵢ = max(max(D⁺φ,0)², min(D⁻φ,0)²)
       ★ 记账：这是 ④ 验证过的格式（`_chk_d4.py`）。**单畴与多畴共用同一份实现**
       （旧写法在两个类里各写一份 ⇒ 极易分叉，是审计记下的一条教训）。"""
    acc = np.zeros_like(phi)
    for ax in range(3):
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        gpos = np.maximum(np.maximum(dm, 0.0) ** 2, np.minimum(dp, 0.0) ** 2)
        gneg = np.maximum(np.maximum(dp, 0.0) ** 2, np.minimum(dm, 0.0) ** 2)
        acc += np.where(sgn > 0, gpos, gneg)
    return np.sqrt(acc)


def _minmod(a, b):
    """minmod 限制器：同号取绝对值小者，异号取 0（保单调）"""
    return 0.5 * (np.sign(a) + np.sign(b)) * np.minimum(np.abs(a), np.abs(b))


def upwind_grad2(phi, sgn, dx):
    """**二阶 ENO(minmod)** Godunov 迎风 |∇φ|。一阶迎风写成
         D⁻ᵢ = (φᵢ−φᵢ₋₁)/dx
       的二阶版本用 3 点单边外推 + minmod 限制（同号才外推 ⇒ 光滑区二阶、拐点处退一阶）：
         Dm2ᵢ = D⁻ᵢ + ½·minmod(D⁻ᵢ−D⁻ᵢ₋₁, D⁺ᵢ−D⁻ᵢ)
         Dp2ᵢ = D⁺ᵢ − ½·minmod(D⁺ᵢ₊₁−D⁺ᵢ, D⁺ᵢ−D⁻ᵢ)
       ★ 记账（为什么要它）：一阶迎风的单边差有 **O(dx) 的取向相关误差**，实测两个后果——
         ① 推进时把有效各向异性压低 ~8%（W1：a2 比 0.90–0.93，且**不随 dx 收敛**）；
         ② Sussman 迭代的不动点不是真 SDF ⇒ reinit **不幂等**，每次把界面内移
            ~0.03–0.10 dx（越用越糟）⇒ 等于给界面加了一个系统性假收缩速度。
        而"中心型/对称型" |∇φ| 虽然二阶、在圆上漂移为 0，却是**边际不稳定**的
        （迭代 100 次后 ΔR 突然跳到 +0.40 dx、带内 |∇φ|→1.26 ✗）。
       ⇒ 二阶 ENO 迎风同时满足：二阶精度 + 单调/稳定。"""
    acc = np.zeros_like(phi)
    for ax in range(3):
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        dmm = np.roll(dm, 1, axis=ax)
        dpp = np.roll(dp, -1, axis=ax)
        Dm2 = dm + 0.5 * _minmod(dm - dmm, dp - dm)
        Dp2 = dp - 0.5 * _minmod(dpp - dp, dp - dm)
        gpos = np.maximum(np.maximum(Dm2, 0.0) ** 2, np.minimum(Dp2, 0.0) ** 2)
        gneg = np.maximum(np.maximum(Dp2, 0.0) ** 2, np.minimum(Dm2, 0.0) ** 2)
        acc += np.where(sgn > 0, gpos, gneg)
    return np.sqrt(acc)


def grad_sym(phi, dx):
    """**二阶**对称 |∇φ|：Σ_轴 ½[(D⁻φ)²+(D⁺φ)²]。
       记账（本轮踩的坑）：一阶 Godunov 迎风 |∇φ| 在**曲面**界面处系统**高估** ~1.5%，
       且误差随取向变化 ⇒ Sussman 迭代的**不动点不是真 SDF**：
       对新鲜球面 SDF 反复 reinit，半径**单调内移且越走越快**
       （-0.028, -0.048, -0.067, -0.084, -0.100 dx ✗，即 reinit 不是幂等的，
       等于给界面加了一个系统性的假收缩速度）。
       对称式把两侧单边差分的 O(dx) 误差对冲掉（余 O(dx²)）⇒ 不动点回到真 SDF ✓。"""
    acc = 0.0
    for ax in range(3):
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        acc = acc + 0.5 * (dm ** 2 + dp ** 2)
    return np.sqrt(acc)


def interface_elastic_energy(C, eps0, k, l, n, N=32, dx=2.5e-8, k0_mode='clamped'):
    """★★ T10（2026-09-28）：**相干界面的弹性能** `γ_el` [J/m²]（按面片身份 (k,l) 与法向 n）。

    做法：在周期盒里用平面 `n·x = const` 把盒子分成两半（区域 k / l），
    用**谱法**（`PF3D.E_el`）解弹性能 `E_el`，再除以**界面面积**（格点键测度）。
    ★ 周期盒里一个周期有 **2 个** 界面；键测度把两个都数进去了 ⇒ 不需要额外的因子 2。

    ★ 记账（判据形式，见 `_probe_paircompat.py` 的前置判决）：
      真实 Ti64 的 Burgers 变体对**不是精确 rank-1 相容**（66 对里最好的对残余
      仍有单变体尺度的 1.4e-3，最差 9.0e-2）⇒ **不能**要求 `γ_el = 0`（机器零）——
      那是**不可达的判据**。可达的判据是：
        ① 合成**精确** rank-1 对 ⇒ `γ_el = 0`（机器零）；
        ② 真实变体 ⇒ `γ_el` 在 `ncmp[k,l]` 处**取最小**且随残余**单调**。

    返回 `(gamma_el, E_el, A)`；`A = 0`（无界面）时返回 `(0.0, E_el, 0.0)`。
    """
    nv = len(eps0)
    L = N * dx
    g = LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.0, Mob=1.0,
                      df=[0.0] * (nv + 1), workers=1, reinit_every=0,
                      k0_mode=k0_mode)
    rel = g.XYZ - np.array([L / 2] * 3)
    nn = np.asarray(n, float)
    d = rel @ (nn / (np.linalg.norm(nn) + 1e-300))
    for j in range(g.nreg):
        g.phi[j] = 1e3
    g.phi[k] = d
    g.phi[l] = -d
    g.init_parent()
    reg = g.region()
    g.pf.phi[:] = False
    for v in range(g.nv):
        g.pf.phi[v] = (reg == v + 1)
    E = float(g.pf.E_el())
    A = 0
    for ax in range(3):
        A += int((reg != np.roll(reg, -1, axis=ax)).sum())
    A *= dx ** 2
    return (E / A if A > 0 else 0.0), E, A


def _bbox_pad(mask, pad=1, wrap=True):
    """布尔掩模的**包围盒**（外扩 pad 胞），返回切片元组；掩模为空返回 None。

    T3 用它把"全场逐场算梯度"压到"只在该场活跃区算"。

    ★★ 两处必须做对（首版都错了，判据 `T3_verify_fastpath.py` T3-2 抓到，记账）：
      ① `pad ≥ 2`：`curvature_of` 用 `np.roll` 做周期中心差分，所以**写回胞的邻居**
         也必须是"用中心差分算出来的"值。`np.gradient` 只在**最外一层**用单边公式
         ⇒ 写回胞需距子盒边界 ≥1，其邻居需距边界 ≥1 ⇒ 写回胞需距边界 ≥2 ⇒ **pad=2**。
      ② `wrap=True`：掩模贴到网格面时，**该轴必须取满整程** —— 否则 `np.roll` 会在
         **子盒**内周期卷绕，而全盒算时是在**整盒**内卷绕，两者不同 ✗。
    """
    idx = np.argwhere(mask)
    if idx.size == 0:
        return None
    n = np.asarray(mask.shape)
    lo = np.maximum(idx.min(0) - pad, 0)
    hi = np.minimum(idx.max(0) + pad + 1, n)
    if wrap:
        # ★ `np.roll` 把轴的**两端耦合**在一起 ⇒ 只要掩模碰到**任一端**，
        #   该轴就必须取满整程（否则子盒内的卷绕对象与全盒不同）。
        _touch = (idx.min(0) == 0) | (idx.max(0) == n - 1)
        lo = np.where(_touch, 0, lo)
        hi = np.where(_touch, n, hi)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def _band_bbox(field, band, dx, margin, wrap=True):
    """带（`|field| ≤ band·dx`）的**包围盒**（外扩 `margin` 胞），返回切片元组或 None。

    ★★★ R1 任务①（2026-09-29）：Sussman 重初始化的**结构性**加速。
      为什么可以只在子盒里迭代（论证，须与实测一起引用）：
        * Sussman 的更新 `φ ← φ − dτ·S·(|∇φ|−1)` 用**迎风**差分；对 `S>0` 的胞
          信息来自 `D⁻`（朝**零等值面**那一侧）⇒ **依赖锥指向界面内部**，
          即"带内胞的值只依赖它到界面之间（更靠内）的胞"。
        * 而**回写掩模**本来就是 `|d2| ≤ band·dx` ⇒ 带外的值**根本不用算对**。
      综合两条：只要子盒包含"带 + margin 胞"，带内的结果与全域迭代**逐位相同**，
      代价却按子盒体积缩小。
      ⚠ **保守取 margin=4**：`np.roll` 的周期回卷只污染离边缘 ≤2 胞的 stencil；
        薄板的中轴处迎风方向可能退化，多留 2 胞余量。
      ⚠ `wrap=True`（周期盒）时，**贴着网格面的轴必须取满整程** —— 与 `_bbox_pad` 同理。
    """
    m = np.abs(field) <= band * dx
    if not m.any():
        return None
    idx = np.argwhere(m)
    n = np.asarray(field.shape)
    lo = np.maximum(idx.min(0) - int(margin), 0)
    hi = np.minimum(idx.max(0) + int(margin) + 1, n)
    if wrap:
        _touch = (idx.min(0) == 0) | (idx.max(0) == n - 1)
        lo = np.where(_touch, 0, lo)
        hi = np.where(_touch, n, hi)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def sussman_reinit(phi, dx, iters=40, dtau=None, grad='upwind2', guard=True,
                   band_cells=None, bbox=None, par=None):
    """④ 保亚胞位置的 PDE 式重初始化：解 φ_τ + S(φ0)(|∇φ|−1) = 0（一阶迎风）。
       零等值面在连续意义下不动 ✓（旧写法 `distance_transform_edt(mask)` 会把界面
       吸附到胞边界，O(0.5dx) 系统偏差 ✗）。
       ★ 记账（本轮修的一个真 bug）：步长必须满足**多维** Godunov 迎风的 CFL
         `dτ·(|S_x|+|S_y|+|S_z|) ≤ dx` ⇒ `dτ ≤ dx/3`（3D；2D 薄板是 dx/2）。
         旧默认 `dτ = 0.8dx` **越界 2.4 倍** ⇒ 这个"迭代"其实在发散：
           症状 ① 界面被"钉"在按 dt 变化的伪不动点上（W1 定容弛豫实测：
                dt 小 5 倍，收敛长径比从 1.35 掉到 1.15 ✗）；
           症状 ② 跑几百步后带内 |∇φ| 从 1.0 突然涨到 5.5 ⇒ 界面炸掉 ✗。
         现在默认 `dτ = 0.5·dx/3`（安全裕度 2 倍），收敛靠增加迭代数（iter=40）。

       ★★★ R1 任务②（2026-09-29）：新增 `par`（并行核）与 `bbox`（子盒）。
         **两者都不改变数值** —— 统计量（`_gm`、`max(gm[_sel])`）用的掩模 `_sel`
         完全落在带内、因而完全落在子盒内，所以统计量逐位不变；
         `par` 只是把逐胞算子切片执行（见 `windowB_par`）。
         ⚠ **绝不能**只在并行路径上加 `bbox` —— 那会让"线程数"变成物理参数。
           因此 `bbox` 与 `par` 都放在**这一个**函数里，两条路径共用同一段代码。
    """
    _par_on = (par is not None and par.n > 1)
    _gwb = (lambda a, s: par.upwind_grad2(a, s, dx)) if _par_on else \
           (lambda a, s: upwind_grad2(a, s, dx))
    _gw1 = (lambda a, s: par.upwind_grad(a, s, dx)) if _par_on else \
           (lambda a, s: upwind_grad(a, s, dx))
    _grd = (lambda a: par.gradient(a, dx, edge_order=2)) if _par_on else \
           (lambda a: np.gradient(a, dx, edge_order=2))
    if bbox is None:
        return _sussman_core(phi, dx, iters, dtau, grad, guard, band_cells,
                             _gwb, _gw1, _grd)
    # ---- 子盒路径：**同一段代码**，只是喂进去的是子盒视图 ----
    # ★★ 记账（R1 自查抓到的**别名 bug**）：子盒路径**绝不能**原地改调用者传进来的数组。
    #   第一版写的是 `phi[bbox] = out; return phi` —— 而调用者 `reinitialize()` 写的是
    #     `dn = self.sussman_reinit(d2, bbox=…)` 然后 `corr2 = dn − d2`，
    #   于是 `dn is d2` ⇒ **`corr2 ≡ 0`**（修正量被自己减掉了）。
    #   全路径返回的是新数组（`_sussman_core` 内部 `phi = phi/_gm` 会新建），
    #   子盒路径也必须**返回新数组**才满足同一个契约。
    sub = np.ascontiguousarray(phi[bbox])
    out = _sussman_core(sub, dx, iters, dtau, grad, guard, band_cells,
                        _gwb, _gw1, _grd)
    res = np.array(phi, copy=True)
    res[bbox] = out
    return res


def _sussman_core(phi, dx, iters, dtau, grad, guard, band_cells, _gwb, _gw1, _grd):
    """Sussman 迭代的**唯一**实现（`sussman_reinit` 的全域/子盒两条路径共用）。

    ★ 为什么抽出来：`AGENTS §3.24`（改一半比不改更危险）—— 两条路径若各写一份，
      迟早分叉。这里保证"全域"与"子盒"、以及"单线程"与"多线程"跑的是**同一段代码**。

    原记账（`EXPERT-#3b / W1-2 / EXPERT-#3c`，逐条保留）：
      * **先整体归一化成近似 SDF**：PDE 式重初始化的稳定性前提是 |∇φ|~1。实测输入
        |∇φ0| = 2（差分场在紧挨界面时）会让 (gm−1)~1，二阶 ENO 过冲 ⇒ **直接发散**
        （zero-level 从 0.012 µm 跑到 −0.82 µm@100 → −71 µm@3000，带内 |∇φ| 变 nan；
        且**迭代越多越糟**，说明是发散不是收敛慢）。归一化只除以**全局常数**，
        不改零等值面、只改斜率，是安全的前置步骤。
      * **统计量的域必须可选**（W1-2）：本算子用 `max(gm)` 定伪时间步。同一场实测
        中心差分全域 max = 1.00，而本算子实际驱动的 `upwind_grad2` 全域 max = **68.5**
        ⇒ `_dte/dtau` 只剩 0.0146。原因是水平集**必然存在中轴/脊线**，脊线上梯度间断
        ⇒ `upwind_grad2` 给伪尖峰 ⇒ **一个远离界面的脊线胞把整个 reinit 冻结**。
        实测（同一初态、只改这一处）：带内中位恢复率 **−2.7% → +97.1%**；
        `region()` 翻转 **0**、界面键 **1.0000×**（零几何损伤）；
        `band_cells ∈ {3,6,12}` ⇒ 96.9% / 97.1% / 46.3% ⇒ **不是需要精调的魔法参数**。
      * **自适应 dτ + 单步 clip + 发散守卫**（EXPERT-#3c）：
        ① `dτ_eff = min(dτ, 0.5dx/3/max(gm))`（CFL 对 gm 也成立）；
        ② 单步更新 clip 到 ±0.5dx；③ `max|φ| > 10×` 初值量级 ⇒ **拒绝本次 reinit**
        （返回原场，**不静默生效**）。
      * 空带 ⇒ **显式退回全域**；**绝不**静默变成"全选"或"全不选"。"""
    phi0 = phi.copy()
    _g = _grd(phi0)
    _gn = np.sqrt(sum(_gi ** 2 for _gi in _g))
    _sel = None
    if band_cells is not None:
        _sel = np.abs(phi0) <= float(band_cells) * dx
        if not _sel.any():
            # ★ 空带 ⇒ **显式退回全域**；**绝不**静默变成"全选"或"全不选"。
            _sel = None
    _gm = float(np.median(_gn if _sel is None else _gn[_sel]))
    if _gm > 1e-12 and abs(_gm - 1.0) > 0.2:
        phi = phi / _gm
        phi0 = phi0 / _gm
    S = phi0 / np.sqrt(phi0 ** 2 + dx ** 2)
    if dtau is None:
        dtau = 0.5 * dx / 3.0   # 一阶迎风、多维 CFL：dτ ≤ dx/3（|S|≤1）
    _phi_raw = phi0.copy()
    _lim0 = float(np.max(np.abs(phi0))) + dx
    for _ in range(int(iters)):
        if grad == 'upwind':
            gm = _gw1(phi, S)
        elif grad == 'upwind2':
            gm = _gwb(phi, S)
        elif grad == 'central':
            g = _grd(phi)
            gm = np.sqrt(sum(gi ** 2 for gi in g))
        else:
            gm = grad_sym(phi, dx)
        _gmax = float(np.max(gm if _sel is None else gm[_sel]))
        _dte = min(dtau, 0.5 * dx / 3.0 / max(_gmax, 1.0))
        _upd = _dte * S * (gm - 1.0)
        phi = phi - np.clip(_upd, -0.5 * dx, 0.5 * dx)
        if guard and float(np.max(np.abs(phi))) > 10.0 * _lim0:
            return _phi_raw            # 发散 => 拒绝，保持原场
    return phi


def herring_stiffness_cusp(ndot2, gamma0, Lam, eps_c=0.05):
    """**尖点/近奇异**界面能的 Herring 刚度 gamma + gamma_tt。

        gamma(th)  = gamma0 * (1 + Lam * sqrt(sin^2 th + eps_c^2))
        gamma_tt   = gamma0 * Lam * (eps_c^2 - s^4 - 2 s^2 eps_c^2) / s^3,   s^2 = sin^2 th + eps_c^2

    ★ 为什么需要它（本轮实测 D11/长时程给的定量理由）：
      孤立单核长跑（beta_h=3.5, beta_w=2.3）：300 步 aspect 3.49 -> 1200 步 **2.23**，
      而**法向厚度反而长了 2.4x**。=> 形状弛豫（Gibbs-Thomson，驱动力 = gamma*kappa）
      用**各向同性的 gamma** 把薄饼**拉圆**了 => 光有 M(n) 钉扎**维持不住**板条。
      要维持，必须让惯习面同时是**低能面 + 刚性面**。

    ★ 凸性（已逐项核对，故**不需要** Wulff 凸化）：
        th -> 90 deg: gamma_tt -> -gamma0*Lam, gamma -> gamma0(1+Lam)
                      => gamma+gamma_tt -> gamma0 > 0  ✓
        th -> 0     : s -> eps_c => gamma_tt -> +gamma0*Lam/eps_c  (>0, 发散) ✓
      => 处处凸；且惯习面处刚度 ~ gamma0*Lam/eps_c **极大** => 该面极稳定。
    Lam 的物理：gamma(惯习面)/gamma(无序面) = 1/(1+Lam)。取 Lam=0.4 => 比 0.71。
    """
    s2 = np.clip(1.0 - ndot2, 0.0, 1.0)
    s2e = s2 + eps_c ** 2
    s = np.sqrt(s2e)
    g = gamma0 * (1.0 + Lam * s)
    gtt = gamma0 * Lam * (eps_c ** 2 - s2 ** 2 - 2.0 * s2 * eps_c ** 2) / (s2e ** 1.5)
    return g + gtt


def herring_stiffness(ndot2, gamma0, Lam, herring=True):
    """各向异性界面刚度 γ_eff = γ + γ_θθ（Herring 项）。
       输入 ndot2 = (n·n_pref)²；对 γ(θ)=γ0[1+Λ sin²θ]（θ = 法向与 n_pref 的夹角）:
           herring=True :  γ+γ_θθ = γ0[1 + 2Λ − 3Λ sin²θ]  ← Gibbs–Thomson 的正确形式
           herring=False:  只用 γ 本身 = γ0[1 + Λ sin²θ]     ← **刻意保留的错误对照**（W1 反向判据）"""
    s2 = 1.0 - ndot2
    if herring:
        return gamma0 * (1.0 + 2.0 * Lam - 3.0 * Lam * s2)
    return gamma0 * (1.0 + Lam * s2)


def iface_crossings(field, dx, axis):
    """**亚胞射线交点**口径的界面位置：沿 `axis` 找 `field` 的相邻变号胞对，
       线性插值出交点在该轴上的亚胞坐标（物理单位）。

    ★ 记账（为什么要它 —— 本轮的直接动因，审计 §10）：
      `region()` **计数法**在**均匀亚胞平移**下没有分辨力：
        · 界面推进 < 0.5·dx 时**逐位不动**（实测 pair_kernel=True 的 P1 读数 0.000 ✗）；
        · 平移恰好是整数胞时又**逐位精确**（旧 W2 的 40×0.1dx = 4dx 正是这种巧合）。
      两个极端都是**构型依赖**的 ⇒ 判据本身不可用。
      射线交点只用"相邻两胞 field 变号 + 线性插值"：O(dx²) 无偏、对任意亚胞平移
      都连续可读，且**不依赖 |∇φ|**（与 S1 的 `radius_rays` 同一口径，可互相印证）。

    返回 (n_cross, coords)；coords 为各交点坐标（一维数组，无交点则为空数组）。
    """
    field = np.asarray(field, float)
    n = field.shape[axis]
    if n < 2:
        return 0, np.zeros(0)
    lo = [slice(None)] * field.ndim
    hi = [slice(None)] * field.ndim
    lo[axis] = np.arange(n - 1)
    hi[axis] = np.arange(1, n)
    a = field[tuple(lo)]
    b = field[tuple(hi)]
    # ★ 记账（本轮实测踩到的退化）：`a*b < 0` 会**漏掉零点正好落在胞心**的情形
    #   （初值 φ = (i−12)dx ⇒ 界面恰在 z 胞 12 的中心 ⇒ a*b = 0 ⇒ 判据返回"无交点"，
    #   量出 z0 = nan ✗）。改用**非对称**变号判据 `(a<0≤b) | (a>0≥b)`：
    #     · a=0 ⇒ t=0（交点就在 a 胞心）、b=0 ⇒ t=1（就在 b 胞心）——都精确；
    #     · 零只在**前一对**被记一次（(a<0,b≥0) 与 (a>0,b≤0) 互斥）⇒ 不重复计数。
    s = ((a < 0) & (b >= 0)) | ((a > 0) & (b <= 0))
    if not s.any():
        return 0, np.zeros(0)
    ii = np.argwhere(s)
    pa = a[tuple(ii.T)]
    pb = b[tuple(ii.T)]
    t = pa / (pa - pb)
    coord = (ii[:, axis].astype(float) + t + 0.5) * dx
    return int(s.sum()), coord


def upwind_flux_vec(phi, V, dx, order=1):
    """★★ D17（2026-09-28）：**矢量速度**的迎风对流算子 `V·∇φ`（保几何平流的核心）。

    为什么要它（P1 的结构性修法）
    ---------------------------
    界面推进的物理是"**零等值面沿自身法向平移**"。仓库此前两条路径分别是：
      * `adv_grad='central'`：`φ ← φ − dt·v_n·|∇φ|_central` —— 用**中心差分**离散
        Hamilton–Jacobi 型 `v_n|∇φ|`。中心型是**非单调（色散）**格式 ⇒ 在网格尺度上
        产生伪振荡 ⇒ 界面**自发粗化**（P1；T16 实测界面胞数 601→4232 ×7）。
      * `adv_grad='upwind'`：Godunov 迎风的 `|∇φ|` 型。它**单调**，球面不粗化；
        但对**线性**（倾斜平面）数据 Godunov 给的是 `max_i|a_i|` 而不是 `|a|`
        ⇒ 倾斜前沿有 **O(dx) 的取向相关慢化**（"阶梯慢化"；W1 实测各向异性被压低
        ~8%，T11g 实测 `v/(MΔf)` 的 Δx 散布 0.558）。
    两者都不对：前者保速度不保几何，后者保几何不保速度。

    **本函数走第三条路：把速度投影成矢量场 `V = v_n·n`，再对 `φ_t + V·∇φ = 0`
    用迎风通量。** 理由：
      1. 迎风格式对**线性**数据是**精确**的（单边差对线性函数无截断误差）
         ⇒ 倾斜平面**精确**平移、无阶梯慢化 ⇒ 修好 `upwind` 的那一半；
      2. 迎风是**单调**格式 ⇒ 不产生网格尺度伪振荡 ⇒ 修好 `central` 的那一半；
      3. 两个场用**同一个** `V` ⇒ 差分场 `d = φ_k − φ_l` 满足 `d_t + V·∇d = 0`
         ⇒ `d` 只**平移**、`|∇d|` 不变（仓库注释里"d 被拉陡、|∇φ| 0.5→530"的病
         在结构上被排除）。

    ⚠ 记账（代价，如实登记）：一阶迎风有 `O(dx)` 的**数值扩散** ⇒ 曲面界面会被轻微
      抹平（靠 `reinitialize` 重整；`order=2` 用 minmod 限制器把光滑区提到二阶）。
      这就是本函数同时提供 `order=1/2` 的原因 —— 哪一档可用由 `T19_verify_proj.py`
      的**已知答案正对照**决定，不靠推理。

    `phi`：(N,N,N) 标量场；`V`：长度 3 的序列（逐胞矢量，可为逐胞 `np.where` 掩模后的场）；
    `order=1` 一阶迎风；`order=2` 二阶 ENO(minmod) 迎风。
    """
    acc = 0.0
    for ax in range(3):
        Va = V[ax]
        if not np.any(Va):
            continue
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx          # D⁻
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx         # D⁺
        if order >= 2:
            dmm = np.roll(dm, 1, axis=ax)
            dpp = np.roll(dp, -1, axis=ax)
            dm = dm + 0.5 * _minmod(dm - dmm, dp - dm)
            dp = dp - 0.5 * _minmod(dpp - dp, dp - dm)
        # 迎风选边：V>0 ⇒ 信息来自上游(−x) ⇒ 用 D⁻；V<0 ⇒ 用 D⁺
        acc = acc + np.where(Va > 0, Va * dm, Va * dp)
    return acc


def extend_along_normal(v, phi, dx, iters=12, dtau_fac=0.4):
    """把界面速度 v 沿**法向**延拓（标准 "extension velocity"：解
         v_τ + S(φ)·(n·∇v) = 0 ,  n = ∇φ/|∇φ|,  S(φ)=φ/√(φ²+dx²)
       用一阶迎风）。为什么必须要它：**只**沿法向常数延拓才能让整个剖面的更新
       成为**纯平移** ⇒ 保 SDF、保界面速度（见 `LevelSetSurface.advance` 的记账）。
       ★ 相比 nearest-interface-point(distance_transform_edt) 延拓：局部、便宜
         （EDT 在 96³ 上每步 ~2 s，这里 ~30 ms），且是**光滑**延拓（无最近点跳变）。"""
    v = v.copy()
    g = np.gradient(phi, dx, edge_order=2)
    gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    for _ in range(iters):
        cov = np.zeros_like(v)
        for ax in range(3):
            w = S * (g[ax] / gn)
            dm = (v - np.roll(v, 1, axis=ax)) / dx
            dp = (np.roll(v, -1, axis=ax) - v) / dx
            cov += w * np.where(w > 0, dm, dp)
        v = v - dtau * cov
    return v


class LevelSetSurface(object):
    """level-set 面场（单相/单畴版；多畴身份由 label 场平流携带，下一步接）"""

    def __init__(self, N, L, gamma=0.15, Mob=1.0, kappa_omega=1.0, ic='sphere',
                 R0=None, workers=4, reinit_every=50, nz=None, ndim=3,
                 reinit_dtau=None, reinit_iters=60, reinit_grad='upwind2'):
        """ndim=2 时用 (N,N,nz) 的薄板 + z 方向平移不变 ⇒ **与真 2D 逐位等价**
           （SDF 不依赖 z、np.gradient 的 z 分量为 0）但便宜 nz 倍。nz 缺省 4。"""
        self.N, self.L = N, L
        self.ndim = ndim
        self.Nz = int(nz) if nz is not None else (4 if ndim == 2 else N)
        self.dx = L / N
        self.gamma = gamma
        self.M = Mob               # 含 Ω（记账：M 已含摩尔体积）
        self.workers = workers
        self.reinit_every = reinit_every
        self.reinit_dtau = reinit_dtau          # None ⇒ 用 sussman_reinit 的安全默认
        self.reinit_iters = reinit_iters
        self.reinit_grad = reinit_grad          # 'sym'(二阶,默认) | 'upwind' | 'central'
        x = (np.arange(N) + 0.5) * self.dx
        xz = (np.arange(self.Nz) + 0.5) * self.dx
        X, Y, Z = np.meshgrid(x, x, xz, indexing='ij')
        c0 = 0.5 * L
        if R0 is None:
            R0 = 0.25 * L
        self.R0 = R0
        r = np.sqrt((X - c0) ** 2 + (Y - c0) ** 2 + (Z - c0) ** 2)
        self.phi = r - R0                    # <0 = 产物内部（有符号距离）

    # ---------- 面几何（全部来自 φ，连续、无台阶伪影）----------
    def normal(self):
        g = np.gradient(self.phi, self.dx, edge_order=2)
        gnorm = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
        return [gi / gnorm for gi in g], gnorm

    def curvature(self):
        """κ = ∇·(∇φ/|∇φ|)（level-set 标准式；凸面（产物在外）取正）"""
        n, _ = self.normal()
        return sum(np.gradient(n[i], self.dx, edge_order=2)[i] for i in range(3))

    def interface_mask(self, band=1.5):
        """界面带：|φ| <= band·dx"""
        return np.abs(self.phi) <= band * self.dx

    def area(self):
        """界面积（coarea 式估计：A = ∫ δ(φ)|∇φ| dV ≈ ∫_{band} |∇φ| dV / (2·band·dx)）
           —— 等价于 (band 内 |∇φ| 的体积分)/(带厚)。收敛性在报告里记账。"""
        m = self.interface_mask()
        _, gnorm = self.normal()
        return float((gnorm * m).sum()) * self.dx ** 3 / (2 * 1.5 * self.dx)

    def volume(self):
        """产物体积 = φ<0 的体积（用平滑阶跃估算以减小量化噪声）"""
        h = 0.5 * (1.0 - np.tanh(np.clip(self.phi / (1.0 * self.dx), -20, 20)))
        return float(h.sum()) * self.dx ** 3

    def radius(self):
        return (3 * self.volume() / (4 * np.pi)) ** (1 / 3)

    # ---------- 2D（薄板）专用：横截面半径 / 定容投影 / 界面点提取 ----------
    def Lz(self):
        return self.Nz * self.dx

    def volume_2d(self):
        """横截面积 = 3D 体积 / 板厚"""
        return self.volume() / self.Lz()

    def radius_2d(self):
        """等效半径 R = sqrt(A_cross/π)（柱体的横截面）"""
        return np.sqrt(max(self.volume_2d(), 0.0) / np.pi)

    def project_volume(self, V_target, iters=12, warn_many_dx=1.0):
        """**定容投影**：把 φ 整体平移一个常数 c（|∇φ|=1 不受影响）使**三维**体积回到 V_target。
           体积对平移的导数 dV/dc = −A（A = 三维界面积）⇒ 牛顿步 c = (V − V_target)/A。
           ★ 记账（本轮踩到的单位陷阱）：**必须用同一套测度** —— 若拿 `volume_2d()`
             （m²）配 `area()`（m²，但是整根柱体的侧面积）就会差一个 Lz ⇒ 修正量被放大
             1/Lz*... 倍。实测：三维/三维 给出正确的 0.115 nm 步长，而 2D/3D 混用一步把
             φ 平移了 **14 mm** ⇒ 界面直接被推出计算域（band=0，"形状消失"）。
             加了下面的守卫：单步修正量超过 `warn_many_dx·dx` 就告警（说明测度没配平）。
           ★ 这是"体积守恒弛豫"的**投影实现**，与 Lagrange 乘子 `df = γ⟨κ⟩_A` 等价
             （两者都只允许形状自由度演化）；投影实现**没有临界核不稳定性** ⇒ 鲁棒。"""
        for _ in range(iters):
            V = self.volume()
            dV = V - V_target
            if abs(dV) < 1e-8 * abs(V_target):
                break
            A = self.area()
            if A <= 0:
                break
            c = dV / A
            if abs(c) > warn_many_dx * self.dx:
                print('   [project_volume 告警] 单步平移 %.3e m = %.2f dx —— 测度可能没配平'
                      % (c, c / self.dx))
            self.phi = self.phi + c
        return self.volume()

    def region_center(self):
        """区域（φ<0）的形心 —— Wulff 形状量测的中心"""
        m = self.phi < 0
        if not m.any():
            return np.zeros(3)
        idx = np.argwhere(m).astype(float) + 0.5
        return (idx.mean(0)) * self.dx

    def radius_iface(self, band=1.5):
        """从**亚胞界面点**量等效半径（球的 R）：λ = mean|x_if − x_c|。
           ★ 记账（本轮修的量测偏差）：`radius()` 用的 tanh 体积测度对**限制在带内**的
             界面平移只有 **90.5%** 灵敏度（0.5sech² 的尾巴被带边截掉）⇒ 用它量界面
             速度会**系统性低估 ~9.5%**（实测：真实更新量给 -0.0200 nm/步，tanh 测度
             只报 -0.0182 nm/步；两者之比 0.918 与 0.905 完全吻合）。
             对**全域平移**（φ+c）才回到 99.86%。所以界面速度必须用**几何点**量，
             不能用带截断的体积测度。"""
        P, _ = self.interface_points(band=band)
        if len(P) < 8:
            return np.nan
        c = self.region_center()
        return float(np.linalg.norm(P - c[None, :], axis=1).mean())

    def radius_rays(self):
        """**射线交点**口径的界面半径：沿三个轴向找 φ 变号的相邻胞对，线性插值出
           亚胞交点位置，再对 |x_cross − x_c| 取平均（面积均匀加权）。
           ★ 为什么需要它：界面**速度**的量测必须避开两类偏置 ——
             (i) tanh 体积测度对"限制在带内"的界面平移只有 90.5% 灵敏度（带边截断）✗；
             (ii) `interface_points` 的**投影** x−φ∇φ/|∇φ|² 在 |∇φ|≠1 时带偏 ✗。
           射线交点只用"相邻两胞的 φ 变号 + 线性插值"，O(dx²) 无偏、也不依赖 |∇φ|。"""
        c = self.region_center()
        rad = []
        for ax in range(3):
            n = self.phi.shape[ax]
            a = np.take(self.phi, np.arange(n - 1), axis=ax)
            b = np.take(self.phi, np.arange(1, n), axis=ax)
            s = (a * b) < 0
            if not s.any():
                continue
            ii = np.argwhere(s)
            pa = a[tuple(ii.T)]
            pb = b[tuple(ii.T)]
            t = pa / (pa - pb)
            pos = (ii.astype(float) + 0.5) * self.dx
            pos[:, ax] = ((ii[:, ax] + t) + 0.5) * self.dx
            rad.append(np.linalg.norm(pos - c[None, :], axis=1))
        if not rad:
            return np.nan
        return float(np.concatenate(rad).mean())

    def interface_points(self, band=1.5, zslice=None):
        """界面点 x_if 与法向 n（一阶投影到零等值面）：
             x_if = x − φ ∇φ/|∇φ|² ,  n = ∇φ/|∇φ|
           返回 (P (M,3), N (M,3))。zslice 给定时只在那一层取点（2D 柱体用）。"""
        g = np.gradient(self.phi, self.dx, edge_order=2)
        gn2 = sum(gi ** 2 for gi in g) + 1e-300
        if zslice is not None:
            sl = (slice(None), slice(None), int(zslice))
            p = self.phi[sl]
            m = np.abs(p) <= band * self.dx
            idx = np.argwhere(m)
            gg = [gi[sl] for gi in g]
            gn2s = gn2[sl]
        else:
            m = np.abs(self.phi) <= band * self.dx
            idx = np.argwhere(m)
            gg, gn2s = g, gn2
        if len(idx) == 0:
            return np.zeros((0, 3)), np.zeros((0, 3))
        pv = self.phi[tuple(idx.T)] if zslice is None else self.phi[sl][tuple(idx.T)]
        pts = np.zeros((len(idx), 3))
        nrm = np.zeros((len(idx), 3))
        # zslice 情形 idx 只有 2 列 ⇒ z 方向导数为 0（真 2D 问题的精确简化）
        axes = [0, 1] if zslice is not None else [0, 1, 2]
        for a in axes:
            ga = gg[a][tuple(idx.T)]
            pts[:, a] = (idx[:, a].astype(float) + 0.5) * self.dx
            nrm[:, a] = ga / np.sqrt(gn2s[tuple(idx.T)])
            pts[:, a] -= pv * ga / gn2s[tuple(idx.T)]
        if zslice is not None:
            pts[:, 2] = (int(zslice) + 0.5) * self.dx
            nrm[:, 2] = 0.0
            nn = np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-300
            nrm = nrm / nn
        return pts, nrm

    # ---------- 速度扩展（nearest-interface-point）----------
    def extend_velocity(self, vn_iface, band_cells=4):
        """把界面上的 v_n 扩展为带上处处可用的速度场（标准做法）"""
        m = self.interface_mask()
        if not m.any():
            return np.zeros_like(self.phi)
        # 到最近界面点的索引
        ind = distance_transform_edt(~m, return_distances=False, return_indices=True)
        vn_ext = vn_iface[tuple(ind)]
        near = distance_transform_edt(~m) <= band_cells
        return np.where(near, vn_ext, 0.0)

    # ---------- 界面推进（PDE，不是翻转）----------
    def advance(self, dt, df=0.0, gamma_eff=None, aniso=0.0, npref=None,
                herring=True, band=1.5, adv_grad='upwind2', band_cells=6,
                extend='edt', ext_iters=14, ext_refresh=5,
                mob_aniso=0.0, mref=None):
        """∂φ/∂t + v_n|∇φ| = 0，v_n = M[Δf − γ_eff(n) κ]（γ_eff = γ+γ_θθ）。
           ★ 记账（本轮移植 ④ 的两处改动）：
             1) 空间导数换成 **Godunov 迎风 |∇φ|**（模块级 `upwind_grad`），
                旧写法用中心差分 `|∇φ|` ⇒ 不稳、且大形变下失真；
             2) 重初始化换成 **Sussman PDE 式**（保亚胞界面位置），
                旧写法 `distance_transform_edt(φ<0 掩模)` 把界面吸附到胞边界 ✗。
           ★ 另外**不再做速度扩展**：v_n 由带上的局部 κ 直接给出（处处光滑），
             而 nearest-interface-point 扩展是 O(dx) 的分段常数近似 ⇒ 无必要且更差。
           —— 顺带记账：本函数旧版还有一个 `ininside := inside` 的笔误（无害但已删）。"""
        # ★★ 记账（本轮最重要的一个修正）：**必须**把界面速度沿法向**扩展到一条较宽的带**
        #    （nearest-interface-point 扩展 ⇒ 速度沿法向为常数 ⇒ 整个剖面的更新是**纯平移**
        #    ⇒ φ 保持 SDF、界面速度精确）。我此前把扩展删掉、只用 1.5dx 窄带，导致：
        #      · 窄带：带外剖面"不动" ⇒ 带边出现折点并随时间累积 ⇒ 界面速度塌掉
        #        （实测 d(R²)/dt 只有理论的 **0.138** ✗，带内 |∇φ| 从 1.00 掉到 0.87）；
        #      · 不扩展的宽带：vn 在带内随 κ∝1/r 变化 ⇒ 剖面被**非均匀拉伸** ⇒ |∇φ| 爆到 4–5 ✗。
        #    修复后（扩展 + 6dx 带）实测 d(R²)/dt = **1.014** ✓、|∇φ| 稳定 ✓。
        gam0 = self.gamma if gamma_eff is None else gamma_eff
        kap = self.curvature()
        m = self.interface_mask(band)
        # ★ 符号约定（记账）：v_n = M[ Δf_bulk − Ω γ κ ]，κ 对**凸的产物**取正。
        #   ⇒ 正曲率使凸体收缩（Gibbs–Thomson）；Δf<0 表示产物相稳定 ⇒ 长大。
        gk = gam0
        if aniso > 0 and npref is not None:
            n, _ = self.normal()
            nd = np.asarray(npref, float)
            nd = nd / (np.linalg.norm(nd) + 1e-300)
            ndot2 = sum(n[i] * nd[i] for i in range(3)) ** 2
            gk = herring_stiffness(np.clip(ndot2, 0.0, 1.0), gam0, aniso, herring)
        # ---- P0.4 (2026-09-26, LATH_FACET_PLAN): 界面**迁移率**各向异性 --------------
        #   物理：界面迁移率与界面能一样由界面结构决定；{334} 型惯习面是"好界面"，
        #         其他取向的迁移率被结构缺陷拖低（faceted growth 的标准图像）。
        #   ★ 为什么必须走 M(n) 而不是继续调 gamma(n)：
        #     P0.3 实测（_chk_mroute A-D，df = **drive_of_T(M_s)** = +1e8 J/m³ 的真实值
        #       —— T5 记账：原文写 "dG_chem(M_s)"，而 dG_chem(M_s) = **−1e8**（ΔG 的约定），
        #       与这里 df=+1e8 是**相反数**；量级对、名字错，已按 T5 统一）：
        #       aniso=0 与 aniso=0.9 的 M6 中位**都是 55.4 deg**，参考取向换对/换错也不动
        #     => 在真实驱动力下，"界面能 vs 驱动力"的幅度竞争根本不成立。
        #     而 M(n) 是**动力学**量，**没有热力学凸性约束**（不需要 gamma+gamma_tt>0）
        #     => 各向异性强度可以任意大，不会被 Delta G 淹没。
        #   形式： M(n) = M0 * [1 - mob_aniso * (1 - (n.nref)^2)]
        #     mob_aniso=0   -> 各向同性（返回旧行为，逐位相同）
        #     mob_aniso=1   -> 非法向迁移率 = 0（完全钉扎）
        Mloc = self.M
        if mob_aniso > 0.0 and mref is not None:
            nv_, _gn_ = self.normal()
            nd_ = np.asarray(mref, float)
            nd_ = nd_ / (np.linalg.norm(nd_) + 1e-300)
            ndot2_ = np.clip(sum(nv_[i] * nd_[i] for i in range(3)) ** 2, 0.0, 1.0)
            Mloc = self.M * (1.0 - mob_aniso * (1.0 - ndot2_))
        vn_if = np.where(m, Mloc * (df - gk * kap), 0.0)
        if extend == 'edt' and (~m).any():
            # 最近界面点扩展：把界面上的 v_n 复制到"到界面距离 ≤ band_cells"内的所有胞
            # ⇒ 沿法向常数 ⇒ 剖面的更新是纯平移（保 SDF、保界面速度）
            # ★ 成本记账：EDT 在 96³ 上 ~2×100 ms ⇒ 每步都算会让步时 +330 ms。
            #   最近界面点的**索引图**变化很慢（界面每步只走 0.02 dx）⇒ 缓存 `ext_refresh`
            #   步复用一次（默认 5 步 ⇒ 步时降到 ~40 ms，速度判据不受影响）。
            age = getattr(self, '_ext_age', 0)
            if age <= 0 or getattr(self, '_ext_band', None) != band_cells:
                self._ext_ind = distance_transform_edt(~m, return_distances=False,
                                                       return_indices=True)
                self._ext_near = distance_transform_edt(~m) <= band_cells
                self._ext_band = band_cells
                self._ext_age = ext_refresh - 1
            else:
                self._ext_age = age - 1
            ind, near = self._ext_ind, self._ext_near
            vn = np.where(near, vn_if[tuple(ind)], 0.0)
        elif extend:
            # ★ 默认：沿法向的 PDE 延拓（局部、便宜、光滑）
            vn = extend_along_normal(vn_if, self.phi, self.dx, iters=ext_iters)
            vn = np.where(np.abs(self.phi) <= band_cells * self.dx, vn, 0.0)
        else:
            vn = vn_if
        if adv_grad == 'central':
            # 对照用：中心差分 |∇φ|（对光滑 SDF 是二阶；迎风是一阶单边）
            _, gn_c = self.normal()
            gmag = gn_c
        elif adv_grad in ('proj', 'proj2'):
            # ★★ D17（2026-09-28）：**投影型保几何平流**（与 `LevelSetMulti.advance`
            #   同一条路）：把 `v_n` 投影成矢量 `V = v_n·n`，再对 `φ_t + V·∇φ = 0`
            #   用迎风通量。理由见 `upwind_flux_vec` 的记账（迎风对线性数据精确 +
            #   单调 ⇒ 既无阶梯慢化、也不产生网格尺度伪振荡）。
            nrm, _ = self.normal()
            V = [vn * nrm[i] for i in range(3)]
            self.phi -= dt * upwind_flux_vec(
                self.phi, V, self.dx, order=(2 if adv_grad == 'proj2' else 1))
            self._cnt = getattr(self, '_cnt', 0) + 1
            if self.reinit_every and self._cnt % self.reinit_every == 0:
                self.reinitialize()
            return vn
        else:
            sgn = np.where(vn > 0, 1.0, -1.0)
            if adv_grad == 'upwind':
                gmag = upwind_grad(self.phi, sgn, self.dx)      # 一阶迎风（最保守）
            else:
                gmag = upwind_grad2(self.phi, sgn, self.dx)     # ★ 二阶 ENO 迎风（默认）
        self.phi -= dt * vn * gmag
        self._cnt = getattr(self, '_cnt', 0) + 1
        if self.reinit_every and self._cnt % self.reinit_every == 0:
            self.reinitialize()
        return vn

    def reinitialize(self, band_cells=6):
        """④ Sussman PDE 式重初始化：把带内的 φ 拉回 |∇φ|=1，**不动零等值面** ✓
           （带外不动 ⇒ 多区域/多岛情形安全）。"""
        near = np.abs(self.phi) <= band_cells * self.dx
        if near.any():
            newp = sussman_reinit(self.phi, self.dx, iters=self.reinit_iters,
                                  dtau=self.reinit_dtau, grad=self.reinit_grad)
            self.phi = np.where(near, newp, self.phi)


# ============================================================ 判据
def S0_curvature(N=64, dx=2e-9, R0=3e-8):
    g = LevelSetSurface(N, N * dx, R0=R0)
    kap = g.curvature()
    m = g.interface_mask()
    k_meas = float(kap[m].mean())
    k_th = 2.0 / R0
    rel = abs(k_meas / k_th - 1)
    print('---- S0 level-set 曲率正对照 ----')
    print('   R=%.0f nm (R/dx=%.1f): κ_meas=%.3e vs 2/R=%.3e ; 相对差 %.2f%%   %s'
          % (R0 * 1e9, R0 / dx, k_meas, k_th, 100 * rel, 'PASS' if rel < 0.05 else 'FAIL'))
    return rel < 0.05


def S1_GibbsThomson(N=96, dx=1e-9, R0=2.4e-8, M=1e-9, gamma=0.15, nstep=400):
    """孤球收缩：d(R²)/dt 应 = -4Mγ（level-set 无台阶伪影，收敛应干净）
       ★ 半径用**亚胞界面点**量（`radius_iface`），不用 tanh 体积测度 ——
         后者对带内平移只有 90.5% 灵敏度，会把斜率系统性拉低 ~9.5% ✗（见该方法记账）。"""
    g = LevelSetSurface(N, N * dx, gamma=gamma, Mob=M, R0=R0)
    dt = 0.02 * dx / (M * 2 * gamma / R0)
    ts, Rs = [], []
    for k in range(nstep):
        if k % 20 == 0:
            ts.append(k * dt)
            Rs.append(g.radius_rays())     # ★ 用无偏的射线交点口径（见该方法的记账）
        g.advance(dt, df=0.0)
    ts, Rs = np.array(ts), np.array(Rs)
    Rs = np.where(np.isfinite(Rs), Rs, np.nan)
    good = np.isfinite(Rs)
    ts, Rs = ts[good], Rs[good]
    keep = (Rs > 0.55 * Rs[0]) & (Rs < 0.99 * Rs[0])   # 收缩方向
    if keep.sum() < 3:                                  # 若反向（长大），则用上侧窗口
        keep = (Rs > 1.01 * Rs[0]) & (Rs < 1.45 * Rs[0])
    if keep.sum() >= 3:
        sl = np.polyfit(ts[keep], Rs[keep] ** 2, 1)[0]
    else:
        sl = np.nan
    sl_th = -4 * M * gamma
    rel = abs(sl / sl_th - 1)
    print('---- S1 Gibbs–Thomson（level-set，孤球收缩）----')
    print('   R(t) 前几点: %s nm' % np.round(np.array(Rs[:6]) * 1e9, 2))
    print('   拟合窗口 %d 点, R/R0∈[%.2f,%.2f] ; d(R²)/dt=%.4e vs -4Mγ=%.4e ; 相对差 %.1f%%   %s'
          % (int(keep.sum()), Rs[keep].min() / Rs[0] if keep.sum() else np.nan,
             Rs[keep].max() / Rs[0] if keep.sum() else np.nan, sl, sl_th, 100 * rel,
             'PASS' if rel < 0.15 else 'FAIL'))
    return rel < 0.15


def _old_main():
    res = {}
    res['S0'] = S0_curvature()
    res['S1'] = S1_GibbsThomson()
    print('\n总判定: %s' % ('ALL PASS' if all(res.values())
                          else 'FAIL -> %s' % [k for k, v in res.items() if not v]))


# ============================================================ 多区域 level-set（多畴身份）
def _argmin_normal(C, e, **kw):
    """★ Round 141：**收敛的** `argmin_n 0.5·e:Lam(C,n):e`（延迟导入，避免环形依赖）。

    本模块与 `windowB_pf3d` 互相引用 ⇒ 用函数内导入。
    物理与实测依据见 `windowB_pf3d.argmin_normal` 的注释。
    """
    from windowB_pf3d import argmin_normal
    return argmin_normal(C, e, **kw)


_ARG_NORMAL_CACHE = {}


def argmin_normal_cached(C, E):
    """`_argmin_normal` 的**进程级 memo**（键 = `(C, E)` 的字节）。

    ★★★ R-block（2026-09-29）：**为什么必须有**
      `_argmin_normal` 是"20k Fibonacci + 局部模式搜索"的**纯函数**，
      单次 ~10 s。而 `LevelSetMulti.__init__` 会调用它
      **每个场一次**（12 变体 = 12 次）**加每对一次**（`_pair_normals` = 66 次）
      ⇒ 单个对象构造 **~780 s**；4 个算例并发时还会互相抢 CPU
      ⇒ 实测生产臂构造 **>15 min** 还没完。
      而**同变体的 `eps0` 逐位相同**（本项目的板条表就是复制出来的）
      ⇒ 12 次里其实只有 1 次是新的。
    ★ 正确性：纯函数 + 只读缓存 + 键是完整输入 ⇒ 命中与未命中**逐位相同**。
      `C` / `E` 都按 float64 的字节做键，不受 NaN 影响（这两个量里没有 NaN）。
    """
    key = (np.asarray(C, float).tobytes(), np.asarray(E, float).tobytes())
    v = _ARG_NORMAL_CACHE.get(key)
    if v is None:
        v = _argmin_normal(C, E)
        _ARG_NORMAL_CACHE[key] = v
    return v


class LevelSetMulti(object):
    """多区域 level-set：每个相/变体一个 φ_k（有符号距离），region = argmin_k φ_k。
       · 身份由 φ 平流携带（**没有随机胞翻转** ✗）
       · 体相耦合：ε⁰(φ) 由 region 给出 ⇒ 复用已验的谱法微弹性
       · 界面动力学：∂φ_k/∂t + v_n^k|∇φ_k| = 0，v_n^k = M[Δf_k + Δf_el,k − Ω γ(n) κ_k]
    """

    def __init__(self, N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9, df=None,
                 Lam=0.0, k0_mode='clamped', workers=4, reinit_every=20, nv=None,
                 aniso_elastic=False, C_hex_tab=None, C_cub=None, sigma_ext=None,
                 reinit_iters=100, reinit_dtau=None, reinit_grad='upwind2',
                 dG_of_T=None, T=None, T_of_t=None, reinit_dt=None,
                 reinit_band_cells=6.0):
        # ★★★ W1-2（2026-09-28，**Gate A-1 选项① —— 用户已批准启用**）：pair reinit 的**统计量域**。
        #   **默认 `6.0`（启用）**；显式传 `None` ⇒ 退回"全域"（改动前的旧行为，可复现归档）。
        #   为什么必须改（`_probe_grad_fixpoint.py` 实测）：
        #     算子用 `max(gm)` 定伪时间步。**同一场**：中心差分全域 max = **1.00**，
        #     而算子实际驱动的 `upwind_grad2` 全域 max = **68.5** ⇒ `_dte/dtau` 只剩 **0.0146**。
        #     水平集场**必然有中轴/脊线**，脊线上梯度间断 ⇒ `upwind_grad2` 伪尖峰
        #     ⇒ **一个远离界面的脊线胞，把整个 reinit 冻结**。
        #   效果（`_chk_w12.py` C-3，真实代码）：恢复率 **−11.0% → +88.0%**；
        #     `region()` 翻转 **0**、界面键 **1.0000×**（**零几何损伤**）。
        #   敏感性（`_probe_fix_bandstats.py`）：`band_cells ∈ {3,6,12}` ⇒ 96.9% / **97.1%** / 46.3%，
        #     且 **6 正是 `reinitialize()` 本来就在用的那个值** ⇒ **不是新增的可调参数**。
        #   ⚠ **这是"改数"的改动**（用户 2026-09-28 批准）⇒ 按 `R8` 必须全量重跑引用它的判据（Wave 2）。
        #     **此前取得的几何读数（板厚/长径比/分组统计）已被本改动超越，必须重取。**
        self.reinit_band_cells = (None if reinit_band_cells is None
                                  else float(reinit_band_cells))
        # EXPERT-#3: reinit_iters 由硬编码 30 提到 100。依据 _tune_reinit.py：
        #   两变体平面界面 d=phi_k-phi_l 的零等值面 iters=30 停在 0.025um，
        #   iters>=100 落到 0.01200um = **解析值** => 残余偏差来自迭代不足。
        self.reinit_iters = int(reinit_iters)
        self.reinit_dtau = reinit_dtau
        self.reinit_grad = reinit_grad
        self.N, self.L = N, L
        self.dx = L / N
        self.gamma = gamma
        self.M = Mob
        self.reinit_every = reinit_every
        # ★★ T11（2026-09-28）：**重初始化按物理时间**（而不是步数）。
        #   为什么必须：CFL 给 `dt ∝ dx` ⇒ 固定 `reinit_every`（步数）时，
        #   **物理上的重初始化间隔 `reinit_every·dt` 正比于 Δx** ⇒ 换个分辨率就换了物理！
        #   给了 `reinit_dt`（秒）时按它触发；不给（默认 None）⇒ 沿用步数语义（逐位兼容）。
        self.reinit_dt = None if reinit_dt is None else float(reinit_dt)
        self._t_since_reinit = 0.0
        self.nv = (nv if nv is not None else (1 if eps0 is None else len(eps0)))
        self.nreg = self.nv + 1                      # 0 = 母相
        # ★★★ R1 任务②（2026-09-29）：**共享内存多线程并行上下文**（`windowB_par.py`）。
        #   【此前的事实】`workers` 只喂给 `sfft.fftn/ifftn`（`windowB_pf3d.py:262,265`）
        #     ⇒ `advance` 里**全部**逐胞算子（迎风通量、minmod、argmin、梯度、einsum）
        #     都是 numpy 单线程调用 ⇒ **defacto 单核**。这就是"advance 只能单核"的原因：
        #     不是不能并行，而是**从来没有把并行度接进去**。
        #   【能不能并行 —— 实测，`_w2_r1par_N192.log`】
        #     ① numpy 的逐元素算子**确实释放 GIL**：把算子按 axis=0 切 slab 用线程跑，
        #        wall 时间真的下降。**双对照**证明量具有分辨力：
        #          正对照 `time.sleep`×20 任务 → 0.054 s（真并行 ✓）
        #          负对照 纯 Python 循环     → 完全平坦（GIL 串行 ✓）
        #     ② **硬天花板 = DRAM 带宽**：本机 triad（读2写1）单线程 11.08 GB/s、
        #        多线程饱和 23.0 GB/s ⇒ **×2.08**。纯流式算子最多 ×2.1；
        #        延迟受限的算子能到 ×4–6.8（`np.where` 4.6、winner/runner-up 6.8、
        #        `argmin` 4.1、`norm` 5.3）⇒ **并行化的收益由"算子的性质"决定，
        #        不是"核数"**。
        #   【正确性】**逐位相同**。所有核都在**空间**上切片，逐胞归约次序不变
        #     （`argmin`/`einsum`/`norm` 的 axis 归约次序没变），且 halo 取法分两类：
        #       · `np.roll` 系（周期 stencil）⇒ halo **环绕取**（`np.take(mode='wrap')`）
        #       · `np.gradient`（盒边界单边差分）⇒ halo 在**盒边界截断**
        #     两条都由 `windowB_par._selftest` 逐位判据把关（10/10 PASS）。
        #   ⚠ 记账：线程数**不是**物理参数（结果逐位相同）⇒ **不触发 `R8`**。
        #     `workers<=1` ⇒ 全部算子退回原单线程实现，行为逐位不变。
        from windowB_par import ParCtx
        self.par = ParCtx(workers)
        self.nthreads = int(workers or 1)
        # ★★ T3（2026-09-28）：`XYZ`（24 B/胞）**惰性分配** —— 它只在撒晶核时用到，
        #   而生产跑里撒核是稀疏事件（B1 的 athermal 形核），却全程占着内存。
        self._XYZ = None
        self.phi = np.full((self.nreg, N, N, N), 1e3)
        # 体相成分与面上过剩（Gibbs 面的状态量）
        try:
            import sys as _s
            # (fix) 原来的硬编码绝对路径 => 换项目相对路径，别人克隆到别处也能跑
            _s.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gibbs'))
            from gibbs_physics import RHO_MOL
            self.rho = RHO_MOL
        except Exception:
            self.rho = 1.0129e5
        self.T = 1950.0
        self.c = np.full((N, N, N), 0.036)
        # ★★ T3：`Gam` / `Gam_mol`（16 B/胞）**惰性分配** —— `surface_chem=False`
        #   （T4 的 B1 默认）时这两块从不被写入，却全程占着内存。
        self._Gam = None
        self._Gam_mol = None
        # ★★ W-6c（2026-09-25）：**面量的权威状态改按「摩尔/胞」存**（Gam_mol）。
        #   为什么： 里的 A_c 是 coarea 测度、**界面一动它就变** ⇒ 账面逐步漏
        #   （实测 advance 侧 rel 1.1e-5/步，30 步累积 1.2e-4；update_Gamma 侧是 2.5e-32）。
        #   改法：内部只对 Gam_mol 做加减（与测度无关）， 只作为
        #   **派生量**供物理（McLean Gamma_eq）与面扩散的通量换算使用 ⇒  用
        #   ，**与时间无关、必然闭合**。
        #   兼容：判据若直接写 （A3/H6/M3 的老写法），update_Gamma 开头会检测
        #   到不一致并以  为准重新同步 Gam_mol（见那里的 guard）。
        # ★★ T3（2026-09-28）：J_edge **惰性分配**（3×(N,N,N) = 24 B/胞）。
        #   它只被面扩散用到，而 `surface_chem=False`（B1 默认）时那条路径整段关闭。
        #   旧写法 `[np.zeros(...)] * 3` 还顺带把**同一个数组引用了三遍**（潜在别名 bug）。
        #   对外仍是 `g.J_edge`（property，读时才分配）⇒ 判据脚本 `_chk_h6.py` 不受影响。
        self._J_edge = None
        self.df = np.zeros(self.nreg) if df is None else np.asarray(df, float)
        # ---- ★★ T6（2026-09-28）：把"**温度的钟**"接进 level-set 引擎 ----
        #   物理：B1 是 athermal 位移型相变 ⇒ 驱动力**只由温度决定**（不是时间）
        #     `df(T) = drive_of_T(T; T0, DS)`（`windowB_km`，T5 已统一为 `>0 = 变体有利`）。
        #   ⇒ 本引擎只认 `df`，不认温度；`dG_of_T` 是**唯一**把温度换成驱动力的人口，
        #     由 `set_T()` 调用。`T_of_t` 是**时间表**（冷却曲线），由 `advance_T()` 驱动。
        #   记账：`windowB_km` 因此被**降级为"钟"** —— 它只是把 T 历史换成驱动历史的
        #     换算器，`DS` 带 **4 倍**不确定度（`DS_BAND = 1.5e5…6.0e5`），
        #     **不预测 `f(T)`**（`D1′`）。
        #   关掉（`dG_of_T=None`，默认）⇒ 与旧行为**逐位相同**（`set_T` 只记历史、不动 df）。
        self.dG_of_T = dG_of_T
        self.T_of_t = T_of_t
        self.T = None if T is None else float(T)
        self.t = 0.0
        self.Thist = dict(t=[], T=[], df=[])
        if self.dG_of_T is not None and self.T is not None:
            self.set_T(self.T)
        # ---- ★★ T4（2026-09-28）：B1 的**溶质通道默认关闭** ----
        #   物理依据（`pipeline/RESEARCH_INTENT.md` §一/§4.2 D2′）：B1 是 β→α′ 的
        #   **位移型、无扩散**相变 ⇒
        #     ① 界面扫过时溶质**原样继承**（k_part = 1.0）⇒ 无分配、无溶质拖曳；
        #     ② 界面**不富集**溶质（Γ ≡ 0）—— 界面化学 Γ_i 属 **Window C，本轮不做**。
        #   记账：这**推翻了此前 `k_part = 0.6303` 的用法** —— 那个数是**液/固分配
        #     系数**（弥散界面 PF 里凝固用的），被误用到位移型马氏体相变上。
        #     凡依赖溶质再分配的归档结论**全部作废**（见 `WINDOWB_P0_REGISTER.md` §T4）。
        #   判据（`T4_verify_no_partition.py`）：200 步后 `max|c − c0| == 0`（逐位）。
        #   回退路径：需要溶质通道时显式写 `g.k_part = 0.6303; g.surface_chem = True`。
        self.k_part = 1.0
        self.surface_chem = False
        # ★★ T9（2026-09-28）：界面刚度 γ(n) 按**面片身份** (I⁻,I⁺) 查表
        #   （`facet_nref`：变体-母相 ⇒ `npref[k]`；变体-变体 ⇒ `ncmp[k,l]`）。
        #   `False` ⇒ 退回 T9 之前"只用 winner 的 `npref[k]`"的行为（供对照）。
        self.facet_id_gamma = True
        # ★★★ R-block（2026-09-29，`BLOCK_DERIVATION.md`）：**板条身份层**
        #   （`windowB_lath.py` 的 `LathTable`）。
        #   `None`（**默认**）⇒ 整条新路径关闭 ⇒ F1/F2/F3 全走标量 `gamma0`
        #     ⇒ 与改动前**逐位相同**（由 `_bk_engine_identity.py` 的逐位判据把关）。
        #   挂上 `LathTable` 后：**F3（同变体低角晶界）** 的界面刚度按
        #     Read–Shockley @@\gamma_{\rm RS}(\theta_{kl})@@ 逐胞替换；
        #     **F1/F2 仍然用标量** ⇒ 单变量改动。
        self.lath = None
        # ★★★ R-block（2026-09-29）：**Gibbs 面上的薄膜序参量 ψ**（`BLOCK_DERIVATION` §4.6）。
        #   `None`（**默认**）⇒ 薄膜通道整段关闭 ⇒ 与改动前**逐位相同**。
        #   设为 `dict(gamma_f=…, W=0.05, L=1e8, psi0=1.0)` 后：
        #     · F3（同变体低角晶界）的面能按 γ_Σ(ψ) 混合；
        #     · ψ 在 F3 胞上按局域 Allen–Cahn 演化（`windowB_film.py`）。
        #   ★ 需要 `self.lath` 已挂上（否则没有 F3 面片身份）。
        self.film = None
        self.psi = None
        self._psi_diag = None
        # ★★ T10：保存建对象时的 C / eps0 引用，供 `gel_facet` 在**自己的小盒**里
        #   量相干界面弹性能（不复用本对象的大盒 —— 那会白烧机时）。
        self._C_ref = C
        self._eps0_ref = None if eps0 is None else [np.asarray(e, float) for e in eps0]
        # ---- T2.1a (2026-09-25): external stress sigma_ext -------------------
        # Driving-force convention, identical to `PF3D.forces()` / `dfdphi()`:
        #     df_v = +eps0_v : sigma_int  +  sigma_ext : eps0_v
        # ★★ T1 修（P0-1，2026-09-28）：**第一项的符号由 `−` 改为 `+`**（原注释写的就是错的）。
        #   驱动力 = −δF_el/δφ_v = +ε⁰_v:σ；外载项 `sigma_ext:eps0_v` 本来就对、不动。
        #   ⇒ 两项现在**同号约定**：正 = 该变体有利。
        # (the second term is the work done by the applied stress as the
        # transformation strain develops).  sigma_ext = None reproduces the old
        # behaviour bit-for-bit (sext_e0 is then identically zero).
        self.sigma_ext = (np.zeros((3, 3)) if sigma_ext is None
                          else np.asarray(sigma_ext, float))
        self.sext_e0 = (np.zeros(self.nv) if eps0 is None else
                        np.array([np.einsum('ij,ij->', self.sigma_ext,
                                            np.asarray(e, float)) for e in eps0]))
        # 弹性
        self.pf = None
        self.ae = None
        self.aniso_elastic = bool(aniso_elastic)
        # ★★★ 2026-09-28（Round 139，**用户批准**）：`elastic_soft` 默认 **False → True**。
        #   为什么（`F-2`，两处 bug 都修完之后才做得了这个判决实验）：
        #     `_w2_edhard3.log` vs `_w2_edsoft3.log`（N=64 / Δx=166.7 nm / 150 步 / 其余逐字相同）
        #       `soft=False`：ΔL : ΔW = +199.4 : +471.5 nm
        #       `soft=True` ：ΔL : ΔW = +745.4 : +235.7 nm   ⇒ **ΔL/ΔW 从 2.75 → 3.16**
        #     更完整的一对（Δx=83.35 / 300 步）：
        #       `soft=False`：ΔL=513.2  ΔW=235.7  ⇒ ΔL/ΔW = **2.18**
        #       `soft=True` ：ΔL=1031.5 ΔW=235.7  ⇒ ΔL/ΔW = **4.38**（ΔL **+101%**，ΔW **逐位不变**）
        #     ⇒ ★ **`soft` 只动"长"方向** —— 正是"把尖端的驱动力/法向还回来"的指纹。
        #   为什么它在物理上更对：
        #     ① 硬 `region` 指示场喂进 FFT 谱法弹性求解器会产生 **Gibbs 振荡**
        #        ⇒ 界面处的 σ 带 O(1) 阶梯噪声 ⇒ `ed` 在界面被污染（AUDIT-#9 的原始动机）；
        #     ② `soft=True` 走的是 `eps0_fields()`（非 gather），而**那正是
        #        `T3_verify_fastpath.py` 当作基准验证过的那条路径**。
        #   ⚠ 代价（必须记账）：`elastic_driving()` 会造 `(nreg,N³)` 并对 **全部 nreg 个场**
        #     做 einsum，而 T3 的 gather 快路径只需 **2** 个 ⇒ **单步变慢**。
        #   ⚠ 严格说 `soft` 是"把 ε⁰ 抹宽 1.5 胞"的**弥散界面**近似，而本模型是
        #     **零厚度 Gibbs 面** ⇒ 若将来要走严格锐界面，正确做法是换**锐界面弹性求解器**
        #     （更大工程），那时本开关应被替换而不是保留。
        #   ⛔ 按 `R8`：**本改动改变全部含 `ed` 的归档读数** ⇒ 引用前必须重跑。
        self.elastic_soft = True
        if C is not None and eps0 is not None:
            from windowB_pf3d import (PF3D, VOIGT, G6 as _G6, _lam_full)   # noqa: F401
            self.pf = PF3D(N, L, C, eps0, gamma=0.0, w90=1e-8, Lmob=0.0,
                           workers=workers, k0_mode=k0_mode,
                           sigma_ext=self.sigma_ext,
                           # ★★ T3（2026-09-28）：level-set 路径只把 `pf.phi` 当**指示场**用
                           #   ⇒ 存 bool（96 → **12 B/胞**）。`ZERO/ONE` 语义不变
                           #   （`eps0_fields` 里 `float*bool` 自动升 float64）。
                           phi_dtype=bool,
                           # ★★ Λ 精度（T3 实测判决，2026-09-28）：**必须 float64**。
                           #   试过 float32（省 144 B/胞）：`Lam` 的元素量级是
                           #   **1.2e10–1.3e11**（不是 O(1)），σ 是 6 项大数相消的结果
                           #   ⇒ 实测 **点位 σ 相对误差 RMS 0.70、max 0.50**；
                           #   **界面带内 100% 的胞 `ed` 误差 > 1%** ⇒ 会直接污染界面速度。
                           #   ⚠ 陷阱：`|ΔE_el|/E_el` 只有 **1.9e-9**（能量由精确的低 k
                           #   模态主导）⇒ **只看能量判据会放过这个错**。
                           #   这条否掉了原计划里的"Λ 存 complex64"（方向对、但精度不够）。
                           lam_prec='f64')
            # ★ T3：K 表只在建 Lam/_k2 时用到 ⇒ 建完释放（24 B/胞）
            self.pf.K = None
            self.e0v_eng = np.array([[eps0[v][i, j] for (i, j) in VOIGT]
                                     for v in range(self.nv)]) * _G6[None, :]
            self._G6 = _G6
        if self.aniso_elastic:
            # ★★ 逐变体模量（方案：参考介质 + 极化迭代；已过 AS-1/AS-1b/AS-2）：
            #   12 个 Burgers 变体的 hcp 张量各不相同（c 轴 = {110}_β 面法向，来自
            #   `windowB_ti64_variants` 的 meta['n'] —— **注意与 `npref` 不是一回事**：
            #   `npref` 是"弹性最省能法向"（惯习面），这里是晶体学 c 轴）
            #   基体 = 母相 bcc。参考模量 C⁰ 取**初始**相体积平均（固定一次；
            #   迭代的不动点与 C⁰ 无关，C⁰ 只影响收敛速度）。
            from windowB_aniso_elastic import AnisoElastic
            from windowB_pf3d import C_hex, C_cubic, C_rot4, rot_z_to
            from windowB_ti64_variants import variants as _vars
            _e0, _Fs, _meta = _vars()
            Cal = C_hex_tab if C_hex_tab is not None else C_hex(
                162.4e9, 92.0e9, 69.0e9, 180.7e9, 46.7e9)      # ★文献值待核对
            Cbe = C_cub if C_cub is not None else C_cubic(134.0e9, 110.0e9, 36.0e9)
            self._C_phases = [Cbe] + [
                C_rot4(Cal, rot_z_to(np.asarray(_meta[v]['n'], float)))
                for v in range(self.nv)]
            f0 = 1.0 / (self.nv + 1)
            self.ae = AnisoElastic(N, L, self._C_phases,
                                   sum(self._C_phases) / len(self._C_phases))

        # ---- P0.1 (2026-09-26, LATH_FACET_PLAN 1-主因①-a): 配对相容法向表 ----
        #   物理依据 = MATH_FRAMEWORK 5.6 的 rank-1 不变平面 (lam2(U)=1):
        #   两个变体 k,l 之间的界面应落在它们的不变平面上, 法向
        #       n*(k,l) = argmin_n 0.5 * dEps0 : Lam(C,n) : dEps0,  dEps0 = eps0_k - eps0_l.
        #   旧代码: 任何界面都用 winner 的 npref[k] (= 对**母相**的惯习面)
        #   => 变体-变体界面用错对象. 生产末态 f=0.9001 => 母相只剩 9.99% 面积
        #   => 绝大多数界面用错 => M6 (58.9 deg vs 随机 59.7 deg) 的第一嫌疑.
        self.ncmp = None      # (nreg,nreg,3); 母相相关项与对角项 = nan (调用方 fallback)
        # ---- P2 (2026-09-26): 每变体的**双轴**（n_hab, w = n_hab x a），a 由 rank-1 分解 ----
        self.wtab = None      # (nreg,3); 母相行 = nan
        # AUDIT-#7 修：同时存**真长轴 a**（rank-1 分解的位移方向）。
        #   原来调用方只能用 n x w 去还原 a，而 a 并不垂直于 n
        #   （实测 n.a = cos(82.7deg) = 0.127），n x (n x a) = n(n.a) - a
        #   => 偏离真 a 约 7.3deg。现在直接给 atab。
        self.atab = None      # (nreg,3); 真长轴 a
        if C is not None and eps0 is not None:
            _w = np.full((self.nreg, 3), np.nan)
            _a = np.full((self.nreg, 3), np.nan)
            # ★★★ 2026-09-29 Round 141 修复：**收敛的 `argmin_n`**。
            #   原写法「在 **400 个随机法向**里取最小」实测**从未收敛**：
            #     `E(400点最优)/E(真最小)` = **16.8 – 1545**（中位 234）；
            #     与真最小的夹角中位 **82°**（`_chk_lam_batch.py`，日志 `_w2_lambatch.log`）。
            #   根因：该泛函的极小**极窄**——40,000 点 Fibonacci 仍高 3–9 倍。
            #   ⇒ 换成 `argmin_normal`（20k Fibonacci + 局部模式搜索，可复现，逐位相同）。
            #   ⚠ 记账：**选支规则不变**（仍 `max|n·nref|`，见 `_rank1_axes`），
            #     只把 `nref` 从"抽样 argmin"换成"收敛 argmin" ⇒ 分支可能相对旧行为改变。
            _nstar = [[] for _ in range(self.nv)]
            for _v in range(self.nv):
                _E = np.asarray(eps0[_v], float)
                _nref, _vmin, _cons = argmin_normal_cached(C, _E)
                _nstar[_v] = [float(_vmin), float(_cons)]
                _R = self._rank1_axes(_E, _nref)
                if _R is not None:
                    _w[_v + 1] = _R[2]
                    _a[_v + 1] = _R[1]      # AUDIT-#7: 真长轴
            self.wtab = _w
            self.atab = _a
            # 收敛证书：12 个变体是立方对称等价的 ⇒ 真最小能量必须**全部相同**。
            # （旧写法没有这个证书，所以"翻支"可以静默发生。）
            self.nstar_conv = np.array(_nstar)          # (nv, 2) = (E_min, E_scan/E_min)
            _e = self.nstar_conv[:, 0]
            self.nstar_spread = float((_e.max() - _e.min()) / max(abs(_e.mean()), 1e-30))

        if C is not None and eps0 is not None:
            self.ncmp = self._pair_normals(C, eps0)

    # ---------- 区域与几何 ----------
    @staticmethod
    def _rank1_axes(eps, nref):
        """对形状应变 eps 做 **rank-1 分解** eps = 0.5*(a n^T + n a^T)，
           并用 nref 选解（分解有**两个**解，取 n 更接近 nref 的那个）。
           返回 (n_hab, a_axis, w_axis)；w = n x a = 板条**宽度方向**。

           物理（MATH_FRAMEWORK 5.6 的 lam2(U)=1 的直接延伸）：
             n = 惯习面法向（大面法向）—— 已被 beta_h 压制
             a = 界面位错的**位移/滑移方向** = 板条**长轴**（不压制）
             w = n x a = 面内垂直方向 = 板条**宽度方向**（第二钉扎轴）
           ★ 记账：a.n 不要求为 0（rank-1 分解中 a.n 正比于 trace(eps)，
             第一版判据误以为要正交，已更正）。判据用**重构误差**。
        """
        eps = np.asarray(eps, float)
        w_, V = np.linalg.eigh(eps)
        o = np.argsort(w_)[::-1]
        w_ = w_[o]; V = V[:, o]
        mu1, mu3 = w_[0], w_[2]
        if mu1 <= 0 or mu3 >= 0:
            return None
        e1, e3 = V[:, 0], V[:, 2]
        r = np.sqrt(-mu3 / mu1)
        cands = []
        for sgn in (+1.0, -1.0):
            n = e1 + sgn * r * e3
            n = n / np.linalg.norm(n)
            a = mu1 * e1 - sgn * np.sqrt(-mu1 * mu3) * e3
            a = a / np.linalg.norm(a)
            cands.append((n, a))
        nd = np.asarray(nref, float); nd = nd / np.linalg.norm(nd)
        best = max(cands, key=lambda t: abs(t[0] @ nd))
        n, a = best
        wv = np.cross(n, a)
        nw = np.linalg.norm(wv)
        if nw < 1e-8:
            wv = np.cross(n, [0.0, 0.0, 1.0])
            nw = np.linalg.norm(wv) + 1e-300
        return n, a, wv / nw

    @staticmethod
    def _pair_normals(C, eps0, nsamp=600, seed=0):
        """变体-变体配对 (k,l) 的 rank-1 相容法向表 (MATH_FRAMEWORK 5.6).

        返回 (nv+1, nv+1, 3): ncmp[k,l] = argmin_n 0.5 dEps0:Lam(C,n):dEps0.
        母相相关项 (k==0 或 l==0) 与对角项 = nan (物理上不适用, 调用方 fallback 到 npref).
        与 _chk_morph.py 的 M6 用**同一**定义 (那里也按 de = eps0[k-1]-eps0[l-1] 取 argmin).

        ★★★ 2026-09-29 Round 141 修复：**改用收敛的 `argmin_normal`**。
          原写法「**600 个随机法向**取 argmin」实测（`_chk_pairnorm.py`，`_w2_pairnorm.log`）：
            `E(ncmp)/E(20k点最优)` 中位 **25.4**、最大 **6943**；
            夹角中位 **87.9°**，**36/66 对 > 20°**（且 20k 点本身也未收敛 ⇒ 这是**下界**）。
          而 `ncmp` 正是 `advance()` 里**变体-变体界面的 `β_h` 参考轴**
          （`windowB_surface.py` 的 `nd_ref = where(has_pair, ncl[ki,li], ...)`）
          —— 也就是 **block / colony / packet** 赖以形成的那根轴。
          ⇒ 旧行为等于**把驱动变体选择的轴对多数配对指错了约 90°**。
        `nsamp`/`seed` 参数保留只为向后兼容调用签名，**不再被使用**。
        """
        nv = len(eps0)
        tab = np.full((nv + 1, nv + 1, 3), np.nan)
        E = [np.asarray(e, float) for e in eps0]
        cons = np.full((nv + 1, nv + 1), np.nan)
        n_zero = 0
        for k in range(1, nv + 1):
            for l in range(k + 1, nv + 1):
                de = E[k - 1] - E[l - 1]
                # ★★★ R-block（2026-09-29）：**零应变差 ⇒ 该表项保持 NaN**。
                #   为什么必须守卫：板条身份层（`windowB_lath.py`）让**同变体**的
                #   两根板条各占一个场 ⇒ `eps0[k] == eps0[l]`（逐位相同）⇒ `de = 0`
                #   ⇒ `argmin_normal(C, 0)` 的泛函**恒等于 0**，任意法向都是最小值
                #   ⇒ 返回值**没有物理意义**。
                #   实测（`_bk_smoke_f3.py` 探针 B4）：**不崩**，返回
                #     `n=[0.010, 0, 0.99995]`、`E=0`、`cons=0` —— 一个随机方向。
                #   保持 NaN ⇒ `facet_nref` 回退到 `npref[k]` = **惯习面法向**；
                #   而"同变体板条面对面堆叠"的界面**正好就是惯习面**
                #   ⇒ **回退分支就是正确的那一支**（`BLOCK_DERIVATION.md` §2.3）。
                if not np.any(np.abs(de) > 1e-30):
                    n_zero += 1
                    continue
                n_p, v_p, c_p = argmin_normal_cached(C, de)
                tab[k, l] = tab[l, k] = n_p
                cons[k, l] = cons[l, k] = c_p
        if n_zero:
            print('[WindowB] ncmp：%d 对**零应变差**（同变体板条在场层面的复制）'
                  '⇒ 保持 NaN，`facet_nref` 回退 `npref`（惯习面）' % n_zero,
                  flush=True)
        return tab

    def region(self):
        # ★★ R1（2026-09-29）：空间切片并行（逐位相同；`argmin` 沿 axis=0 的次序不变）。
        #   实测（N=192）：`argmin over 13 fields` 单线程 0.216 s → ×4.1 @16 线程。
        _p = getattr(self, 'par', None)
        if _p is not None:
            return _p.argmin(self.phi).astype(np.int8)
        return np.argmin(self.phi, axis=0).astype(np.int8)

    # ================= 长大中的形核（D18，2026-09-28 用户批准并入）=================
    def nuc_cfg(self, R_nuc, t_nuc, gamma=0.15, n_init=0, p_auto=0.0,
                harden_f=1.0, sym_gap_cells=2, max_per_step=1, seed=11,
                var_rule='ed', use_fcrit=False,
                vgroup=None, nfsv=False, attach=False, attach_overlap=0.0,
                elong=1.0, along=None, prefer_end=True, nfsv_strict=True,
                block_edge=True, align_inplane=True, alt_side=True,
                force_reinit_after_event=True):
        """⚠⚠ **`harden_f=1.0` 是本函数的默认值 ⇒ 阶段③默认不可达**
        （`hardened = f_now >= 1.0` 要求母相胞数恰为 0）。见
        `WINDOWB_AUDIT_REGISTER.md` D4/A7。三种处置任选其一，**但必须显式**：
          (a) 传 `harden_f≈0.1` 才真正启用"母相硬化 ⇒ 改形核其它变体"这条阶段③规则；
          (b) 保持 1.0 并**明确声明"本次运行不启用阶段③"**；
          (c) 改默认值（会改数，须按 `R8` 重跑引用它的判据）。
        ⚠ 另：即使触发，`k` 会被覆盖为**全体变体均匀抽样** ⇒ 可能抽到未形核变体而
        静默空转（`idx.size==0` 无计数，见 A6③）。**当前实现下阶段③只能算"骨架"**。

        配置形核通道。**必须显式调用才生效** ⇒ 默认（不调用）行为与归档逐位相同。

        物理依据（全部有文献锚，见 `lit/NUCLEATION_ANCHORS.md`、`WINDOWB_LATH_GAP_ROOTCAUSE §3.3`）
        ------------------------------------------------------------------
        * **形核是必须的**：`RESEARCH_INTENT` 第 100–102 行「α′ 以板条为单位**形核 + 长大**」。
          文献明确否定"只在 t=0 撒一次核"：Khan 1990（剑桥博士论文）§5.3.2 预存缺陷密度
          "not large enough to explain the kinetics"；Villa 2014（DTU）§2.7.3 自发形核位
          `1e11–1e13 m^-3` "far too small"，"**autocatalytic nucleation dominates**"。
        * **板条厚 = 形核属性**，不是长大属性：Morito 2005 实测板条宽 0.2 µm 在 prior-γ 晶粒
          **2.3→370 µm（160×）**内"does not change"；Chakraborty 2022："the TRANSVERSE (WIDTH)
          GROWTH OF LATHS WITHIN BLOCKS **ESSENTIALLY DEPENDS ON THE NUCLEATION OF ADJACENT
          HIERARCHICAL UNITS**"。
        * **block = 同变体反复形核**：Furuhara 2008「A BLOCK IS FORMED BY **REPEATED NUCLEATION
          OF THE SAME VARIANT** OF LATHS ADJACENT TO EACH OTHER」。
        * **三阶段规则**（Morito 2022）：① 起点 = prior-β 晶界；② 主通道 = 已有板条周围由
          释放位错/应力驱动、优先**同变体**；③ 母相硬化到阈值 ⇒ 抑制同变体传播 ⇒ 改形核**其它变体**。
          ⇒ 本实现用 `harden_f`（转变分数）当阶段 ②→③ 的开关（是母相硬化的**代理量**，
          不是硬化本身 —— 见 `T27` 的判据）。
        * **两条通道**：
            `fresh`（独立）：变体取该点 `argmax_k ed[k]`（弹性能变化最小，Du 2017 的规则）。
                    ✅ **W1-4（2026-09-28）：形核判据 `f_nuc^ch > f_nuc^crit = 4γ/d` 已接线**，
                    由 `use_fcrit=True` 打开（默认 False ⇒ 逐位向后兼容）。
                    判定式 `(df + max_k ed_k) > fcrit`；`df` 经 `nucleate(df=…)` 传入。
                    ⚠ 仍**只覆盖 `fresh`**；`stack` 通道未加此判据（已知范围缺口）。
                    ⚠ `d` 取核厚 `t`，**其定义未从原文核实** ⇒ 措辞见上（不得称"实现了 Du 2017 的判据"）。
            `stack`（sympathetic/自催化）：在已有板条的**惯习面内**平移一整片处置**同变体**新核，
                    中间**留一层残余母相**（Chen 1979 LBL 博士论文：新核"spatially separate from
                    the pre-existing plate"、平行生长、"leaving a layer of retained austenite"）。
        * **参数锚点**：`t_nuc` 取 **LPBF α′ 实测板条厚 0.51–0.88 µm**（Shuai 2026,
          doi 10.3390/ma19061049）⇒ `t/Δx = 14` @Δx=50 nm，**过约束①**。
          ⚠ **记账**：文献的**形核胚**直径是 **40 nm**（Salama 2024, doi 10.1016/j.commatsci.2024.113033），
          在 Δx=50 nm 下 `t/Δx = 0.8` ⇒ **不可解析**。故本实现把 `t_nuc` 当**亚网格输入**，
          取"文献板条厚"而非"文献核径"，二者不是同一个量（Du 2017 的结论正是
          "the individual lath is not distinguishable"，厚度在其模型里不是预测量）。
        """
        self._nuc = dict(R=float(R_nuc), t=float(t_nuc), gamma=float(gamma),
                         p_auto=float(p_auto), harden_f=float(harden_f),
                         gap=int(sym_gap_cells), cap=int(max_per_step),
                         var_rule=str(var_rule),
                         use_fcrit=bool(use_fcrit),
                         # ★★★ R11（2026-09-29）：**块的"可表示性"与"界面 regime"**
                         #   两个开关。默认全关 ⇒ 与归档逐位相同。
                         #
                         # 【为什么要 `nfsv`（new field, same variant）】
                         #   `stack` 通道原来是 `seed_plate(k, …)` —— **同一个场**。
                         #   而块的定义就是「同变体反复形核」（Furuhara 2008：
                         #   "a block is formed by REPEATED NUCLEATION OF THE SAME
                         #   VARIANT of laths adjacent to each other"）。
                         #   同变体 + 同一个场 ⇒ 第二个核只是**加厚第一片**，
                         #   永远得不到"多根板条"⇒ **块在这一方案下结构上不可表示**
                         #   （本仓库 A-5 的判定）。
                         #   ⇒ `nfsv=True` 时：选中已有场 `k` 后，改播进一个**同变体
                         #     且当前为空**的新场 `j`；找不到就用 `k`（并计数）。
                         #   需要一个 `vgroup`（`{场号: 变体号}`）才能知道谁同变体；
                         #   传 `None` ⇒ 该开关无效（并计数，不静默）。
                         #
                         # 【为什么要 `attach`，以及它与 Chen 1979 的关系】
                         #   原实现在惯习面内平移一整片，**中间留一层残余母相**
                         #   （`sym_gap_cells=2`），文献锚是 Chen 1979（LBL 博士论文）：
                         #   新核 "spatially separate from the pre-existing plate"、
                         #   平行生长、"leaving a layer of retained austenite"。
                         #   ⚠ **那是 Fe-Ni 马氏体**（母相是奥氏体 γ）。
                         #   本体系是 **Ti-6Al-4V 的 β→α′**，而本项目的 C-1 判据
                         #   （Cahn 润湿）给出：`γ_RS(θ≤5°) ≤ 0.277 < 2γ_α′β ≈ 0.30`
                         #   ⇒ **不润湿 ⇒ 干晶界才是稳定态**；
                         #   且 `P-2` 实测（`auto` 臂 ψ 单调退湿到 0.09）与之一致。
                         #   ⇒ **两条结论都对，但对不同体系。** `attach=True` 就是
                         #     "按 C-1 选干晶界"这一 regime：新核与源板条**共用一张
                         #     界面**（近端面落在源板条边界上、再咬入 `attach_overlap`），
                         #     于是 `seed_plate` 的真 SDF + `argmin` 把界面定在**中面**
                         #     ⇒ 一张完整的阶梯界面，而不是两列错开的阶梯夹一层 β。
                         #   `attach_overlap` 的经验值（同分辨率 Δx=62.5 nm、
                         #   同 n*、N=96、200 步的剂量–响应实测）：
                         #     `o = 1Δx = 62.5 nm` ⇒ 界面完整（β 夹层占比 0.13–0.15
                         #     = 预摆对照底噪），`o = 0` ⇒ 只有 0.29–0.62（阶梯错位）；
                         #     `o = 1.5Δx` **过大**，会把先形成的板条撕碎。
                         #   ⚠ **这是模型选择，不是从自由能推出来的**（记账红线）。
                         vgroup=({int(a): int(b) for a, b in vgroup.items()}
                                 if vgroup is not None else None),
                         nfsv=bool(nfsv), attach=bool(attach),
                         attach_overlap=float(attach_overlap),
                         # ★★★ R12：**核的形状**。原先两条通道都调
                         #   `seed_plate(k, cc, nrm, R, t)` —— **不传 `elong`/`along`
                         #   ⇒ 播的是圆盘**（面内足迹 `πR²`）。
                         #   实测代价（`--arm eng`，R=320 nm，200 步）：
                         #     第一次引擎事件的 F3 接触面 **0.3906 µm²**
                         #     —— 正好是 `π·320² = 0.3217 µm²` 的量级，
                         #     而驱动层 `_seed_next` 传了
                         #     `elong=L/W=3.75, along=a_ax, flat_end=True`
                         #     ⇒ 足迹 640×2400 = **1.536 µm²**，同一步给 **1.5174 µm²**。
                         #   ⇒ 终态 `f3_area` 1.0687 vs 7.6448（**小 7 倍**）、
                         #     `Vt` 1.1580 vs 2.6897、`nslab_n` 只到 5。
                         #   机理与 `LR1` 的旧结论一致：**块被锁在种子形状上**
                         #   （圆盘种子只能给出长/宽≈1 的等轴块）。
                         #   `elong=1.0 + along=None` ⇒ `seed_plate` 走原分支
                         #   ⇒ **与改动前逐位相同**（由 `_bk_nuc_identity.py` 的 U-1 保证）。
                         elong=float(elong),
                         along=(None if along is None
                                else np.asarray(along, float).copy()),
                         # ★★★ R13：`attach` 下**优先抽端片**。只在 `attach=True`
                         #   时生效 ⇒ `attach=False`（默认）**完全不变**。
                         #   动机（实测 `eng2`，200 步）：引擎随机抽 `k`，抽到**内层片**
                         #   时两侧都被别的场占住 ⇒ `cover` 守卫拒掉 ⇒ 该次事件作废
                         #   ⇒ 阶梯进度**慢半拍**（step 90 时 3 片，而驱动层方案 4 片）。
                         #   只有**端片**才有自由外侧。"端片"的判据是
                         #   "沿惯习面法向的质心投影取到极值"——它假定同组板条
                         #   **共用一张惯习面**（正是 block 的情形）。
                         prefer_end=bool(prefer_end),
                         # ★ R14：`nfsv` 找不到空场时**拒绝**该事件（而不是回退到 k）。
                         #   只在 `nfsv=True` 时被读到 ⇒ 默认路径不变。
                         nfsv_strict=bool(nfsv_strict),
                         # ★ R17：`attach` 落位基准用**整块外缘**（而非源板条自身外缘）。
                         #   只在 `attach=True` 时被读到 ⇒ 默认路径不变。
                         block_edge=bool(block_edge),
                         # ★ R18：新片的**面内中心**对齐到"整块的面内中心"
                         #   （而不是源板条自己的质心）。只在 `attach=True` 时读到。
                         align_inplane=bool(align_inplane),
                         # ★ R21：`attach` 下**交替选端**（对齐驱动层 `_seed_next` 的
                         #   `side = +1 if j%2==0 else -1`）。只在 `attach=True` 时读到。
                         alt_side=bool(alt_side),
                         # ★ R22：有形核事件时是否强制 reinit（默认 True = 归档行为）。
                         #   `False` ⇒ 与驱动层 `_seed_next` 一致（后者不置该标志）。
                         force_reinit_after_event=bool(force_reinit_after_event),
                         rng=np.random.default_rng(seed))
        # ★★ 记账（Round 63 接线；**Round 84 更正依据**——`ReferenceAudit` #14）：
        #   `p_auto` **已接线并使用**（见下面 sympathetic 分支的 `_gain`）。
        #   ⛔ **但它的函数形式没有一手文献依据**：原写"取自 Bhadeshia
        #      *Theory of Transformations in Steel* (2023) §5 式 (5.24) 的形状"，
        #      而文献核查确认**该书正文不在出版社预览内、该式无法核实**
        #      （`docs/refcheck/REFERENCE_AUDIT.md` #14）；最接近的一手来源
        #      **Khan 1990 §5.3.2** 给的是 `dN = dN_i + d(p·f)`、`N_i = (1−f)N_V⁰`
        #      —— **括号里没有分母**，也没有 `4f(1−f)` 这个形状。
        #   ⇒ **`p_auto` 必须读作「本项目自设的无量纲增益」**，不是文献参数：
        #      增益 = 1 + p_auto · 4f(1−f)   （f = 0.5 处为 1+p_auto）
        #      定义：「转变量过半时，sympathetic 形核的**尝试次数**相对无自催化情形增加的倍数」。
        #   ⚠ 实测（`_t24pa0.log` vs `_t24pa6.log`，同规格只差 `p_auto=0/6`）：block 13 vs 13、
        #      中位 508.3 vs 508.6 nm ⇒ **在下游形态层面无分辨力**（且见 A5：它改的是"尝试次数"、
        #      还被 `cap` 卡死、`round()` 量化、`f=0` 时 `gain≡1`）。
        #   ⇒ **不要再用 `p_auto` 作为"标定自催化强度"的说法**；要标定请先给出有依据的率律。
        self._nuc_events = []
        self._nuc_n_init = int(n_init)
        if n_init > 0:
            self._nuc_place_initial(int(n_init))

    def _nuc_place_initial(self, n):
        """t=0 撒下 `n` 个**待机**核（不立即 `seed_plate`：位点合法即可，激活时再种）。"""
        c = self._nuc
        rng = c['rng']
        R, t = c['R'], c['t']
        pad = R + 2 * self.dx
        sites, ns = [], 0
        for _ in range(n * 20):
            if ns >= n:
                break
            ctr = rng.random(3) * (self.L - 2 * pad) + pad
            k = int(rng.integers(1, self.nreg))
            sites.append((k, ctr))
            ns += 1
        self._nuc['sites'] = sites

    def _nuc_safe_mask(self, R_nuc, gap_cells=2):
        """到任何非母相胞的欧氏距离 ≥ `R_nuc + gap` 的母相胞（用 EDT，避免手工盒扫描）。"""
        from scipy import ndimage
        par = (self.region() == 0)
        if not par.any():
            return np.zeros_like(par), par
        dt = ndimage.distance_transform_edt(par) * self.dx
        return (dt >= (R_nuc + gap_cells * self.dx)) & par, par

    def nucleate(self, ed, R_nuc=None, t_nuc=None, n_fresh=0, n_stack=0,
                 f_now=0.0, drive_min=None, df=0.0):
        """**每步调用一次**：按三阶段规则新增核。返回本轮新种下的 `[(k, mode)]`。

        `ed` = `elastic_driving()` 的返回（`(nreg,N,N,N)`）。
        **只有先 `nuc_cfg()` 才有效**（否则本方法不会被调用 —— 调用方负责）。
        """
        c = getattr(self, '_nuc', None)
        if c is None:
            return []
        R = c['R'] if R_nuc is None else float(R_nuc)
        t = c['t'] if t_nuc is None else float(t_nuc)
        rng = c['rng']
        nv = self.nreg - 1
        out = []
        cap = max(1, c['cap'])
        # ---------- 形核判据 `f_nuc^crit = 4γ/d`（Du 2017）
        # ✅ **W1-4（2026-09-28）：本判据已接线**，由 `nuc_cfg(use_fcrit=True)` 打开。
        #   * 判定式：`(df + max_k ed_k) > fcrit`，其中 `fcrit = 4γ/t`（`drive_min` 给了则覆盖）；
        #   * `df` 由调用方经 `nucleate(..., df=Δf)` 传入；
        #   * 被拒的位点计入 `dbg['fcrit']`（**显式可诊断**，不再静默）。
        #   ⚠ **默认 `use_fcrit=False` ⇒ 完全不比较 ⇒ 与归档行为逐位相同**（启用会改数 ⇒ `R8`）。
        #   ⚠ 历史（留痕）：Round 86 时本条是"**算了却从不比较**"——代码算了 `fcrit` 却从未使用，
        #     而 docstring 声称"按 `f_nuc^ch > f_nuc^crit` 筛选形核点" ⇒ 未实现的声称。
        #     该问题**已于本轮修复**；`gamma` / `drive_min` 现在**确有作用**（当 `use_fcrit=True`）。
        #   ⚠ **`d` 的定义未从 Du 2017 原文核实**（本实现取核厚 `t`）
        #     ⇒ 措辞只能是"实现了登记表 §9 所载的判定式"，**不得**写成"实现了 Du 2017 的判据"。
        fcrit = 4.0 * c['gamma'] / max(t, 1e-30)
        if drive_min is not None:
            fcrit = float(drive_min)
        nrm_all = getattr(self, '_npref_list', None)

        # ---------- ① 待机核：按 `argmax_k ed` 激活（Du 2017 的"弹性能变化最小"）
        sites = c.get('sites', [])
        if sites and n_fresh > 0:
            # ★★ Round 103 修（`WINDOWB_AUDIT_REGISTER.md` A8）：原来写
            #   `cl = np.clip(ed[1:], None, None)` —— **两端都是 `None` ⇒ 恒等变换**
            #   （实测 `np.clip([-1,2],None,None) == [-1,2]`），却每步**复制**一整个
            #   `(nv,N³)` 数组（N=96、nv=12 时 ~85 MB），而本函数只用到 3 个数。
            #   变量名 `cl` 是"只留有利变体"的残留 —— 正是 **D1（`4γ/d` 判据未接线）**
            #   留下的现场痕迹。
            #   ⇒ 改成**基本切片**：`ed[1:]` 返回**视图**（零拷贝），数值逐位相同。
            cl = ed[1:]                                         # 视图，不是拷贝
            nfr_done = 0
            for i in range(len(sites) - 1, -1, -1):
                # ★ 记账（T27 冒烟抓到）：原写法只受 `cap` 约束、**不受 `n_fresh` 约束**
                #   ⇒ 一次调用就把名额全用光，后面的 `stack` 通道永远拿不到名额
                #   ⇒ 实测 `stack=0`（sympathetic/block 通道静默失效）。
                if len(out) >= cap or nfr_done >= n_fresh:
                    break
                _, ctr = sites[i]
                ci = np.clip((ctr / self.dx).astype(int), 0, self.N - 1)
                drv = cl[:, ci[0], ci[1], ci[2]]
                # ★ Round 77：核的**变体选择规则**（两种都有文献锚，可切换；默认 `ed`）
                #   `ed`     —— `argmax_k ed[k]`（弹性能变化最小；Du 2017 波鸿博士论文）
                #   `random` —— **随机抽 1 个**（Salama et al. 2024, Comput. Mater. Sci. 241,
                #               113033 的配方是"每个形核点随机抽 2 个 K-S 变体"）
                #   动机（实测）：`M6p` p25 在形核档退化到 **23.9°–25.4°，超 D16c 门槛 20°**
                #   ⇒ 需要检验"是不是 `argmax ed` 这条规则把取向选坏了"。
                #   ⚠ 默认仍是 `ed` ⇒ **归档行为不变**。
                # ★★ Round 93 修（`WINDOWB_AUDIT_REGISTER.md` C2，**实测语义**）：
                #   `np.argmax` 遇到 NaN **返回第一个 NaN 的下标、不报错**
                #   （实测 `argmax([nan,1,3])=0`、`argmax([1,nan,3])=1`）
                #   ⇒ 若 `ed` 含 NaN，会**静默选中一个 NaN 变体**。
                #   `ed` 的 NaN 来源：`eps0`/`sigma_ext`/`C` 自带 NaN、
                #   `aniso_elastic=True` 的极化迭代发散、或近奇异声学张量。
                #   ⇒ 这里加**显式守卫**：非有限就跳过该位点并计数，绝不静默选一个 NaN 变体。
                _ok_drv = np.isfinite(drv)
                if not bool(_ok_drv.all()):
                    _c3 = c.setdefault('dbg', dict(att=0, oob=0, cov=0, exc=0, ok=0, nocand=0))
                    _c3['nan_ed'] = _c3.get('nan_ed', 0) + 1
                    continue
                # ★★★ W1-4（2026-09-28）：**接线 `f_nuc^crit = 4γ/d` 判据**（登记表 §9 D1/A1）。
                #   默认 `use_fcrit=False` ⇒ **完全不比较** ⇒ 与归档行为**逐位相同**。
                #   判定式：`(df + max_k ed_k) > 4γ/d`（`drive_min` 给了就覆盖 `4γ/d`）。
                #   为什么是 `+`：`ed` 存的是"弹性能**变化**"，而上面用 `argmax_k ed` 选
                #   "弹性能变化**最小**"的变体 ⇒ `ed` 越大越有利 ⇒ 驱动力 = `df + max_k ed_k`，
                #   与选法自洽。
                #   ⚠ **`d` 的定义未从 Du 2017 原文核实**，本实现取核厚 `t`
                #     ⇒ 措辞只能是"实现了登记表 §9 所载的判定式"，
                #       **不得**写成"实现了 Du 2017 的判据"（措辞红线，见 MEASUREMENT_SPEC R10 同类纪律）。
                #   ⚠ **只覆盖 `fresh` 通道**；`stack`（sympathetic）通道**未**加该判据 —— 这是**已知的范围缺口**，
                #     不得把本实现说成"两条通道都过了驱动力判据"。
                if c.get('use_fcrit', False):
                    _dmax = float(np.max(drv))
                    if (float(df) + _dmax) <= fcrit:
                        _c4 = c.setdefault('dbg', dict(att=0, oob=0, cov=0, exc=0,
                                                       ok=0, nocand=0))
                        _c4['fcrit'] = _c4.get('fcrit', 0) + 1
                        continue
                # ★★★ W1-6（2026-09-28，**用户决策 D-2**）：变体选择规则加 **`doublet`**。
                #   文献配方（Salama et al. 2024, Comput. Mater. Sci. 241, 113033）：
                #     **每个形核点随机抽 2 个 K-S 变体**（不重复）。
                #   动机（实测）：`M6p` p25 在形核档落到 **19–31°（随构型）**，**超 D16c 门槛 20°**
                #     ⇒ 需要检验"是不是 `argmax ed` 这条规则把取向选坏了"。
                #   ⚠ **向后兼容硬约束**：`'ed'`（默认）下 `_ks` 只有 1 个元素、**且不消耗 `rng`**
                #     （原式在 `'ed'` 下也不调 `rng`）⇒ 默认路径**逐位不变**（由 `_chk_w16.py` D-1 证明）。
                #   ⚠ `n_fresh` 限的是**事件数**（与现有一致）⇒ `doublet` 下每个位点占 **2 个** `n_fresh` 名额。
                _rule = c.get('var_rule', 'ed')
                if _rule == 'random':
                    _ks = [int(rng.integers(1, nv + 1))]
                elif _rule == 'doublet':
                    _ks = [int(x) for x in rng.choice(np.arange(1, nv + 1), size=2,
                                                      replace=False)]
                else:                                   # 'ed'（默认）
                    _ks = [int(np.argmax(drv)) + 1]
                # ★★ Round 89 修（`WINDOWB_AUDIT_REGISTER.md` A2，**实测已证**）：
                #   原来 `fresh` 通道**没有任何重叠守卫**，而 `seed_plate` 的
                #   `phi[j] = max(phi[j], -sdf)` 会把新核盘内的**已有变体删掉**——
                #   实测把 k=2 的核种在已有 k=1 盘的芯部 ⇒ k=1 由 2912 胞掉到 2496 胞
                #   （**−416 胞 / −14.3%**），而 `T27` 的 N-6 判据（聚合区域数）看不见。
                #   唯一现成的守卫工具 `_nuc_safe_mask()` 全仓零调用（死代码），
                #   故此处**直接复用 stack 通道已验证的 `cover` 判据**（几何与 `seed_plate`
                #   的 sdf 定义完全一致，审计已确认"不是近似"）。
                _any_ok = False
                for _vidx, kk in enumerate(_ks):
                    if len(out) >= cap or nfr_done >= n_fresh:
                        break
                    _nrm = np.asarray(self._npref_of(kk), float)
                    _nrm = _nrm / (np.linalg.norm(_nrm) + 1e-300)
                    # ★★★ W1-6 修（Round 134，`_chk_w16.py` D-2 抓到）：
                    #   **同一站点的多个变体不能占同一个盘** —— 第一个变体种下后，
                    #   第二个变体的 `cover` 守卫会发现那个盘已被**兄弟核**占据 ⇒ **必然被挡**
                    #   （实测 `doublet` 退化成"1 事件/站点 + 一次浪费的尝试"，阻挡 7 vs `ed` 的 1）。
                    #   ⇒ 除第一个变体外，其余变体在**面内**错开 `2R + gap`（两盘相切不重叠）后再试。
                    #   ⚠ 对 `'ed'`（`_ks` 长度 1）`_vidx` 恒为 0 ⇒ `_cands` 恒为 `[ctr]`
                    #     ⇒ 与旧写法**逐位等价**（由 `_chk_w16.py` D-1b 证明）。
                    _cands = [ctr]
                    if _vidx > 0:
                        _u = np.array([1.0, 0.0, 0.0])
                        if abs(float(_u @ _nrm)) > 0.9:
                            _u = np.array([0.0, 1.0, 0.0])
                        _u = _u - (_u @ _nrm) * _nrm
                        _u = _u / (np.linalg.norm(_u) + 1e-300)
                        _v = np.cross(_nrm, _u)
                        _off = 2.0 * R + c['gap'] * self.dx
                        _cands = _cands + [ctr + _off * (np.cos(_t) * _u + np.sin(_t) * _v)
                                           for _t in np.linspace(0.0, 2.0 * np.pi, 8,
                                                                 endpoint=False)]
                    _placed = False
                    for _cc in _cands:
                        _rel = self.XYZ - _cc
                        _dd = _rel @ _nrm
                        _rp = np.linalg.norm(_rel - _dd[..., None] * _nrm, axis=-1)
                        _cover = (np.abs(_dd) <= t / 2) & (_rp <= R)
                        if (not bool(_cover.any())) or \
                                (not bool((self.region()[_cover] == 0).all())):
                            continue                     # 该候选位置不行 ⇒ 试下一个
                        try:
                            self.seed_plate(kk, _cc, _nrm, R, t)
                            _placed = True
                            _any_ok = True
                            out.append((kk, 'fresh'))
                            nfr_done += 1
                            c['n_activated'] = c.get('n_activated', 0) + 1
                        except ValueError:
                            continue
                        break
                    if not _placed:
                        _c2 = c.setdefault('dbg', dict(att=0, oob=0, cov=0, exc=0, ok=0, nocand=0))
                        _c2['fresh_blocked'] = _c2.get('fresh_blocked', 0) + 1
                        # ⚠ `doublet` 下这里是**试下一个变体**，不再跳过整个位点
                        continue
                if _any_ok and i < len(sites):
                    sites.pop(i)                        # 位点用过即移除（只移一次）
        c['pending_fresh'] = len(sites)

        # ---------- ② sympathetic：母相未硬化时优先**同变体**侧向邻位
        if n_stack > 0:
            # ★★★ 2026-09-28（Round 63）**接线 `p_auto`**：自催化项的**无量纲**形式
            #   Bhadeshia, *Theory of Transformations in Steel* (2023) §5 式 (5.24)：
            #       N_V = [ N_V⁰ + p_a·V_V^{α′}/(…) ] · ( 1 − V_V^{α′} )
            #   其中 `(…)` 的分母我**没有读到**（子代理只摘了式子的骨架）⇒ **不臆造**。
            #   本实现只取该式的**形状** `V_V^{α′}(1−V_V^{α′})`（在 f=0.5 处取最大 1，
            #   故用 `4f(1−f)` 归一化 ⇒ **不含任何自由常数**），并把它定义成
            #   sympathetic 事件数的**增益**：
            #       gain = 1 + p_auto · 4·f·(1−f)        （f = 0.5 处 gain = 1 + p_auto）
            #   ⇒ **`p_auto` 的定义（先写死，不得事后挪动）：**
            #      「转变量过半时，自催化形核速率相对**无自催化**情形增加的**倍数**」。
            #   ⇒ `p_auto = 0` 时 `gain ≡ 1` ⇒ **与接线前逐位相同**（向后兼容，
            #     已由 `T27` N-2 的"默认不生效"保证同一类性质）。
            #   ⛔ **原"标定靶：block:lath ≈ 26（Morito 2009）"已撤回**
            #     （2026-09-28，`MEASUREMENT_SPEC R10` / `REFERENCE_AUDIT` #6）：
            #     **那是钢**（IF 钢 Fe-0.0049C-3.14Mn…1473 K 水淬），与 Ti-6Al-4V 跨材料。
            #   ✅ **同材料同工艺的靶只有两个**：板条厚 **0.51–0.68 µm**
            #     （Shuai 2026，P=173 W 时达 0.88）；几何长:厚 **≈ 9:1**
            #     （Wang 2026，8.1±2.0 × 0.9±0.4 µm）。
            #   ⚠ `block:lath` 仍可作为**本项目自设的机制自检量**（不用文献靶），
            #     因为 **LPBF Ti-64 的 block/packet 尺寸在公开文献里查不到**。
            _gain = 1.0 + c['p_auto'] * 4.0 * max(0.0, min(1.0, f_now)) * (1.0 - max(0.0, min(1.0, f_now)))
            _nst = int(round(n_stack * _gain))
            # ★★ Round 65 诊断计数（回答"为什么 `stack` 落位被拒"）：
            #   `att` 尝试次数、`oob` 越界、`cov` 被 `cover` 守卫拒、`exc` `seed_plate` 抛错、
            #   `ok` 成功。**只读记账、不改行为**（默认不影响任何结果）。
            _dbg = c.setdefault('dbg', dict(att=0, oob=0, cov=0, exc=0, ok=0, nocand=0))
            hardened = f_now >= c['harden_f']
            reg = self.region()
            ks = [k for k in np.unique(reg) if k > 0]
            if ks:
                for _ in range(_nst):
                    if len(out) >= cap:
                        break
                    # ★★ Round 84 修（`WINDOWB_AUDIT_REGISTER.md` A4）：
                    #   原来 `reg` 是**循环外的一次快照**，而 `seed_plate` 在同一调用内就改
                    #   `self.phi` ⇒ `cover` 守卫**看不见同一次调用里刚种下的核**；
                    #   且 k 每次迭代重抽 ⇒ 第二个事件可落在第一个上、甚至**不同变体把前一个抹掉**。
                    #   `T24/T27` 传 `max_per_step=8` ⇒ 每调用最多 8 个事件，风险实存。
                    reg = self.region()
                    k = int(ks[rng.integers(0, len(ks))])
                    if hardened:                                # 阶段③：换变体
                        k = int(rng.integers(1, nv + 1))
                    m = (reg == k)
                    idx = np.argwhere(m)
                    if idx.size == 0:
                        continue
                    # ★★★ R11：**同变体 ⇒ 新场**（`nfsv`）。默认关 ⇒ 下面
                    #   `k_new == k`，与归档**逐位相同**。
                    k_new = k
                    if c.get('nfsv', False) and not hardened:
                        vg = c.get('vgroup')
                        if vg is None:
                            _dbg['nfsv_novgroup'] = _dbg.get('nfsv_novgroup', 0) + 1
                        else:
                            _v = vg.get(k)
                            for _j in range(1, nv + 1):
                                if _j == k or vg.get(_j) != _v:
                                    continue
                                if not bool((reg == _j).any()):
                                    k_new = _j
                                    break
                            if k_new == k:
                                _dbg['nfsv_nofield'] = _dbg.get('nfsv_nofield', 0) + 1
                                # ★★★ R14：**没有空场 ⇒ 必须拒绝该事件，不得回退**。
                                #   实测（`eng3`，200 步，`prefer_end` 已开）：
                                #     step 150 时 6 片全在位（✅ 端片优先奏效），
                                #     但 step 180 又触发一次 —— 6 个场已被占满，
                                #     `nfsv` 找不到空场 ⇒ 回退成 `k_new = k`
                                #     ⇒ **往已有场里再播一片** ⇒ `nslab_n` 变成 7、
                                #     `runs=3/6/5/4/3/1/2`（**场 3 出现两次**）、
                                #     `Vt` 冲到 3.05（越出预登记的 [2.4,2.9]）。
                                #   物理含义：「空场用完」= **模型能表示的板条数到顶**
                                #   （`nv` 是个表示上限，不是物理上限）。此时
                                #   **静默改播到已有场**会把"表示不了"伪装成"又长了一片"
                                #   —— 必须**拒绝 + 计数**，让缺口显式可见。
                                #   ⚠ 只在 `nfsv=True` 时生效 ⇒ 默认路径不变。
                                if c.get('nfsv_strict', True):
                                    continue
                            else:
                                _dbg['nfsv_ok'] = _dbg.get('nfsv_ok', 0) + 1
                    c0 = (idx.mean(0) + 0.5) * self.dx
                    # ★★★ R16：**`attach` 下改用稳健中心（中位数）**。
                    #   为什么：`c0 = idx.mean(0)` 用的是**该场全部胞**的质心，
                    #   而场里总有 **1–2 体素的孤立碎点**散在盒子里（`eng2` 的
                    #   `ncomp_max` 到 14、`eng5` 到 18，而 `ncompbig_max` 恒为 1）。
                    #   碎点把**均值**拉偏 ⇒ 新片的**面内中心**跟着偏 ⇒ 两张板条
                    #   只**部分**重叠 ⇒ 界面一部分贴、一部分夹母相
                    #   ⇒ `V-7b`（β 占比）变差、`V-3g` 变大（界面被推着走）。
                    #   **驱动层 `_seed_next` 不受此影响**：它把新片放在**原始盒心**
                    #   `c0` 上、只沿 n* 平移。
                    #   实测对照（同配置、同 200 步）：
                    #     `gs5`（驱动层）  V-7b 最差 0.15 / V-3g 0.024 Δx
                    #     `eng5`（引擎，均值中心） V-7b 最差 1.00 / V-3g 0.439 Δx
                    #   ⇒ 中位数对少数离群胞**免疫**；`attach_only=True` 保证
                    #     只改新 regime（`attach=False` 时用原均值 ⇒ 逐位不变）。
                    c0_at = None
                    if c.get('attach', False):
                        c0_at = (np.median(idx, axis=0) + 0.5) * self.dx
                        _sh = float(np.linalg.norm(c0_at - c0)) / self.dx
                        _dbg['c_shift_max_dx'] = max(
                            _dbg.get('c_shift_max_dx', 0.0), _sh)
                        c0 = c0_at
                    nrm = np.asarray(self._npref_of(k), float)
                    nrm = nrm / np.linalg.norm(nrm)
                    pos = (idx.astype(float) + 0.5) * self.dx
                    # ★★★ R11：**共用一张界面**（`attach`）。默认关 ⇒ 走下面的
                    #   16 方向 × 4 档偏移搜索，与归档**逐位相同**。
                    if c.get('attach', False):
                        # ★★★ R13：**优先抽端片**（只有端片有自由外侧）。
                        #   随机抽到的 `k` 若是内层片，`attach` 两侧都会被别的场占住
                        #   ⇒ `cover` 守卫拒 ⇒ 本次事件作废（`eng2` 实测慢半拍）。
                        #   ⚠ 这里是**改 `k` 的抽样**，不改几何；`attach=False` 时
                        #     整段不执行 ⇒ 归档行为不变。
                        if c.get('prefer_end', True) and len(ks) >= 2:
                            _pr = {}
                            for _j in ks:
                                _i2 = np.argwhere(reg == _j)
                                if _i2.size:
                                    _pr[_j] = float(((_i2.mean(0) + 0.5)
                                                     * self.dx) @ nrm)
                            if len(_pr) >= 2 and k in _pr:
                                _lo = min(_pr, key=_pr.get)
                                _hi = max(_pr, key=_pr.get)
                                if k not in (_lo, _hi):
                                    k = _lo if rng.random() < 0.5 else _hi
                                    _dbg['end_pref'] = _dbg.get('end_pref', 0) + 1
                                    m = (reg == k)
                                    idx = np.argwhere(m)
                                    if idx.size == 0:
                                        continue
                                    c0 = (idx.mean(0) + 0.5) * self.dx
                                    pos = (idx.astype(float) + 0.5) * self.dx
                        _pn = pos @ nrm
                        # ★★★ R17：**落位基准改成"整块外缘"**（`block_edge`，默认开）。
                        #   动机（`eng5`/`eng6` 的共同模式，实测）：按堆叠顺序读相邻对，
                        #   **只有最外两张界面是干净的**（β 占比 0.13–0.15），
                        #   **中间三张全脏**（0.43–1.00）。这正是"**新片被插进块内部**"
                        #   的特征：两端是自由外侧（贴上去就成一张干界面），
                        #   中间的界面在后续事件里被夹着反复挤压 ⇒ 被推开成 β 夹层。
                        #   机理：`_pn` 是**源板条自身**的胞投影。若抽到的源板条
                        #   **不是**几何上最外那张（`prefer_end` 按**质心**取极值，
                        #   而质心会被碎点与不均匀长大带偏），它的"外缘"就在块内部
                        #   ⇒ 新片被插到内部。
                        #   ⇒ 改用**全部 α′ 胞**的投影极值（= 整块外缘）作基准；
                        #     并把"源板条外缘比整块外缘内缩多少"记进
                        #     `dbg['edge_gap_max_dx']`（**这是本诊断的可证伪点**：
                        #     若它 ≈ 0，说明源板条一直就是最外那张，本条修法无意义）。
                        #   ⚠ `block_edge=False` 或 `attach=False` ⇒ 原路径 ⇒ 逐位不变。
                        if c.get('block_edge', True):
                            _bi = np.argwhere(reg > 0)
                            _ball = ((_bi.astype(float) + 0.5) * self.dx) @ nrm
                            _e_hi, _e_lo = float(_ball.max()), float(_ball.min())
                            # ★★ R18 修（R17 的设计错误）：原式取**大**者
                            #   `max(_e_hi-_pn.max(), _pn.min()-_e_lo)`。
                            #   当源板条**正确地**处在某一端时，它那一侧的差 ≈ 0，
                            #   而**另一侧的差 = 整块跨度 − 一片厚** ⇒ `max` 选中的
                            #   正是这一项 ⇒ 读出的 14.61（≈913 nm）**其实是"块有多厚"**，
                            #   不是"源板条内缩多少"。
                            #   ⇒ 正确口径是取**小**者：源板条若真在最外端，
                            #     它至少有一侧与整块外缘齐平 ⇒ min ≈ 0。
                            _gp = min(_e_hi - float(_pn.max()),
                                      float(_pn.min()) - _e_lo) / self.dx
                            _dbg['edge_gap_min_dx'] = min(
                                _dbg.get('edge_gap_min_dx', 9.9), _gp)
                            # ★★★ R18：**面内对齐到"整块的面内中心"**（`align_inplane`）。
                            #   依据（`eng8` 的**逐对** F3 面积表，逐点实测）：
                            #     step 30  1-2=1.535                       （一张满界面）
                            #     step 60  1-2=1.547  1-3=1.542            （两张，都满）
                            #     step 70→90  1-3 涨到 **2.043**           ← **超过一张满界面**
                            #     step 90  3-4=1.507
                            #     step 100 1-3 **−0.672**  3-4 **+0.329**  ← 界面在迁移
                            #     step 130 3-4 **−0.890**，且 **2-3=0.003 出现**
                            #   ⇒ 接触拓扑**不是一条链**（`1-2`、`1-3`、`2-3` 同时存在，
                            #     即 1/2/3 互相接触）⇒ **板条在面内没对齐**（横向错开）。
                            #   `1-3` 涨到 2.04 > 一张满界面（≈1.54）就是铁证：
                            #   两片不只在一个面上接触。
                            #   根因：新片的**面内中心**取的是**源板条自己的质心**
                            #   `c0`。板条沿 `a` **不对称长大** ⇒ 质心在面内漂移
                            #   ⇒ 新片跟着偏。而驱动层 `_seed_next` 把新片放在
                            #   **原始盒心**上、只沿 n* 平移 ⇒ 面内**永远对齐**。
                            #   ⇒ 改用**整块 α′ 的面内中心**：
                            #     `_ip = c_blk − (c_blk·nrm)·nrm`（面内部分），
                            #     再沿 n* 平移到 `_edge + side·(t/2 − o)`。
                            #     注意 `_ip·nrm ≡ 0`（构造如此）⇒ 沿 n* 的位置
                            #     完全由 `_edge` 定，不会被面内中心影响。
                            if c.get('align_inplane', True):
                                _cb = ((_bi.astype(float) + 0.5) * self.dx).mean(0)
                                c0 = _cb - float(_cb @ nrm) * nrm
                        else:
                            _e_hi, _e_lo = float(_pn.max()), float(_pn.min())
                        done = False                 # ★ 必须先初始化：下面 `if done`
                        # ★★★ R21：**交替选端**（`alt_side`，默认开；只在 `attach` 下）。
                        #   依据（R20 逐条对齐后的**唯一剩余差别**）：
                        #     板条几何 / 法向 / 面内中心 / 沿 n* 的落位公式 **全部等价**，
                        #     只剩选端方式：驱动层 `_seed_next` **严格交替**
                        #     （`side = +1 if j%2==0 else -1`），而这里**总是先试 `+1`**
                        #     ⇒ 成功就**一直在同一端**加片。
                        #   ⚠ **本条只有排除法支撑，没有机理** ——
                        #     "单端堆叠为什么会造成过接触(2.2)/非链拓扑"我讲不出来。
                        #     故预登记里写明：**若不改变结果，则差别在别处**，不得在此打转。
                        #   ⚠ `alt_side=False` 或 `attach=False` ⇒ 原路径 ⇒ 逐位不变。
                        _sides = ((1.0, -1.0) if not c.get('alt_side', True)
                                  else ((1.0, -1.0) if (_dbg.get('ok', 0) % 2 == 0)
                                        else (-1.0, 1.0)))
                        for _side in _sides:         #   在"一个都没放成"时也要能求值
                            if done:
                                break
                            _edge = _e_hi if _side > 0 else _e_lo
                            cc = c0 + ((_edge - float(c0 @ nrm))
                                       + _side * (t / 2.0
                                                  - c.get('attach_overlap', 0.0))) * nrm
                            cc = cc - self.L * np.floor(cc / self.L)   # 周期折回
                            if np.any(cc < R + 0.3e-6) or np.any(cc > self.L - R - 0.3e-6):
                                _dbg['oob'] += 1
                                continue
                            rel = self.XYZ - cc
                            dd = rel @ nrm
                            rp = np.linalg.norm(rel - dd[..., None] * nrm, axis=-1)
                            cover = (np.abs(dd) <= t / 2) & (rp <= R)
                            if not bool(cover.any()):
                                _dbg['empty'] = _dbg.get('empty', 0) + 1
                                continue
                            # ★ 守卫**按 regime 放宽**：允许落在母相(0)**或源板条 k**
                            #   上 —— 后者正是"共用一张界面"。绝不能落在**别的**场上。
                            _okr = reg[cover]
                            if not bool(np.isin(_okr, (0, k)).all()):
                                _dbg['cov'] += 1
                                continue
                            try:
                                self.seed_plate(k_new, cc, nrm, R, t,
                                                elong=c.get('elong', 1.0),
                                                along=c.get('along'),
                                                flat_end=True)
                                out.append((k_new, 'attach'))
                                _dbg['ok'] += 1
                                _dbg['attach_ok'] = _dbg.get('attach_ok', 0) + 1
                                done = True
                            except ValueError:
                                _dbg['exc'] += 1
                        if done:
                            continue                    # 本事件已完成，下一个事件
                    # ★ 记账（T27 第 2 版抓到）：原来只试 **1 个偏移距离 × 8 个方向**，
                    #   而 `off = 半展宽 + R + gap` 是个**固定值** ⇒ 在 f 已不小的盒子里
                    #   几乎必然越界或被 `cover` 守卫拒 ⇒ 实测 `stack=0`（通道静默失效）。
                    #   现在：16 个方向 × 3 档偏移（`off`、`off+2(R+gap)`、`off+4(R+gap)`）。
                    done = False
                    for _try in range(16):
                        if done:
                            break
                        _dbg['att'] += 1
                        v = rng.normal(size=3)
                        v = v - (v @ nrm) * nrm
                        if np.linalg.norm(v) < 1e-6:
                            continue
                        v = v / np.linalg.norm(v)
                        pv = pos @ v
                        base = 0.5 * float(pv.max() - pv.min()) + R + c['gap'] * self.dx
                        # ★★ Round 67 修（针对 Round 65 实测的 **90% 越界**）：
                        #   原来只试 `s ∈ {base, base+2(R+gap), base+4(R+gap)}`，**只会越走越远**
                        #   ⇒ 在大核 + 小盒下 `base` 本身就常出界（实测 425/471 次越界、成功率 1%）。
                        #   真正的物理约束是"**不重叠**"，而它由下面的 `cover` 守卫精确执行
                        #   ⇒ 允许**更近**的落位（最小间距 `R+gap`）既合法又大幅提高成功率。
                        #   现在按 `s` 从大到小扫描：`base` → `R+gap`，取第一个过界内+`cover` 的。
                        _s_hi = base
                        _s_lo = R + c['gap'] * self.dx
                        for j in range(4):
                            s_ = _s_hi - j * (_s_hi - _s_lo) / 3.0
                            cc = c0 + s_ * v
                            if np.any(cc < R + 0.3e-6) or np.any(cc > self.L - R - 0.3e-6):
                                _dbg['oob'] += 1
                                continue
                            rel = self.XYZ - cc
                            dd = rel @ nrm
                            rp = np.linalg.norm(rel - dd[..., None] * nrm, axis=-1)
                            cover = (np.abs(dd) <= t / 2) & (rp <= R)
                            # ★★ Round 83 修（`WINDOWB_AUDIT_REGISTER.md` A3，实测）：
                            #   **空掩模上 `(x==0).all()` 返回 True**（numpy 语义）⇒
                            #   `t/2 < ~dx/2`（薄核）时 `cover` 为空 ⇒ 守卫被"真空真"绕过，
                            #   `seed_plate` 仍改写数万胞的 phi（实测 26006 胞、最大 Δ=1.09 µm）
                            #   而 `region()` 完全不变 ⇒ **核根本不存在**，代码却记 `ok+=1`。
                            if not bool(cover.any()):
                                _dbg.setdefault('empty', 0)
                                _dbg['empty'] += 1
                                continue
                            if not bool((reg[cover] == 0).all()):
                                _dbg['cov'] += 1
                                continue
                            try:
                                self.seed_plate(k, cc, nrm, R, t,
                                                elong=c.get('elong', 1.0),
                                                along=c.get('along'),
                                                flat_end=True)
                                out.append((k, 'stack'))
                                _dbg['ok'] += 1
                                done = True
                            except ValueError:
                                _dbg['exc'] += 1
                            if done:
                                break
        self._nuc_events += out
        # ★★★ W1-3（2026-09-28，`C4`）：**本轮确有事件** ⇒ 置标志，由 `_finish_advance` 消费，
        #   强制做一次 reinit（跳过容差对它不生效）。
        #   依据：`seed_plate` 在盘内**覆写** `φ_j`（`max(φ_j, −sdf)`）、盘外保留旧值
        #   ⇒ 盘边界出现 O(|旧 φ_j|) 的跳变（可达 −1 µm 量级），而 `region()` 靠 argmin 仍然正确
        #   ⇒ **不报错、但 φ 已不是距离函数**。定时 reinit 是唯一的兜底，而它可能被跳过。
        #   ⚠ 只在 `out` 非空（真有事件）时置位 ⇒ 不形核的算例**逐位不变**。
        # ★★★ R22：可用 `nuc_cfg(force_reinit_after_event=False)` **关掉**这一强制。
        #   动机（R21 的结论与 R19 的观察）：**驱动层 `_seed_next` 只调
        #   `seed_plate()`，不置这个标志** ⇒ 两条路径在"事件后是否强制 reinit"
        #   上**不同**。而 R19 实测「`1-3` 在**两次形核之间**自己从 1.545 涨到 2.246」
        #   ⇒ 界面的变化发生在**事件之后**，正是这条强制 reinit 会起作用的地方
        #   （Sussman reinit 会**移动零水平集**）。
        #   ⇒ `False` 时与驱动层一致（默认 `True` = 归档行为，逐位不变）。
        if out and c.get('force_reinit_after_event', True):
            self._need_reinit = True
        if out:
            _dbg['n_events'] = _dbg.get('n_events', 0) + len(out)
            _dbg['forced_reinit'] = (_dbg.get('forced_reinit', 0)
                                     + (1 if c.get('force_reinit_after_event', True)
                                        else 0))
        return out

    def _npref_of(self, k):
        """变体 `k` 的惯习面法向（由 `advance(npref=...)` 缓存的 `self.npref_tab`）。

        ★★ Round 85 修（`WINDOWB_AUDIT_REGISTER.md` A12）：原来表缺失/无该 `k` 时
        **静默返回 `[0,0,1]`** 且无告警 ⇒ 若走 `per_field=True` 路径（`advance` 在 2121
        提前 return，而 `self.npref_tab` 原本在 2187 才赋值 ⇒ **那条路径永远拿不到表**），
        **所有新核的惯习面会静默变成 z 轴**、形核取向全错而无任何提示。
        ⇒ 现在**硬失败**：拿不到就抛错，绝不静默给一个假法向。"""
        tab = getattr(self, 'npref_tab', None)
        if tab is None:
            raise RuntimeError(
                '_npref_of: `npref_tab` 未设置 —— `advance(npref=...)` 尚未被调用过，'
                '或走的是 `per_field=True` 路径（该路径现在也会在入口处缓存表）。')
        try:
            v = tab.get(k)
        except AttributeError:
            raise TypeError('_npref_of: `npref` 必须是 dict（得到 %s）' % type(tab).__name__)
        if v is None:
            raise KeyError('_npref_of: `npref` 表里没有变体 %r' % (k,))
        return np.asarray(v, float)

    def _sep_conv3(self, f, k):
        """周期边界下的**可分离** 1D 卷积（沿三个轴各做一次 `k`）。

        用途：`advance(norm_smooth=m)` 里对差分场的**梯度分量**做盒式平滑
        （`MEASUREMENT_SPEC R3` 记录的"对法向做平滑/粗 stencil"口径）。
        `np.pad(mode='wrap')` + `np.convolve(..., 'valid')` ⇒ 严格周期、无边界污染。
        已对 `scipy.ndimage.uniform_filter(mode='wrap')` 逐位校验（`_chk_sepconv.py`，
        3 档 m，最大差 ≤4.4e-16）+ 常值场正对照 + 负对照。"""
        out = np.asarray(f, float)
        n = len(k) // 2
        # ★★ Round 83 修（`WINDOWB_AUDIT_REGISTER.md` C1，实测）：`m >= N` 时
        #   `np.convolve(...,'valid')` 的长度规则 `max(M,N)-min(M,N)+1` 会**反过来**取核的
        #   valid 段，且 `n >= N` 时 `out[-n:]` 被裁剪成只有一份数组 ⇒ **pad 不是真 halo**
        #   ⇒ 输出形状错（实测 N=8: m=9→(6,6,6)、m=11→(2,2,2)），下游要么广播报错
        #   （**报错指向 advance，极难查**），要么在 `3N-2m==1` 的巧合下**静默广播**
        #   ⇒ 全部胞共用一个法向、`M(n)` 各向异性退化成标量。
        #   边界恰好是 `m == N`（实测 m=N 时仍逐位正确）⇒ 断言写 `m <= N`。
        if n > out.shape[0]:
            raise ValueError(
                '_sep_conv3: norm_smooth 半径 %d 超过数组边长 %d（会静默出错）'
                % (n, out.shape[0]))
        for ax in range(3):
            out = np.moveaxis(out, ax, 0)
            pad = np.concatenate([out[-n:], out, out[:n]], axis=0) if n > 0 else out
            out = np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 0, pad)
            out = np.moveaxis(out, 0, ax)
        return out

    def seed_sphere(self, k, center, R):
        c = np.asarray(center, float)
        r = np.linalg.norm(self.XYZ - c, axis=-1)
        self.phi[k] = np.minimum(self.phi[k], r - R)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], R - r)   # 其它区域让位

    def seed_plate(self, k, center, normal, R, t, elong=1.0, along=None, flat_end=False):
        """薄板晶核：法向 normal、半径 R、厚 t。

           P3 (2026-09-26): elong/along 支持**长条形**种子（面内椭圆）。
           为什么需要：Mfac 对变体-变体界面是**双重压制**（(n.ncmp)^2 与 (n.w)^2）
           => 块被**锁在种子形状**上 => 圆盘种子只能给出长/宽~1 的等轴块
           （实测 LR1 长/宽=1.39）。真实马氏体板条的**形核胚本身是薄片状**的
           （晶体学控制）=> 属 HyBRID_FRAMEWORK 8 item 4 的**形核是输入**。
           along = 长轴方向（= n x w）；elong = 长/宽比。
        """
        c = np.asarray(center, float)
        n = np.asarray(normal, float)
        n = n / np.linalg.norm(n)
        rel = self.XYZ - c
        d = rel @ n
        u = rel - d[..., None] * n
        rperp = np.linalg.norm(u, axis=-1)
        if elong > 1.0 and along is not None:
            al = np.asarray(along, float)
            al = al / (np.linalg.norm(al) + 1e-300)
            e_par = u @ al
            e_per = np.linalg.norm(u - e_par[..., None] * al, axis=-1)
            rperp = np.sqrt((e_par / elong) ** 2 + e_per ** 2)
        # EXPERT-#1 修：**越界硬检查**。 在 elong>1 时用 (e_par/elong)^2+e_per^2
        #   => 长轴半径 = elong*R。若它超过"种子中心到最近域面的距离"，种子会被
        #   盒子截断（实测 E6: elong*R=1.8um > L/2=0.8um => 初始长/宽只有 2.72 而非 6）。
        #   截断后的一切形貌结论都无效 => 这里直接拒绝，不再静默。
        if elong > 1.0:
            _c = np.asarray(center, float)
            _margin = float(min(_c.min(), (self.L - _c).min()))
            if elong * R > _margin:
                raise ValueError(
                    'elongated seed exceeds domain: elong*R=%.4g um > margin %.4g um. '
                    'Enlarge L, reduce R, or reduce elong.'
                    % (elong * R, _margin))
        if flat_end and elong > 1.0 and along is not None:
            # 判据：把**长轴两端做成平端面**（矩形棱柱），而不是椭圆圆角。
            #   动机（_dbg_3face.py）：椭圆种子的长轴端是圆角 => 界面法向**从不接近 a**
            #   => "沿 a 的生长"只能靠斜界面，而斜界面同时增大 W/T => 三方向同比长大。
            #   矩形棱柱的端面严格垂直 a => 它是唯一能"只增加 L"的面。
            al = np.asarray(along, float)
            al = al / (np.linalg.norm(al) + 1e-300)
            e_par = u @ al
            e_per = np.linalg.norm(u - e_par[..., None] * al, axis=-1)
            sdf = np.maximum(np.maximum(np.abs(d) - t / 2, np.abs(e_par) - elong * R),
                             e_per - R)
            self.phi[k] = np.minimum(self.phi[k], sdf)
            for j in range(self.nreg):
                if j != k:
                    self.phi[j] = np.maximum(self.phi[j], -sdf)
            return
        sdf = np.maximum(np.abs(d) - t / 2, rperp - R)         # 椭/圆盘 SDF（近似）
        self.phi[k] = np.minimum(self.phi[k], sdf)
        for j in range(self.nreg):
            if j != k:
                self.phi[j] = np.maximum(self.phi[j], -sdf)

    def init_parent(self):
        """★ 多区域 VDF 的标准初始化：母相 = 变体并集的补集 ⇒ φ_0 = −min_{k≥1} φ_k。
           （本轮修的 bug：把 φ_0 初始化成常数 1e3 ⇒ argmin 永远选变体 ⇒ 母相初始体积 0 ✗）"""
        self.phi[0] = -np.min(self.phi[1:], axis=0)

    # ================= 面上场 Γ（溶质过剩）：Gibbs 面的"面" =================
    def surface_band(self):
        """界面胞集合：6 邻域内区域号不同者（3D 中的离散 2D 流形）"""
        reg = self.region()
        m = np.zeros_like(reg, bool)
        for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            m |= (np.roll(reg, d, axis=(0, 1, 2)) != reg)
        return m

    def cell_area(self):
        """每胞的界面面积 A_c = (#异键)/2·dx²（立体学一致的测度）"""
        reg = self.region()
        b = np.zeros(reg.shape)
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            b += (np.roll(reg, d, axis=(0, 1, 2)) != reg)
        return 0.5 * b * self.dx ** 2

    def cell_area_geom(self):
        """★ P1 修正：几何（coarea / 部分体积）面积测度，替换格子键测度。
           A_c(i) = |∇φ_k(i)|·dx²/3（只取 winner==k 且在 1.5dx 带内）。
           ★ 记账：初版多乘了 2（误以为要"两侧各半"），实测给 +100.5% ✗；
             实际上每个胞只属一个区域 ⇒ Σ_k 已含两侧 ⇒ 去掉因子后 +0.25% ✅
             （与 A2 的 +0.3% 完全一致，两条独立估计互相印证 ✓）。"""
        reg = self.region()
        A = np.zeros_like(self.phi[0])
        for k in range(self.nreg):
            g = np.gradient(self.phi[k], self.dx, edge_order=2)
            # ★★ 记账（本轮修的真 bug，M3/A3 的 `nan` 就是它）：**不能给 gn 加 ε**。
            #   旧写法 `gn = |∇φ| + 1e-30` ⇒ 带外（|∇φ| = 0）的胞也得到 A_c = 1e-48 > 0
            #   ⇒ 掩模 `A_c > 0` **恒为真（全域）**、`A_c` 在带外是 1e-48 量级。
            #   在 H6 把面扩散改成"保守边通量 + `Δq/A_c`"之后，真实带（A_c≈6.7e-19）与
            #   "幽灵带"（1e-48）的交界处比值 ~1e29 ⇒ 显式更新**爆掉**（实测 M3：
            #   `|Γ|` 1e-6 → 2.9e5 → 3.6e21 → nan）。⇒ 用**原始** |∇φ|：带外 A_c 严格为 0，
            #   掩模 `A_c > 0` 就精确等于"该胞承载界面面积"（H6 想要的语义）。
            gn = np.sqrt(sum(gi ** 2 for gi in g))
            band = (reg == k) & (np.abs(self.phi[k]) <= 1.5 * self.dx)
            A = np.where(band, gn * self.dx ** 2 / 3.0, A)
        return A

    def area_total_geom(self):
        return float(self.cell_area_geom().sum())

    def band_health(self):
        """界面带健康度 —— **防止几何量静默失真**（本轮实测的坑）。

        多畴 + 宽带速度扩展时，各区域按"自己最近的界面"平移 ⇒ 两区域之间的差分
        `φ_k−φ_l` 被**无限拉陡**：实测带内 |∇φ| 从 0.5 涨到 530、带胞从 3.7e4 掉到 155
        ⇒ 面几何测度（S_v、面积）**静默退化到 0** ✗。
        任何用带几何做结论的地方（S_v、板条厚度、面偏析总量）必须先过这一关。
        返回 (带胞数, 带内 |∇φ_winner| 中位, 是否健康)。
        """
        A = self.cell_area_geom()
        m = A > 0
        if not m.any():
            return 0, np.inf, False
        karr = np.argsort(self.phi, axis=0)[0]
        phiw = np.take_along_axis(self.phi, karr[None], 0)[0]
        gn = np.sqrt(sum(gi ** 2 for gi in np.gradient(phiw, self.dx, edge_order=2)))
        med = float(np.median(gn[m]))
        ok = (med < 5.0) and (int(m.sum()) > 0.002 * self.phi.shape[1] ** 3)
        return int(m.sum()), med, bool(ok)

    # ★★ T3（2026-09-28）：`XYZ` / `Gam` / `Gam_mol` 惰性分配（见 __init__ 的记账）。
    #   对外接口完全不变（可读可写）⇒ 判据脚本与既有调用点不受影响。
    @property
    def XYZ(self):
        if getattr(self, '_XYZ', None) is None:
            x = (np.arange(self.N) + 0.5) * self.dx
            self._XYZ = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
        return self._XYZ

    @XYZ.setter
    def XYZ(self, v):
        self._XYZ = v

    @property
    def Gam(self):
        if getattr(self, '_Gam', None) is None:
            self._Gam = np.zeros((self.N, self.N, self.N))
        return self._Gam

    @Gam.setter
    def Gam(self, v):
        self._Gam = v

    @property
    def Gam_mol(self):
        if getattr(self, '_Gam_mol', None) is None:
            self._Gam_mol = np.zeros((self.N, self.N, self.N))
        return self._Gam_mol

    @Gam_mol.setter
    def Gam_mol(self, v):
        self._Gam_mol = v

    # ★★ T3（2026-09-28）：`J_edge` 惰性分配（3×(N,N,N) = 24 B/胞，只在面扩散用到）。
    #   对外接口不变（`g.J_edge[i]` 可读可写）⇒ `_chk_h6.py` 等判据脚本不受影响。
    @property
    def J_edge(self):
        if getattr(self, '_J_edge', None) is None:
            self._J_edge = [np.zeros((self.N,) * 3) for _ in range(3)]
        return self._J_edge

    @J_edge.setter
    def J_edge(self, v):
        self._J_edge = v

    def Gamma_eq(self, c):
        """Langmuir/McLean 平衡过剩（mol/m²），复用 pipeline/gibbs 的单一参数来源"""
        try:
            import sys as _s
            # (fix) 原来的硬编码绝对路径 => 换项目相对路径，别人克隆到别处也能跑
            _s.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gibbs'))
            from gibbs_physics import gamma_eq_langmuir, dH_seg_from_anchor
            H, _ = dH_seg_from_anchor()
            flat = np.ravel(c)
            out = np.array([gamma_eq_langmuir(float(x), self.T, H) for x in flat])
            return out.reshape(c.shape)
        except Exception:
            K = np.exp(2.0)
            x = K * c
            return 2.14e-5 * x / (1.0 + x)

    def update_Gamma(self, dt, tau_ex=1e-9, D_s=1e-20):
        """面的演化（全部守恒）：
             (1) 与体相按局部平衡交换（同一胞等量反号 ⇒ 精确守恒；含 ρ_mol 换算）
             (2) 沿面扩散：**切向 Laplace–Beltrami 算子**（② 本轮修：旧写法用 6 邻域格点键，
                 含法向邻居 ⇒ Γ 会跨界面扩散 = 物理错 ✗）
             (3) 离开界面带的胞，其面过剩**还给体相**（⑥ 本轮修：旧写法直接清零 ⇒ 溶质泄漏 ✗）

        ★★ T4（2026-09-28）：`self.surface_chem = False`（B1 默认）时**整段关闭**。
           物理：位移型无扩散 ⇒ 界面既不分配也不富集溶质；界面化学 Γ_i 属 Window C。
           判据：`max|c − c0| == 0`（逐位）。需要溶质通道时显式置 `g.surface_chem = True`。
        """
        if not getattr(self, 'surface_chem', True):
            return 0.0                      # Γ ≡ 0，体相 c 不动（T4）
        if not hasattr(self, 'Gam'):
            self.Gam = np.zeros_like(self.phi[0])
        A_c = self.cell_area_geom()      # ★ P1：用几何（coarea）测度，替换格子键测度
        # ★★ H6 记账（本轮）：**面积、交换、扩散必须用同一个掩模**
        #   旧写法：`surface_band()`（异邻 2 层带）与 `cell_area_geom`（winner & |φ|≤1.5dx）不一致
        #   ⇒ 外层带胞 A_c=0 ⇒ 面扩散/交换在那里失效、且总量记账错位 ✗（审计 §5.2 的老账）。
        m = A_c > 0
        # ---- W-6c：Gam_mol 的兼容 guard（外部若写 Gam，以 Gam 为准重新同步）----
        # ★★ W-6c 的 guard（第二轮修，关键）：**不能用  去判"外部写歪"** ——
        #   界面一移动 A_c 就变，于是即使没人动 Gam， 也不再等于 Gam_mol
        #   ⇒ guard 会把 Gam_mol 重算成  ⇒ **凭空改摩尔量**（实测 rel 1.1e-5/步，
        #   30 步累积 1.2e-4，与 W-6b 的残差完全同源）。
        #   正确判据：比较"当前 Gam"与"**上一次由 Gam_mol 派生出来的 Gam**"（）——
        #   只有**外部真的写了 Gam** 时两者才会不同（面积变化不影响它）✓。
        if not hasattr(self, 'Gam_mol') or self.Gam_mol.shape != A_c.shape:
            self.Gam_mol = self.Gam * A_c
        elif hasattr(self, '_Gam_derived') and self._Gam_derived.shape == self.Gam.shape:
            _sc = max(float(np.max(np.abs(self.Gam))), 1e-300)
            if float(np.max(np.abs(self.Gam - self._Gam_derived))) > 1e-12 * _sc:
                self.Gam_mol = self.Gam * A_c          # 外部写了 Gam => 以它为准
        else:
            self.Gam_mol = self.Gam * A_c
        # (3) ★ W-6d：把"带外但仍持有 Gam_mol"的胞**每步强制回吐**给体相。
        #   旧写法依赖 （"上一步在带内、这一步不在"）⇒ 与调用顺序/reinit 耦合，
        #   漏掉的胞会让 Gam_mol 挂在带外 ⇒ 账面多出量（M4 综合场景 2.02e-04 -> 2.43e-03 的来源）。
        #   新写法只用**当前**的 ：凡是带外且 Gam_mol != 0 的，一律回吐并清零 ⇒ 与顺序无关。
        wander = (self.Gam_mol != 0.0) & (~m)
        if wander.any():
            self.c = self.c + np.where(wander,
                                       self.Gam_mol / (self.rho * self.dx ** 3), 0.0)
            self.Gam_mol = np.where(wander, 0.0, self.Gam_mol)
        self._m_prev, self._A_prev = m.copy(), A_c.copy()
        Gam_eq = self.Gamma_eq(self.c)
        # ★ 稳定性保护：显式弛豫必须 dt ≤ τ_ex，否则 Γ 过冲发散（实测 M4 里 dt=4e-9 > τ=1e-9
        #   导致总量变负、涨 1e5 倍 ✗）。超出时按线性插值限幅（等价于隐式的第一步）。
        frac = min(1.0, dt / tau_ex)
        # (1) 局部平衡交换：**按摩尔**做（目标摩尔 = Gamma_eq * A_c）⇒ 体/面等量反号，精确守恒
        dmol = np.where(m, (Gam_eq * A_c - self.Gam_mol) * frac, 0.0)
        self.Gam_mol = np.where(m, self.Gam_mol + dmol, 0.0)
        self.c -= dmol / (self.rho * self.dx ** 3)
        # (2) 面扩散 —— ★★ H6：改成**保守边通量形式**（旧写法是 Laplace–Beltrami *微分算子*）
        #   为什么必须改：微分算子离散（中心差分）**没有通量结构** ⇒ Σ(A_c ΔΓ) ≠ 0，
        #   即"面扩散会凭空造/吞溶质"，而 `ΣJ_s = 0`（三叉线通量平衡）正是本课题要学的东西。
        #   通量形式：把面看成"带上的一个 2D 流形"，边 (i,j) 的通量为
        #       F_ij = −D_s·A_e·(Γ_j−Γ_i)/ℓ_ij,  A_e = ½(A_c(i)+A_c(j)),
        #       ℓ_ij = dx·|sin θ_ij| = |(x_j−x_i) − n̂(n̂·(x_j−x_i))|   ← 投影到切平面
        #   于是：① 纯法向相连（ℓ→0）的通量为 0 ⇒ 不跨界面扩散 ✓（审计 A3 的切向性）；
        #        ② 每条边只在 i、j 各记一次且符号相反 ⇒ **逐位守恒** ✓；
        #        ③ 三叉线处各支通量自然相加 ⇒ **ΣJ_s = 0 是结构性的** ✓。
        #   平界面极限：n=ẑ ⇒ x/y 边 ℓ=dx、z 边 ℓ=0 ⇒ 退化为切向 5 点 Laplacian ✓ 一致。
        if D_s > 0:
            order = np.argsort(self.phi, axis=0)
            karr = order[0]
            self.J_edge = []          # ★ 暴露每条边通量（供 ΣJ_s 判据/H7/算子使用）
            # winner 的法向（用 winner 的 φ 直接求梯度）
            # ★ 记账（本轮踩的坑）：**不能用 `self.phi[karr]`** —— 4 维数组上用 3 维整数
            #   索引，numpy 会把尾部维度**接在索引形状后面** ⇒ 得到 (N,N,N,N,N,N) 的 6 维
            #   数组（实测报 "allocate 512 GiB" ✗）。正确写法是 `take_along_axis`
            #   （与 `advance` 里既有写法一致）。
            phiw = np.take_along_axis(self.phi, karr[None], 0)[0]
            gk = np.gradient(phiw, self.dx, edge_order=2)
            nrm = np.stack(gk, -1)
            nn = np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-30
            nhat = nrm / nn
            eps = 1e-3 * self.dx
            for ax in range(3):
                Ac_j = np.roll(A_c, -1, axis=ax)
                Ae = 0.5 * (A_c + Ac_j)
                # ★★ 记账（本轮修的**真 bug**，A3/M3 的直接根因）：**绝不能对界面两侧的
                #   法向取平均**。界面两侧的 winner 不同 ⇒ 两者的 n̂ 恰好**反向**
                #   （+ẑ 与 −ẑ）⇒ 平均后**相消为 0** ⇒ 归一化退化 ⇒ `sinθ = 1` ⇒
                #   系统把**跨界面（法向）连接**误判成**切向**连接 ⇒ Γ 沿法向泄漏。
                #   实测：A3 的法向二阶矩 12dx → ~0（Γ 全跑到别的 z 层）、M3 的 Γ 被摊到
                #   3 层、只能到 Γ_McLean 的 **0.477 倍**（都指向同一个 bug）。
                #   修法：取**更靠内那一侧**（φ_winner 更负）的法向作为该连接的界面法向。
                #   单界面光滑处两侧法向几乎相同（等价）✓；界面处恰好给出正确的界面法向 ✓。
                #   （注意：sinθ 只用 `n_pair·ê` 的**平方** ⇒ 符号无关 ⇒ "取哪一侧"只影响
                #     "不被相消"，不引入新的方向约定。）
                phj = np.roll(phiw, -1, axis=ax)
                take_i = phiw <= phj
                npair = np.where(take_i[..., None], nhat,
                                 np.roll(nhat, -1, axis=ax))
                sin_t = np.sqrt(np.maximum(1.0 - npair[..., ax] ** 2, 0.0))
                mj = np.roll(m, -1, axis=ax)
                conn = m & mj
                # ★ 记账（本轮由 F1 的**有效 D_s** 检验抓到的**量纲错误**）：
                #   导通必须写成 `D_s·A_e·sinθ/dx²`，而不是 `D_s·A_e/ℓ`。
                #   理由：面上的有限体积式是 `A_c ∂_tΓ = Σ_j (D_s·L_ij/ℓ_ij)(Γ_j−Γ_i)`，
                #   其中 L_ij 是**边长**（不是面积！）。把 A_c≈dx² 的**面积**当 L 用，
                #   会白白多出一个 dx ⇒ 有效 D 变成 `D_s·dx`（量纲也从 m²/s 变 m³/s）。
                #   实测：修前 d(R²)/dt 口径的有效 D_s/D_s = **1e-8 = dx** ✗；
                #   正确写法 = D_s·A_e·sinθ/dx²（平界面 sinθ=1 ⇒ 退化切向 5 点 Laplacian ✓，
                #   纯法向 sinθ→0 ⇒ 通量→0 ✓）。
                # W-6c：通量里的 Γ 由派生量给出（Gamma = Gam_mol/A_c），**更新量本来就是摩尔**
                m_safe = np.where(m, A_c, 1.0)
                Gam_v = np.where(m, self.Gam_mol / m_safe, 0.0)
                J = np.where(conn, -D_s * Ae * sin_t
                             * (np.roll(Gam_v, -1, axis=ax) - Gam_v) / self.dx ** 2,
                             0.0)
                dq = dt * J
                self.J_edge.append(J)
                # Δ(摩尔)_i = dt·(J_{i−1→i} − J_{i→i+1}) ⇒ roll(+1) 把上一条边的 J 搬到 i
                self.Gam_mol = np.where(m, self.Gam_mol
                                        + (np.roll(dq, 1, axis=ax) - dq), self.Gam_mol)
        else:
            self.J_edge = [np.zeros_like(self.Gam)] * 3
        # 派生 Gamma（per-area）供物理/判据读取；Gam_mol 才是权威状态
        self.Gam = np.where(m, self.Gam_mol / np.where(m, A_c, 1.0), 0.0)
        self._Gam_derived = self.Gam.copy()      # ★ 供 guard 区分"外部写"vs"面积变"
        # (3') 带外的 Γ 清零（其摩尔量已在上面还给体相）
        self.Gam = np.where(m, self.Gam, 0.0)

    def _normal_of(self, k):
        g = np.gradient(self.phi[k], self.dx, edge_order=2)
        gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
        return [gi / gn for gi in g]

    def iface_offset(self, k=1, l=0, axis=2, near=None):
        """**亚胞射线交点**口径的界面位置：k 与 l 之间沿 `axis` 的交点均值。
           量界面**速度**用它：v = (z_if^(1) − z_if^(0))/(nstep·dt)（符号按 k 收缩为负）。
           ★ 记账：**不要**用 `region()` 计数法量速度 —— 亚胞平移下会失明/巧合精确
             （见模块级 `iface_crossings` 的记账与审计 §10）。
           `near` 给定时只取**离 near 最近的那一个交点**（每列一个，再取均值）
           —— 用于一列里有多个界面（如周期 slab 有 2 个）时锁定要跟踪的那一个。
           返回 (n_used, coord)；n=0 时 coord 为 nan。"""
        n, coord = iface_crossings(self.phi[k] - self.phi[l], self.dx, axis)
        if n == 0:
            return 0, float('nan')
        if near is not None:
            return 1, float(coord[np.argmin(np.abs(coord - near))])
        return n, float(coord.mean())

    def totals(self):
        """总溶质（mol）：体相 Σc·ρ·dV + 面 ΣΓ·A_c"""
        if not hasattr(self, 'Gam'):
            self.Gam = np.zeros_like(self.phi[0])
        mb = float(self.c.sum()) * self.rho * self.dx ** 3
        # ★★ W-6c：面量用**权威状态 Gam_mol（摩尔/胞）**求和 —— 与面积测度无关 ⇒ 必然闭合。
        if not hasattr(self, 'Gam_mol'):
            A_c = self.cell_area_geom()
            self.Gam_mol = self.Gam * A_c
        ms = float(self.Gam_mol.sum())
        return mb, ms

    def wrap_axes(self, k=None):
        """★★ T12（D12a，2026-09-28）：**周期盒绕盒检测**。

        为什么必须有：周期边界下，长过 `L/2` 的板条会**绕盒**，其"长度"读数会超过 `L`
        却**没有任何报错**。审计实测（`_audit_geom.py`）：**9/9 个单核算例的"长"都 > L**，
        占投影上限 `L·Σ|u_i|` 的 **70%–96%**（C1 95.8%、A1 91.9%、N1 89.2% …）
        —— 而那批正是 `EXPERT_REVIEW_RESPONSE.md §5` 当作"第一批干净板条数据"的算例。
        ⇒ 没有守卫时，绕盒会静默污染所有"板条长度/长径比"的结论。

        做法（**周期连通性**，不是"包围盒"）：
          ① 对区域掩模做 6-邻域连通标记（非周期）；
          ② 把跨盒面的周期邻居对**并查集合并**（只有两侧都在掩模内才合并）；
          ③ 若某个合并后的连通分量**同时**触及某个轴的**两个对立面** ⇒ 该轴**绕盒**。

        返回绕盒的轴列表（`k=None` 时用全部变体区域 `region()>0` 的并集）。
        """
        from scipy import ndimage
        reg = self.region()
        m = (reg > 0) if k is None else (reg == k)
        if not m.any():
            return []
        lab, n = ndimage.label(m)                      # 6-邻域（默认 structure）
        parent = list(range(n + 1))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
        for ax in range(3):
            a0 = np.take(m, 0, axis=ax)
            a1 = np.take(m, -1, axis=ax)
            l0 = np.take(lab, 0, axis=ax)
            l1 = np.take(lab, -1, axis=ax)
            both = a0 & a1
            if both.any():
                for x, y in zip(l0[both].ravel(), l1[both].ravel()):
                    union(int(x), int(y))
        out = []
        for ax in range(3):
            l0 = np.take(lab, 0, axis=ax)
            l1 = np.take(lab, -1, axis=ax)
            r0 = {find(int(v)) for v in l0[l0 > 0].ravel()}
            r1 = {find(int(v)) for v in l1[l1 > 0].ravel()}
            if r0 & r1:
                out.append(ax)
        return out

    def wrap_axes_any(self):
        """★★ T12-D12a 修正（2026-09-28）：**逐变体**查绕盒。

        为什么必须改语义：`wrap_axes(None)` 判的是"**所有变体区域的并集**是否周期贯通"。
        但**碰撞之后变体网络本来就会渗流贯通** —— 那正是 impingement 的定义！
        ⇒ 并集口径会把"**网络已连通**"误报成"**某条板条绕盒**"。

        实测（`T13_recheck_wrap.py`）：多核 RVE 在 `f = 0.05–0.17` 就被并集口径判为"绕盒"，
        而那时**没有任何单条板条**能跨过 `L`（种子面内半径只有 ~0.5 µm，`L/2 = 1.6 µm`）。

        正确判据：**只有某一个变体自身的区域贯通周期盒**，才说明那条板条绕了盒。
        返回 `{k: [轴...]}`（空 dict = 无变体绕盒）。
        """
        out = {}
        for k in range(1, self.nreg):
            ax = self.wrap_axes(k)
            if ax:
                out[k] = ax
        return out

    def check_wrap(self, k=None, strict=None, tag=''):
        """绕盒守卫的**入口**：`strict=True`（或 `self.wrap_strict`）时直接抛错。"""
        ax = self.wrap_axes(k)
        if ax and (strict if strict is not None
                   else getattr(self, 'wrap_strict', False)):
            raise RuntimeError(
                'T12/D12a 绕盒守卫：区域 %s 沿轴 %s **绕盒**（周期性贯通）'
                '⇒ 长度/长径比读数无效。请放大 L、缩短板条或缩小种子。%s'
                % ('全部变体' if k is None else k, ax, tag))
        return ax

    def region_extent(self, k=None):
        """区域在各轴上的**朴素包围盒长度**（未解绕）与"若绕盒则不可信"的标记。"""
        reg = self.region()
        m = (reg > 0) if k is None else (reg == k)
        idx = np.argwhere(m)
        if idx.size == 0:
            return None, []
        ext = (idx.max(0) - idx.min(0) + 1).astype(float) * self.dx
        return ext, self.wrap_axes(k)

    def curvature_of(self, k, grad=None, gn=None, field=None):
        """kappa = div(grad phi / |grad phi|)。

           AUDIT-#8 修：np.gradient 默认 edge_order=1（边界一阶）=> 对界面靠近边界、
           或只有数胞厚的薄片，kappa 在边界/薄向上误差大。改用 **edge_order=2**。
           记账：这不能解决"薄片只有 2-3 胞厚时二阶导本身不可信"的根本问题
           （那是分辨率问题，见 LATH_CODE_AUDIT #8/#2 与 C 节），只去掉边界那一项误差。

           ★★ T3（2026-09-28）：① 接受**预计算的梯度/模长**（调用方本来就要算，旧写法
             在这里又算一遍 ⇒ 每场 2 次 `np.gradient`）；② 只算**对角项** `∂_i n_i` ——
             旧写法 `np.gradient(n[i], dx)[i]` 会算出 3 个偏导、丢掉 2 个（3× 浪费）；
             ③ 对角项用**周期中心差分**（`np.roll`），对周期盒比 `np.gradient` 的单边
             边界**更正确**（旧写法在首末两层用单边差分 = 周期盒里没有的边界）。
             ⚠ 记账：②③ 让首末两层的 kappa 与旧值**不同**（内部逐位相同，若 grad 相同）。
             影响面：`T3_verify_fastpath.py` 的正对照给出对照量级。
           `field` 可传**子盒切片**（T3 的包围盒加速用）。"""
        arr = self.phi[k] if field is None else field
        g = np.gradient(arr, self.dx, edge_order=2) if grad is None else grad
        if gn is None:
            gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
        out = None
        for i in range(3):
            ni = g[i] / gn
            di = (np.roll(ni, -1, axis=i) - np.roll(ni, 1, axis=i)) / (2.0 * self.dx)
            out = di if out is None else out + di
        return out

    def facet_nref(self, k, larr, npref):
        """★★ T9（2026-09-28）：按**面片身份** `(I⁻, I⁺) = (k, l)` 给**每胞**一个参考取向。

        物理：Gibbs 面的本构量（γ(n)、M(n)）是**面自己的性质**，由界面两侧的相决定：

          * `(k, 0)`（变体 k / 母相）⇒ 变体 k 与母相的**惯习面**法向 `npref[k]`
          * `(k, l)`（两变体）      ⇒ 两变体的 **rank-1 相容（不变）平面** `ncmp[k,l]`

        ★ 修的是什么：在 T9 之前，**迁移率** `M(n)` 已经按配对查表（`nd_ref`），
          但**界面刚度** `γ(n)` 只用了 **winner 自己的 `npref[k]`**
          ⇒ 变体-变体界面上 γ 的择优方向用错对象（那是 k 与**母相**的惯习面，
          不是 k 与 l 的不变平面）。两者在 f→1（界面几乎全是变体-变体）时差别最大。

        返回 `(…,3)`；`ncmp` 缺失/非有限时该胞退回 `npref[k]`；`npref[k]` 也没有时返回 None。
        """
        ncl = getattr(self, 'ncmp', None)
        if ncl is None or npref is None or npref.get(k) is None:
            return None
        nk = np.asarray(npref[k], float)
        nk = nk / (np.linalg.norm(nk) + 1e-300)
        out = np.broadcast_to(nk, np.shape(larr) + (3,)).copy()
        has_pair = np.asarray(larr) > 0
        if has_pair.any():
            li = np.clip(np.asarray(larr), 0, self.nreg - 1)
            cand = ncl[np.clip(int(k), 0, self.nreg - 1), li]
            good = has_pair & np.isfinite(cand).all(-1)
            if good.any():
                out = np.where(good[..., None], cand, out)
        return out

    def facet_gamma_sub(self, k, lsub, gamma0):
        """★★★ R-block（2026-09-29）：按**面片身份** @@(k,l)@@ 逐胞给基础面能
        @@\\gamma_\\Sigma@@（`BLOCK_DERIVATION.md` §2.3/§3.1）。

        * `self.lath is None`（**默认**）⇒ 直接返回**标量** `gamma0`
          ⇒ 与改动前**逐位相同**。
        * 挂了 `windowB_lath.LathTable` ⇒ **F3（同变体低角晶界）** 的胞返回
          @@\\gamma_{\\rm RS}(\\theta_{kl})@@，其余胞仍填 `gamma0`。

        ★ 为什么可以**把数组当 `gamma0` 传**：`_stiff_of` 的三条分支
          （`herring_stiffness_cusp` / `herring_stiffness` / 无分支）
          **对 `gamma0` 全部严格线性**（`:293-328`；`_bk_verify.py` S-4 逐位核过）
          ⇒ 传数组不改变任何几何/迎风/Herring 代码。
        ★ 纯函数（只读 `self.lath.gtab`）⇒ 在 `ParCtx.for_each` 的线程里安全。
        """
        lt = getattr(self, 'lath', None)
        if lt is None:
            return gamma0
        return lt.facet_gamma_sub(k, lsub, gamma0)

    def gel_facet(self, k, l, N=32, dx=2.5e-8):
        """★★ T10：面片身份 `(k,l)` 的**相干界面弹性能** `γ_el` [J/m²]（带缓存）。

        法向取该面片的**本征法向**：`(k,l)` 都在变体里 ⇒ `ncmp[k,l]`；
        否则退回 `npref[k]`（变体-母相的惯习面）。与 `facet_nref` **同一套身份约定**
        ⇒ γ 的"结构部分"与"弹性部分"作用在同一张面上 ✓。
        缓存键 `(k, l)`；`lambda_el=0`（`advance` 默认）时本表**从不被调用** ⇒ 逐位兼容。
        """
        key = (int(k), int(l))
        if not hasattr(self, '_gel_cache'):
            self._gel_cache = {}
        if key in self._gel_cache:
            return self._gel_cache[key]
        n = None
        try:
            n = self.facet_nref(int(k), np.array(int(l)), self.npref)
        except Exception:
            n = None
        if n is None:
            val = 0.0
        else:
            nv_ = np.asarray(n, float).reshape(-1, 3)[0]
            val = interface_elastic_energy(self._C4gel(), self._eps0_4gel(),
                                           int(k), int(l), nv_, N=N, dx=dx)[0]
        self._gel_cache[key] = float(val)
        return float(val)

    def _eps0_4gel(self):
        return getattr(self, '_eps0_ref', None)

    def _C4gel(self):
        return getattr(self, '_C_ref', None)

    def gel_facet_sub(self, k, larr):
        """按 `(k, larr)` 逐胞给 `γ_el`（`larr==0` ⇒ 变体-母相面片）。"""
        out = np.zeros(np.shape(larr))
        for l in np.unique(np.asarray(larr)):
            m = (np.asarray(larr) == l)
            out[m] = self.gel_facet(k, int(l))
        return out

    def _stiff_of(self, k, g, gn, npref, aniso, gamma0, herring, facet_lam, facet_eps,
                  nref_cell=None):
        """单个场的界面**刚度** gamma + gamma_tt（T3：从 `advance` 里抽出来，
           好让"只对活跃场、只在包围盒内"这条路径复用同一份逻辑，避免两处分叉）。

        ★★ T9：`nref_cell` 给定时按**面片身份**逐胞取参考取向（见 `facet_nref`）；
          不给则退回 T9 之前的行为（一律用 winner 的 `npref[k]`）⇒ 可做对照。"""
        gk = self.gamma if gamma0 is None else gamma0
        if facet_lam > 0.0 and npref is not None and npref.get(k) is not None:
            # ★ P3：尖点界面能（只在给了 npref 的场上用）
            n = np.stack([gi / gn for gi in g], -1)
            nd = np.asarray(npref[k], float)
            nd = nd / (np.linalg.norm(nd) + 1e-300)
            c2f = np.clip((n @ nd) ** 2, 0.0, 1.0)
            gk = herring_stiffness_cusp(c2f, gk, facet_lam, facet_eps)
        # ★ 记账（2026-09-26 的 bug）：这里必须是 **elif**。
        #   第一版写成独立的 if => 当 aniso>0 时，下面 sin^2 分支会把 facet 的 gk
        #   **整个覆盖** => facet_lam=0/0.4/1.0 三档结果**逐位相同**（实测抓到）。
        elif aniso > 0 and nref_cell is not None:
            # ★★ T9：按**面片身份**逐胞查表
            n = np.stack([gi / gn for gi in g], -1)
            nd = nref_cell / (np.linalg.norm(nref_cell, axis=-1, keepdims=True) + 1e-300)
            c2 = np.clip(np.einsum('...i,...i->...', n, nd) ** 2, 0.0, 1.0)
            gk = herring_stiffness(c2, gk, aniso, herring)
        elif aniso > 0 and npref is not None and npref.get(k) is not None:
            n = np.stack([gi / gn for gi in g], -1)
            # ★ 各向异性刚度：**统一走 `herring_stiffness`**（原来这里内联的写法与
            #   `LevelSetSurface` 各写一份 ⇒ 已合并，避免两处分叉）
            nd = np.asarray(npref[k], float)
            nd = nd / (np.linalg.norm(nd) + 1e-300)
            c2 = np.clip((n @ nd) ** 2, 0.0, 1.0)
            gk = herring_stiffness(c2, gk, aniso, herring)
        return gk

    # ================= ④ 数值格式：Godunov 迎风 |∇φ| 与 Sussman 重初始化 =================
    def _upwind_grad(self, phi, sgn):
        """★ 委托给**模块级** `upwind_grad`（单畴/多畴共用一份 ⇒ 不会分叉）"""
        return upwind_grad(phi, sgn, self.dx)

    def sussman_reinit(self, phi, iters=None, bbox=None):
        """委托给模块级 `sussman_reinit`。
           EXPERT-#3: 默认改用 self.reinit_iters 并透传 dtau/grad
           （原来这里硬编码 iters=30，且丢掉了 dtau/grad）。
           ★ W1-2: 再透传 `band_cells=self.reinit_band_cells`（默认 None ⇒ 全域 ⇒ 逐位兼容）。
           ★★ R1（2026-09-29）：透传 `par`（并行核）与 `bbox`（子盒）。
             **两者都不改变数值**（论证见模块级 `_band_bbox` / `sussman_reinit`），
             而且**两条路径共用同一段迭代代码** ⇒ 线程数不是物理参数。"""
        return sussman_reinit(phi, self.dx,
                              iters=(self.reinit_iters if iters is None else iters),
                              dtau=getattr(self, 'reinit_dtau', None),
                              grad=getattr(self, 'reinit_grad', 'upwind2'),
                              band_cells=getattr(self, 'reinit_band_cells', None),
                              bbox=bbox, par=getattr(self, 'par', None))

    def _advance_phi(self, k, vn, dt):
        """④ 用迎风 |∇φ| 推进：φ_t + v_n|∇φ| = 0"""
        sgn = np.where(vn > 0, 1.0, -1.0)
        return self.phi[k] - dt * vn * self._upwind_grad(self.phi[k], sgn)

    def volume(self, k):
        m = (self.region() == k)
        return float(m.sum()) * self.dx ** 3

    def area(self, k):
        reg = self.region()
        c = 0
        for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            nb = np.roll(reg, d, axis=(0, 1, 2))
            c += int(np.count_nonzero((reg == k) & (nb != k)))
        return c * self.dx ** 2

    # ---------- 体相驱动：谱法微弹性 ----------
    def elastic_driving(self, soft=None):
        """返回 (nreg, N,N,N)：**+ε⁰_k:σ**（对母相为 0）。

           ★★ T1 修（P0-1，2026-09-28）：本函数的**符号**由 `−ε⁰:σ` 改为 `+ε⁰:σ`。
             依据（变分法）：F_el = ½∫(ε−ε⁰):C:(ε−ε⁰)，机械平衡下 δF_el/δφ_v = −ε⁰_v:σ；
             演化 ∂φ/∂t = −L δF/δφ ⇒ **驱动力 = +ε⁰_v:σ**。
             独立数值判决（`T1_verify_edsign.py` / `_audit_edsign2.py`，单变体球 R=120 nm，
             N=48/dx=20 nm）：真实 D_corr = −(dE/dV) = **−1.43e8 J/m³**
             （coarea 面积；用精确 4πR² 得 −1.49e8），修前返回 **+1.66e8**
             ⇒ **符号相反**（比值 −1.17）；修后比值 **+1.12 ~ +1.17 ∈ [0.8,1.3]** ✓
             ⇒ 这是**纯符号错误、量级本来正确**。
             ⚠ 记账：本改动**改变了全部用过 `elastic_driving` 的归档结果的数值**，
             与修前的产物**不可比较**（影响面清单见 `WINDOWB_P0_REGISTER.md` §P0-1）。

           AUDIT-#9 修：原来一律用 **hard region** 指示场（@B@pf.phi[v] = (reg==v+1)@B@）
           => 界面胞的 eps0 分布是阶梯状 => FFT 谱法解出的 sigma 在界面处有 O(1) 阶梯噪声
           => 驱动 ed 在界面附近被污染。新增 soft 选项：用**平滑指示场**
               h_k = 0.5*(1 - tanh(phi_k / w)),  w = 1.5*dx
           默认 soft=None => 沿用类属性 self.elastic_soft（**默认 False**，
           以免改变已归档的全部结论）；显式 soft=True 才启用。"""
        if soft is None:
            soft = bool(getattr(self, 'elastic_soft', False))
        _hard = (lambda v: (self.region() == v + 1))
        reg = self.region()
        out = np.zeros((self.nreg,) + reg.shape)
        if self.aniso_elastic:
            # ★ 逐变体模量路径（`windowB_aniso_elastic.AnisoElastic`，已过 AS-1/AS-1b/AS-2）：
            #   把 `region` 的 0/1 指示场当作相场（与 PF3D 路径一致），解 inhomogeneous
            #   弹性取 σ。σ 的 6 分量约定与 `PF3D.sigma_tensor()` **逐位一致**
            #   （AS-1/AS-1b 实测 0.00e+00 / 9.5e-16）⇒ 下面 `e0v_eng` 的内积可直接复用。
            phi = np.zeros((self.nreg,) + reg.shape)
            for k in range(self.nreg):
                phi[k] = (reg == k)
            e0l = [np.zeros((3, 3))] + [np.asarray(e, float)
                                        for e in self.pf.eps0]
            #   ★ 记账：`AnisoElastic` 内部**全张量**（(3,3,N,N,N)，见该模块的记账）⇒
            #     用 `sigma6` 转成本仓库 6 分量约定（与 `PF3D.sigma_tensor()` 逐位一致，
            #     AS-1/AS-1b 三种 ε⁰ 实测 ≤9.5e-16）。
            #   ★ 性能：**热启动**（上一步的 ε 当初值）+ tol=1e-8 ⇒ 迭代数从 ~35 降到个位数。
            #     驱动力只需要 ~1e-4 的 σ 精度；AS-1/AS-1b 的严格一致性判据走 tol=1e-10。
            sig6, _nit, _ = self.ae.sigma6(
                phi, e0l, niter=80, tol=1e-8,
                init=getattr(self, '_ae_eps', None))
            self._ae_eps = self.ae.eps
            for v in range(self.nv):
                # ★★ T1 修（P0-1，2026-09-28）：符号 `−` → `+`（见 `elastic_driving` 的记账）。
                out[v + 1] = (+np.einsum('p,p...->...', self.e0v_eng[v], sig6)
                              + self.sext_e0[v])
            self._ae_nit = _nit
            return out
        if self.pf is None:
            return out
        if soft:
            if self.pf.phi.dtype == np.bool_:
                # ★ T3：布尔指示场装不下"软"剖面 ⇒ 按需一次性转成浮点（默认不走这条路）
                self.pf.phi = self.pf.phi.astype(np.float64)
            # AUDIT-#9: 平滑指示场（level-set 的 phi 是 SDF => 0.5*(1-tanh) 是自然选择）
            # ★ R1（2026-09-29）：12 个场互不相交 ⇒ 按场并行（`tanh` 是超越函数，
            #   单线程时是 `elastic_driving` 里的一项实打实的开销）。
            _w = 1.5 * self.dx
            self.par.for_each([
                (lambda v=v: self.pf.phi.__setitem__(
                    v, 0.5 * (1.0 - np.tanh(self.phi[v + 1] / _w))))
                for v in range(self.nv)], tag='ed.soft_phi')
        else:
            for v in range(self.nv):
                self.pf.phi[v] = (reg == v + 1)
        # ★★ T3：走 gather 路径（`region` 已经算过 ⇒ 不必再建 nv 个指示场）
        #
        # ★★★ 2026-09-28（Round 137）**修 `F-2`：`elastic_soft` 原本是一个"死开关"**。
        #   症状（`_chk_edsoft.py` 实测）：`elastic_driving(soft=True)` 与 `(soft=False)`
        #     `np.array_equal` = **True**，`max|Δ| = 0.000e+00` ⇒ 改它**完全不动任何东西**。
        #   根因：上面 `if soft:` 分支刚把**软剖面**写进 `self.pf.phi`，
        #     但这一行原来一律传**硬 `reg`**：
        #       `sigma_tensor(reg)` → `_epsh(reg)` → `eps0_fields_idx(reg)`
        #       而 `eps0_fields_idx`（`windowB_pf3d.py:255`）用 `idx > 0` 直接 gather，
        #       **根本不读 `self.phi`** ⇒ T3 的快路径把软剖面整个丢掉了。
        #     ⇒ AUDIT-#9 声称的"用平滑指示场消除界面 σ 的 O(1) 阶梯噪声"**从未生效**
        #       （`AGENTS.md §3.7`：编译通过、不报错，完全不代表改动生效了）。
        #   修法（**最小改动、且默认路径逐位不变**）：
        #     `soft=False` ⇒ 仍旧传 `reg` ⇒ 与修前**逐位相同**（归档读数不受影响）；
        #     `soft=True`  ⇒ 传 `None` ⇒ 走 `eps0_fields()`（`windowB_pf3d.py:235-240`），
        #                    它按 `Σ_v e0v[v,p]·self.phi[v]` 装配 ⇒ **真正吃到软剖面**。
        #   ⇒ 本条遵守 `WINDOWB_ROADMAP_TO_CORRECT.md §8.6` 定下的"两步走"纪律：
        #     **先落地"默认逐位不变"的能力，把"启用"留成单独一次显式改动**。
        #   ⚠ 代价记账：`soft=True` 时 `eps0_fields` 是 `6×nv = 72` 次整场乘加
        #     （T3 的记账说这是弹性耗时的大头）⇒ **`soft=True` 会明显变慢**，属预期。
        sig = self.pf.sigma_tensor(None if soft else reg)
        # ★ R1（2026-09-29）：12 个场只写 `out[v+1]`（互不相交）⇒ 按场并行。
        self.par.for_each([
            (lambda v=v: out.__setitem__(
                v + 1, (+np.einsum('p,p...->...', self.e0v_eng[v], sig)
                        + self.sext_e0[v])))
            for v in range(self.nv)], tag='ed.einsum')
        return out

    # ================= ★★ T6：温度的钟（T → 驱动力） =================
    def set_T(self, T, t=None):
        """把温度设到 `T`：`df[1:] = dG_of_T(T)`（**只对变体给驱动，母相恒 0**）。

        ★ T6：这是**唯一**把温度变成驱动力的入口。
        ★ 约定（T5 统一）：`df > 0 = 变体有利` ⇒ `T < T0` 时 `df > 0`、`T > T0` 时 `df < 0`。
        ★ `dG_of_T=None` 时**只记历史、不动 `df`** ⇒ 与 T6 之前的行为**逐位相同**。
        """
        self.T = float(T)
        if t is not None:
            self.t = float(t)
        if self.dG_of_T is not None:
            self.df[1:] = float(self.dG_of_T(self.T))
        self.Thist['t'].append(float(self.t))
        self.Thist['T'].append(self.T)
        self.Thist['df'].append(float(self.df[1]))
        return float(self.df[1])

    def T_now(self, t=None):
        """按时间表取温度（`T_of_t=None` 时返回当前 `self.T`）。[T]"""
        if self.T_of_t is None:
            return self.T
        return float(self.T_of_t(self.t if t is None else t))

    def advance_T(self, dt, **kw):
        """按 `T_of_t` 时间表推进一步：先 `t += dt`、`set_T(T_of_t(t))`，再 `advance(dt)`。

        ★ athermal 语义：马氏体**没有热激活** ⇒ 每个 T 上系统趋向该 T 的平衡分数，
          动力学只决定"多快到达"、不决定"到达哪"。所以**温度必须随步推进**，
          不能在循环外一次性设好（那会漏掉驱动力的时间演化）。
        """
        self.t = self.t + float(dt)
        if self.T_of_t is not None:
            self.set_T(self.T_of_t(self.t), t=self.t)
        return self.advance(dt, **kw)

    def elastic_driving_pair(self, karr, larr):
        """★ T3（2026-09-28）：**只算 winner / runner-up 两个场**的弹性驱动。

        下游（`advance` 的非 per_field 路径）只用 `ed[karr]` 与 `ed[larr]`，
        而旧写法先造一个 (nreg,N,N,N)（12 份多余）并做 **12 次 einsum**。
        这里改成"按 winner/runner-up 索引 gather 后加权求和"：
          ed_v = Σ_p e0v_eng[v,p]·σ_p + sext_e0[v]      （母相恒为 0）
        ⇒ 内存 (nreg,N³) → 2×(N³)，算术 12×(6乘5加) → 6×(gather+乘+加)。
        ⚠ 记账：求和次序与 einsum 不同 ⇒ 末位可能有 ~1e-16 相对差（不是逐位相同）；
          由 `T3_verify_fastpath.py` 判据把关。
        `aniso_elastic` / 无弹性 时退回通用实现（那些路径需要完整表）。"""
        if self.pf is None:
            z = np.zeros(self.phi.shape[1:])
            return z.copy(), z
        # ★★★ 2026-09-28（Round 137）**`F-2` 的第二处实例**（同一 bug 的另一条路径）。
        #   实测证据（`_w2_edhard2.log` vs `_w2_edsoft2.log`，引擎 `a1eb151f`）：
        #     两臂的**形状逐位相同**（`L=1458.6 W=1414.5 T=844.0`、`胞=233`、M-3/M-5 全同），
        #     而探针直接调 `elastic_driving()` 读到的 M-6 `ed` **却不同**
        #     （尖端 −2.517e8 → −1.957e8）⇒ **说明 `advance` 用的不是 M-6 读的那条路径**。
        #   走查确认：`advance` 走的是本函数（`:2374`），而下面 `sigma_tensor(reg)`
        #   **同样不读 `self.phi`** ⇒ 与 `elastic_driving` 里那处是同一个 bug。
        #   ⇒ `soft=True` 时改走通用实现（与 `aniso_elastic` 分支同款）。
        #   ⚠ 代价：`elastic_driving()` 会造 `(nreg,N³)` 并做 `nreg` 次 einsum
        #     —— 正是 T3 优化掉的东西 ⇒ **`soft=True` 会明显更慢**（预期，非 bug）；
        #     `soft=False`（**默认**）路径与修前**逐位相同**。
        soft = bool(getattr(self, 'elastic_soft', False))
        if self.aniso_elastic or soft:
            ed = self.elastic_driving()
            return (np.take_along_axis(ed, karr[None], 0)[0],
                    np.take_along_axis(ed, larr[None], 0)[0])
        reg = self.region()
        # ★★ T3：走 gather 路径（不再建 nv 个指示场、不再做 72 次整场乘加）
        sig = self.pf.sigma_tensor(reg)
        e0p = np.concatenate([np.zeros((1, 6)),
                              np.asarray(self.e0v_eng, float)], 0)     # 0 = 母相
        sep = np.concatenate([[0.0], np.asarray(self.sext_e0, float)])

        def _ed(idx):
            out = np.zeros(sig.shape[1:])
            for p in range(6):
                out += e0p[idx, p] * sig[p]
            return out + sep[idx]
        return _ed(np.clip(karr, 0, self.nv)), _ed(np.clip(larr, 0, self.nv))

    # ---------- 界面推进（PDE）----------
    # AUDIT-#1 (2026-09-26)： 的**默认值**由 'upwind' 改为 'central'。
    #   依据：审计发现两种格式在长时程上给出**不同结果**（同一 E6 配置：
    #   长/宽 1.54(upwind) vs 1.75(central)，f 0.727 vs 0.846；C1(central) 跑满 700 步、
    #   带胞健康、无失稳）=> 取更准确的 central 为默认。
    #   ⚠ 记账：**这改变了后续所有结果的数值**，与审计前的归档结果不可逐位比较。
    #   若某算例出现失稳（陡梯度），显式传 adv_grad='upwind' 可回退。
    def advance(self, dt, aniso=0.0, npref=None, gamma0=None, herring=True,
                adv_grad='proj2', extend='edt', band_cells=20, iface_band=2.0,
                drag=None, pair_kernel=False, per_field=False, pair_aniso=False,
                mob_aniso=0.0, pin_min=True, mob_beta=0.0, mob_beta_w=0.0,
                facet_lam=0.0, facet_eps=0.05, lambda_el=0.0, band_len=None,
                norm_smooth=0):
        # ★★★ D17（2026-09-28，用户批准）：**默认平流格式由 `'central'` 改为 `'proj2'`**。
        #   依据（`T19_verify_proj.py`，球 + 常数驱动、已知答案 `R(t)=R0+v·t`；
        #   判定点取**同一物理半径** `R=0.38L` 上插值）：
        #     | 格式    | R/R_ex−1 | 键数/干净阶梯键测度 | 判定 |
        #     | central | **+4.16%** | **2.237**（界面自发粗化，P1）| ✗ |
        #     | upwind  | −2.14%   | 1.016 | ✗（数值扩散致收缩）|
        #     | proj    | −2.22%   | 1.009 | ✗（同上，一阶）|
        #     | **proj2** | **−0.54%** | **0.998** | **★可用** |
        #   ⇒ 旧默认 `central` 用**非单调（色散）**格式离散 HJ 型 `v_n|∇φ|`，在网格尺度
        #     产生伪振荡 ⇒ 界面自发粗化（P1；T16 前置实测界面胞数 601→4232×7、
        #     `M6p` p25 3.5°→18.2°）。`proj2` 把 `v_n` **投影**成矢量 `V = v_n·n`
        #     再做**二阶 ENO(minmod) 迎风**对流 ⇒ 单调（不粗化）+ 对线性数据精确
        #     （无阶梯慢化）+ 两场共用同一个 `V`（差分场只平移）。
        #   ⚠ 记账：**D17 之前的所有归档读数都是在 `central` 下跑的**；要复现它们
        #     必须显式传 `adv_grad='central'`。`central` 路径**保留且未改动**。
        # ★★ T11：`band_len`（米）给定时**按物理长度**定延拓带宽：
        #   `band_cells = round(band_len/dx)`。为什么必须：`band_cells` 是**胞数**
        #   ⇒ 物理带宽 `band_cells·dx` 随 Δx 变 ⇒ 界面速度会**依赖分辨率**
        #   （实测 `v/(MΔf)` 在 Δx=40/50/62.5 nm 上分别为 0.923/0.843/0.818）。
        if band_len is not None:
            band_cells = max(1, int(round(float(band_len) / self.dx)))
        # ★★ T10：`lambda_el` = **相干界面弹性能 γ_el 的敏感度旋钮**（默认 0 = 不计入
        #   ⇒ 与 T10 之前**逐位相同**）。λ_el=1 时 `stk += γ_el(面片身份)`。
        # ★ 记账（本轮 P1 重标定）：`iface_band=2.0` 而非 1.0 —— 界面种子必须是
        #   **≥2 层胞**。实测 pair_kernel 下 `iface_band=1.0`（|∇d|≈2 ⇒ 种子只有
        #   1 层）时，`extend_along_normal` 的迎风延拓**退化**（v/MΔf = 0.125 ✗）；
        #   2.0/3.0 都给 1.0000 ✓（`_chk_p1.py` 全网格扫描，见审计 §10.1）。
        # ★ 记账（本轮）：`pair_kernel=True` 是"按配对核"的**实验性**实现（见审计 §10），
        #   尚未通过标定判据（平界面 |v|/MΔf 实测 0.00 ✗）⇒ **默认保持 False**，
        #   即停在已被 W2 验证的那条路径上（pair=False + EDT 扩展 + 20dx 带 ⇒ 1.0000 ✓）。
        """★ ⑤（本轮修）配对一致推进：界面 (winner k, runner-up l) 用**同一个** v_n，
           两侧 φ 一致更新（φ_k 减、φ_l 增）。旧写法让每个 φ_k 各用自己 v_k ⇒
           实测界面有效速度只有 **v/2** ✗（因为 VDF 里 |∇(φ_k−φ_l)|=2）。
           判据 W2 用"平界面 + 常数驱动"直接量界面速度验证。"""
        # ★★★ A3（2026-09-28）**自述平流格式**（防"改一半"的静默陷阱，AGENTS §3.24）。
        #   审计发现：全仓只有 **3 个诊断脚本**显式传 `adv_grad='central'`；
        #   而**全部生产/验证脚本**（T12/T13/T14/T15/T16/T20/T21/T24…）都是**不传**、
        #   吃默认值。D17 把默认从 `central` 改成 `proj2` 之后：
        #     ⇒ 重跑任何一个归档脚本都会给出**与报告里不同的数**，而脚本/输出里
        #       **没有任何标识**说明它换过格式 —— 这正是"改一半比不改更危险"。
        #   ⇒ 每个进程**首次**调用时打印一行自述（之后静默），使任何重跑都自我记账。
        if not getattr(self, '_adv_banner_done', False):
            _explicit = 'explicit' if adv_grad != 'proj2' else 'DEFAULT'
            print('[WindowB] 平流格式 adv_grad=%r（%s）；D17 之前默认是 central，'
                  '归档读数需显式传 central 才能复现。' % (adv_grad, _explicit),
                  flush=True)
            self._adv_banner_done = True
        reg0 = self.region()
        nreg = self.nreg
        # ★★ T3（2026-09-28）**去空算 + 降内存**（旧实现见 git 历史）：
        #   ① 旧写法为**全部 nreg 个场**算 `|∇φ|`、曲率、刚度并各存一份 (nreg,N,N,N)
        #      ⇒ 3×(13·N³) float64 = **276 MB**（N=96），而下游只用
        #      `take_along_axis(·, karr)` / `(·, larr)` —— 即每胞**只用 winner/runner-up**。
        #   ② 每个场还算了**两次** `np.gradient`（本循环 1 次 + `curvature_of` 内部 1 次），
        #      且 `curvature_of` 里 `np.gradient(n[i])[i]` 把 3 个偏导全算出来、丢掉 2 个。
        #   ③ 实测（`T3_mem_probe.py` + `_prof_step.py`，N=96）：`np.gradient` **87 次/步**
        #      占 24% 时间；单步临时峰值 **1072 B/胞**；常驻 592 B/胞。
        #   改法：只对**活跃场**（出现在 karr 或 larr 里）算，且只在
        #      **该场活跃胞的包围盒**（外扩 1 胞）内算，再散点写回按 winner/runner-up
        #      索引的 (N,N,N) 数组 ⇒ 常驻 276→14 MB，时间同降。
        #   ★ 为什么外扩 1 胞就够：`np.gradient` 在子盒**内部**用中心差分（与全盒逐位相同），
        #      只有子盒最外一层用单边差分；写回时只写**未外扩**的 `mk` ⇒ 用到的值全在内部 ✓。
        #      （`mk` 贴到网格边界时，子盒边界 = 网格边界 ⇒ 与旧写法的单边处理一致 ✓。）
        #   ⚠ `per_field=True` 需要**完整的** stiff 表，保留旧路径（非生产默认）。
        _shape = self.phi.shape[1:]
        # ★★ Round 85 修（`WINDOWB_AUDIT_REGISTER.md` A12）：把 `npref` 表的缓存**提到入口处**。
        #   原来它在 2187 才赋值，而 `per_field=True` 会在 2121 附近**提前 return** ⇒
        #   那条路径下 `self.npref_tab` 永远是 None ⇒ `_npref_of()` 静默返回 `[0,0,1]`
        #   ⇒ **所有新核的惯习面变成 z 轴**且无告警。配合新的硬失败 `_npref_of()`，
        #   这条路径现在会给出明确报错而不是错的取向。
        #   （默认路径 `per_field=False` 行为不变：同一对象、只是提前几行赋值。）
        self.npref_tab = npref
        # winner / runner-up
        # ★★ T3：`np.argsort(phi, axis=0)` 会造一个 (nreg,N³) **int64** 临时量
        #   （104 B/胞，N=96 时 92 MB）—— 而下游只要前两名。
        #   改法：`argmin` 拿 winner，再用 nreg 次"掩模内取更小"扫出 runner-up
        #   ⇒ 不产生 (nreg,N³) 临时量；数值与 argsort 前两名**逐位相同**（无并列时）。
        #   ★★ R1（2026-09-29）：整段交给 `windowB_par.ParCtx.argmin2` —— 在**空间**上
        #     切片并行，`np.argmin` 沿 axis=0 的次序与 runner-up 扫描的 j 次序**都没变**
        #     ⇒ 与上面这段**逐位相同**（`windowB_par._selftest` 已验证）。
        #     实测（N=192）：「winner+runner-up（13 场）」单线程 1.486 s → **×6.8 @16 线程**
        #     —— 它是本步里**加速比最高**的一块（说明它本来不是带宽受限，而是掩模
        #     布尔索引的延迟受限）。
        karr, larr = self.par.argmin2(self.phi)
        karr = karr.astype(np.intp)
        larr = larr.astype(np.intp)
        # ★★★ R-block（2026-09-29）：**F3 面能表 —— 主线程一次性向量化预计算**。
        #
        #   为什么必须这么写（两条，缺一不可）：
        #   ① **并行适配**：`_geom_k(k)` 是在 `self.par.for_each(...)` 的**工作线程**里
        #      跑的（见下面 `for_each` 那一行）。任何"在 worker 里做重分配"的写法
        #      都会 (a) 放大内存峰值、(b) 把 GIL/内存带宽变成瓶颈。
        #      ⇒ 正确分工：**主线程建表（只读）→ worker 只做零分配的 `[bb]` 切片**。
        #      `_gc_full` 建好后**不再被写** ⇒ 无竞争、无共享可变状态。
        #   ② **内存**：若在 `_geom_k` 里逐场调用 `facet_gamma_sub(k, larr[bb], gamma0)`，
        #      每个活跃场要分配 3–4 份子盒大小的临时数组
        #      （N=192 时 56 MB/份 ⇒ 7 个场 ≈ **1.2 GB/步**的瞬时分配）。
        #      实测这条把 WSL 推到 **swap 8188/8192 = 99.9%**、并让一个进程卡在 D 态。
        #      ⇒ 改成一次 N³ gather（≈226 MB，含临时），**降 5 倍以上**。
        #   ③ **数值**：`_gc_full[bb]` 与逐场调用的结果**逐位相同**
        #      （同一个 `gtab[k][clip(l)]`，同一个 `where(isfinite, ·, gamma0)`）。
        #      ⇒ 不改变任何归约次序 ⇒ **线程数仍不是物理参数**（判据 `_bk_par_identity.py`）。
        self._gc_full = None
        if getattr(self, 'lath', None) is not None:
            _g0 = self.gamma if gamma0 is None else float(gamma0)
            _G = self.lath.gtab[np.clip(karr, 0, self.nreg - 1),
                                np.clip(larr, 0, self.nreg - 1)]
            _isF3 = np.isfinite(_G)
            # ---- ★★★ R-block：**Gibbs 面上的薄膜序参量 ψ**（`BLOCK_DERIVATION` §4.6）----
            #   开关：`self.film`（默认 **None** ⇒ 整条通道关闭 ⇒ 逐位不变）。
            #   `self.film = dict(gamma_f=…, W=0.05, L=1e8, psi0=1.0)`。
            #   物理：γ_Σ(ψ) = (1−f)γ_dry + f·γ_f + W·g(ψ)；ψ 只在 **F3 胞**上演化
            #     （F1/F2 **不碰** ⇒ 变体/母相界面的面能不受影响 = 单变量）。
            #   数值：κ_ψ=0 ⇒ **纯局域 AC**，用 `flatnonzero` 限制在 F3 胞
            #     （~3000 胞）⇒ 零额外大分配；跑在**主线程**，与 `for_each` 的 worker
            #     不重叠 ⇒ 不引入竞态（判据见 `_bk_par_identity.py`）。
            _fm = getattr(self, 'film', None)
            if _fm is not None:
                from windowB_film import gamma_mix, psi_step_local
                if getattr(self, 'psi', None) is None:
                    self.psi = np.full(self.phi.shape[1:],
                                       float(_fm.get('psi0', 1.0)))
                _gd = np.where(_isF3, _G, _g0)
                self.psi, self._psi_diag = psi_step_local(
                    self.psi, _gd, dt, _isF3, float(_fm['gamma_f']),
                    W=float(_fm.get('W', 0.05)), L=float(_fm.get('L', 1.0e8)))
                _G = np.where(_isF3, gamma_mix(_G, self.psi,
                                               float(_fm['gamma_f']),
                                               float(_fm.get('W', 0.05))), _g0)
                self._gc_full = _G
            else:
                self._gc_full = np.where(_isF3, _G, _g0)
        if per_field:
            ed = self.elastic_driving()
            # ★★ 按**场**推进（2026-09-25 新增，方案 (a)）—— 见 `_advance_perfield` 的记账。
            #   走这条分支时后面那套"winner/runner-up 两场"逻辑整段跳过。
            gn_f = np.zeros_like(self.phi)
            stiff_f = np.ones((nreg,) + _shape)
            for k in range(nreg):
                g = np.gradient(self.phi[k], self.dx, edge_order=2)
                gn_f[k] = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
                stiff_f[k] = self._stiff_of(k, g, gn_f[k], npref, aniso, gamma0,
                                            herring, facet_lam, facet_eps)
            self._advance_perfield(dt, karr, larr, ed, stiff_f, iface_band,
                                   band_cells, adv_grad)
            return self._finish_advance(reg0, dt)
        kap_w = np.zeros(_shape)          # winner 的曲率（按 winner 索引）
        stk_w = np.ones(_shape)           # winner 的刚度
        stl_w = np.ones(_shape) if pair_kernel else None
        act = np.unique(np.concatenate((np.unique(karr), np.unique(larr))))
        self._t3_nact = int(act.size)

        def _geom_k(k):
            mw = (karr == k)
            ml = (larr == k)
            mk = mw | ml
            bb = _bbox_pad(mk, 2)
            if bb is None:
                return
            gsub = self.par.gradient(self.phi[k][bb], self.dx, edge_order=2)
            gnsub = np.sqrt(sum(gi ** 2 for gi in gsub)) + 1e-30
            kapsub = self.curvature_of(k, grad=gsub, gn=gnsub)
            # ★★ T9：刚度按**面片身份** (k, larr) 逐胞查表（`facet_id_gamma=False` 时退回旧行为）
            _nref_sub = (self.facet_nref(k, larr[bb], npref)
                         if getattr(self, 'facet_id_gamma', True) else None)
            stksub = self._stiff_of(k, gsub, gnsub, npref, aniso,
                                    (self._gc_full[bb] if self._gc_full is not None
                                     else gamma0),
                                    herring, facet_lam, facet_eps,
                                    nref_cell=_nref_sub)
            # ★★ T10：把**相干界面弹性能** `γ_el` 按面片身份加到界面上
            #   （`stk` 是"γ + γ_tt"，量纲 J/m² ⇒ 与 `γ_el` 可直接相加）。
            #   `lambda_el=0`（默认）⇒ **整段跳过** ⇒ 与 T10 之前逐位相同。
            #   `lambda_el` 是**敏感度旋钮**：1.0 = 全量计入，0 = 不计。
            if lambda_el > 0.0 and self._eps0_ref is not None:
                _gel = self.gel_facet_sub(k, np.asarray(larr[bb]))
                stksub = stksub + float(lambda_el) * _gel
            mwb = mw[bb]
            kap_w[bb][mwb] = kapsub[mwb]
            if np.ndim(stksub) == 0:
                stk_w[bb][mwb] = float(stksub)
                if stl_w is not None:
                    stl_w[bb][ml[bb]] = float(stksub)
            else:
                stk_w[bb][mwb] = stksub[mwb]
                if stl_w is not None:
                    stl_w[bb][ml[bb]] = stksub[ml[bb]]

        # ★★ R1（2026-09-29）：按场并行。**为什么安全**：各 k 的写入位置互不相交 ——
        #   一个胞的 winner 唯一 ⇒ `mwb = (karr[bb]==k)` 对不同的 k 是**不相交**的掩模
        #   （`stl_w` 那一路写 `ml[bb]`，同一胞的 runner-up 也唯一）⇒ 无竞争。
        #   `facet_nref` / `_stiff_of` / `curvature_of` 都是**纯函数**（只读实例表），
        #   唯一例外是 `gel_facet` 的 `_gel_cache`（dict 赋值在 GIL 下原子；且
        #   `lambda_el=0` 默认时根本不会被调用）。
        self.par.for_each([(lambda k=int(k): _geom_k(int(k))) for k in act],
                          tag='advance.geom_k')
        # ★ R-block：worker 已全部结束 ⇒ **立刻释放**这张 N³ 表，
        #   不让它常驻（N=192 时 56 MB）。它只在 `_geom_k` 里被读。
        self._gc_full = None
        # 每胞的配对速度（正 = winner 长大）
        # ★ T3：只算 winner/runner-up 两份（旧写法造 (nreg,N,N,N) 再 take_along_axis）
        edk, edl = self.elastic_driving_pair(karr, larr)
        stk = stk_w                       # T3：已按 winner 索引（原来是 take_along_axis(stiff,…)）
        pha = np.take_along_axis(self.phi, karr[None], 0)[0]
        phb = np.take_along_axis(self.phi, larr[None], 0)[0]
        # ---- P0.2 (2026-09-26): 按**配对**选各向异性参考取向 ------------------
        #   (k,0) 类界面 -> npref[k] (变体对母相的惯习面)
        #   (k,l) 类界面 -> ncmp[k,l] (两变体的不变平面, 见 _pair_normals)
        #   旧写法一律用 winner 的 npref[k] => 在 f->1 时对绝大多数界面用错对象.
        #   界面法向用**差分场** d = phi_k - phi_l 的梯度 (两侧对称, 且就是该界面的法向).
        _need_ref = (pair_aniso and aniso > 0) or (mob_aniso > 0.0) or (mob_beta > 0.0)
        # ★ D18 记账：把 `npref` 缓存到实例上，供 `nucleate()` 取新核的惯习面法向。
        #   （`nucleate()` 是在 `advance()` **之外**被每步调用的，拿不到这个局部变量。）
        self.npref_tab = npref
        nd_ref_ = None
        # AUDIT-#4 修：原来这里还要求 self.ncmp is not None，而 ncmp 只在
        #   (C is not None and eps0 is not None) 时才建 => 跑"单变体 vs 母相"(nv=1、
        #   不给 eps0) 时 ncmp=None => 整块被跳过 => **mob_beta 静默不生效**。
        #   现在：ncmp 缺失时退化为"只用 npref"，并在下面 has_pair 分支做保护。
        if _need_ref:
            gd_ = self.par.gradient(pha - phb, self.dx, edge_order=2)
            # ★★★ 2026-09-28（根因报告 ① 的候选修法，**默认关闭**）：`norm_smooth>0`
            #   时把差分场的梯度各分量做一次 `(2m+1)³` 盒式平滑再归一化。
            #   动机（`_probe_LT.py` + `_probe_LT_ed.log` 实测）：
            #     `M(n)=M0exp[−β_h(n·n*)²−β_w(n·w)²]` 在**慢方向的极小值附近很陡**，
            #     而界面法向取自 `∇d`，带内 `|∇d|` 中位只有 **0.70–0.93**（应 ≈1）
            #     ⇒ 法向有散布 ⇒ **噪声把慢方向的迁移率抬高**、压缩各向异性对比。
            #   实测证据：设计 长:厚 = 33，Δx=50 nm 只有 **8.45**、Δx=25 nm 回到 **14.34**
            #     ⇒ 确为离散效应；而 `ed` 在三个面几乎相同（−2.80/−3.05/−2.90e8）
            #     ⇒ **不是弹性顶住**，只能是 `M(n)` 的输入（法向）被污染。
            #   这正是 `MEASUREMENT_SPEC R3` 早已记录的口径：
            #     "局部法向（中心差分）阶梯上振荡 ⇒ 或对法向做平滑/粗 stencil"。
            #   ⚠ 记账：本改动**默认 `norm_smooth=0`（不生效）**，归档结果不受影响；
            #     要用必须显式传参，并按 `MEASUREMENT_SPEC R8` 重跑引用它的判据。
            if norm_smooth > 0:
                # ★★ Round 92 修（`WINDOWB_AUDIT_REGISTER.md` A15 第②条，**静默失效**）：
                #   `0 < norm_smooth < 1`（如 0.5）⇒ `2*int(0.5)+1 = 1` ⇒ `_k = [1.0]`
                #   ⇒ **恒等滤波**：参数"看起来生效、实则什么也没做"。
                #   ⇒ 改为显式拒绝。`norm_smooth` 的语义是**胞数半径**，必须是 ≥1 的整数。
                if not float(norm_smooth).is_integer() or int(norm_smooth) < 1:
                    raise ValueError(
                        'norm_smooth 必须是 >=1 的整数（单位=胞）；得到 %r。'
                        '0<x<1 会退化成恒等滤波（静默失效），负值整段关闭。' % (norm_smooth,))
                _m = int(norm_smooth)
                _k = np.ones(2 * _m + 1) / (2 * _m + 1)
                gd_ = [self._sep_conv3(g_, _k) for g_ in gd_]
            gdn_ = np.sqrt(sum(g_ ** 2 for g_ in gd_)) + 1e-30
            ndir_ = np.stack([g_ / gdn_ for g_ in gd_], -1)
            ndir_ = ndir_ / (np.linalg.norm(ndir_, axis=-1, keepdims=True) + 1e-300)
            np_arr = np.full((nreg, 3), np.nan)
            if npref is not None:
                for kk, vv in npref.items():
                    if vv is not None and 0 <= int(kk) < nreg:
                        vv = np.asarray(vv, float)
                        np_arr[int(kk)] = vv / (np.linalg.norm(vv) + 1e-300)
            ncl = getattr(self, 'ncmp', None)
            ki = np.clip(karr, 0, nreg - 1)
            li = np.clip(larr, 0, nreg - 1)
            has_pair = (karr > 0) & (larr > 0)
            if ncl is None:
                # AUDIT-#4: 没有配对表 => 变体-变体界面也退化为用 winner/runner-up 的 npref
                nd_ref = np.where((karr > 0)[..., None], np_arr[ki], np_arr[li])
            else:
                nd_ref = np.where(has_pair[..., None], ncl[ki, li],
                                  np.where((karr > 0)[..., None], np_arr[ki], np_arr[li]))
            badp = ~np.isfinite(nd_ref).all(-1)
            if badp.any():
                nd_ref = np.where(badp[..., None], np_arr[ki], nd_ref)
            c2p = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref) ** 2, 0.0, 1.0)
            nd_ref_ = nd_ref
            if pair_aniso and aniso > 0:
                stk = herring_stiffness(c2p, self.gamma if gamma0 is None else gamma0,
                                        aniso, herring)
            self._pair_aniso_used = True
        elif pair_aniso:
            self._pair_aniso_used = False
        # ★★ 按配对（pair-canonical）核 —— 本轮修的关键点：
        #   旧写法用 "winner 自己的曲率 κ_karr" 与 "winner 自己的刚度"，跨界面时曲率项
        #   在两侧**不对称**（内侧用 κ_karr、外侧用 κ_larr）⇒ 与"按区域"的速度扩展叠加后，
        #   两区域之间的差分 φ_k−φ_l 会被无限拉陡（实测带内 |∇φ| 0.5→530、带胞 3.7e4→155，
        #   几何测度静默归零 ✗）。
        #   改成用**差分场** d = φ_karr − φ_larr 的曲率（对两侧严格对称、且保持 winner 的
        #   符号约定）与**成对平均刚度** ⇒ 界面速度成为该配对的单一标量，两侧一致。
        if pair_kernel:
            # ★★ T11j（2026-09-28）：差分场**按区域编号定向**（`σ = sign(l−k)`）。
            #   旧写法 `dd = pha - phb` 用的是 winner/runner-up 次序，而 `karr/larr`
            #   **跨界面会互换** ⇒ `∇dd` 的方向跨界面翻转 ⇒ `div(∇dd/|∇dd|)` 翻号
            #   ⇒ 界面两侧的曲率项互相抵消。**这解释了仓库注释里
            #   "pair_kernel 平界面标定实测 0.00 ✗"** —— 当年失败的原因就是这个。
            dd = np.where(karr < larr, 1.0, -1.0) * (pha - phb)
            gd = np.gradient(dd, self.dx, edge_order=2)
            gdn = np.sqrt(sum(g ** 2 for g in gd)) + 1e-30
            nd = [g / gdn for g in gd]
            kap_pair = sum(np.gradient(nd[i], self.dx, edge_order=2)[i] for i in range(3))
            # ★★★ A1（2026-09-28）：**同一条 winner 定向因子**（病灶与修法见下面 else 分支
            #   的长记账）。`dd = σ(pha−phb)` 是按区域编号定向的 ⇒ `div(∇dd/|∇dd|)`
            #   的正号含义是"**编号较小**的区域凸"，而下游要的是"**winner** 凸"
            #   ⇒ 乘 `σ` 换回 winner 口径。
            if not getattr(self, '_pc_legacy', False):
                kap_pair = np.where(karr < larr, 1.0, -1.0) * kap_pair
            stk_pair = 0.5 * (stk + stl_w)      # T3：stl_w 已按 runner-up 索引
            kap_cell = kap_pair
            stk = stk_pair
        else:
            # ★★ T11h（2026-09-28，修 EXPERT-#4）：曲率改用**差分场** `d = φ_karr − φ_larr`。
            #
            #   病灶（T11-C 实测）：旧写法取 **winner 场自己的曲率** ⇒ 界面两侧不对称：
            #     内侧（winner = 区域 1）`κ = div(∇φ₁/|∇φ₁|) = +2/r`
            #     外侧（winner = 区域 0）`κ = div(∇φ₀/|∇φ₀|) = −2/r`  ← **符号翻转**
            #   ⇒ 两侧的 `−γ·κ` 一正一负、**互相抵消** ⇒ 曲率驱动被系统性削弱。
            #   **实测**：Gibbs–Thomson 平衡半径应为 `2γ/Δf = 300 nm`，而球长到 1850 nm
            #   仍不停 ⇒ `γ_eff/γ = 5.9–6.2`（≈6 倍削弱）✓ 与该机制定量吻合。
            #
            #   为什么差分场是对的：`∇d = 2∇φ_k`、`|∇d| = 2`（本轮实测恰好 **2.0000**）
            #   ⇒ `div(∇d/|∇d|) ≡ div(∇φ_k/|∇φ_k|) = κ_k`，**且跨界面连续**
            #   （`d` 翻号但 `∇d` 方向不变）⇒ 两侧拿到**同一个**κ ✓
            #   —— 与 T2 的 `pair reinit` 用的是同一套"差分场才是界面"的道理。
            #   ⚠ 记账：这**改变了所有用曲率的归档结果**（板条尖端、Gibbs–Thomson、
            #     Ostwald）。回归守卫：T11-A′（速度）与 T11-B（面积）不得退化。
            # ★★★ A1（2026-09-28）：**默认改为走差分场曲率**（`pair_curvature` 的默认值
            #   由 False 改为 True）。依据（`T22_verify_paircurv.py`）：
            #     ① **在旧路径本来正确的地方，新路径逐位相同**：两区域（变体-母相）算例上
            #        `σ·div(∇(σΔφ)/|∇(σΔφ)|)` 与 `kap_w` 的最大相对差 = **0.000e+00** ✓
            #        （因为那里 `∇φ_0 = −∇φ_1`、两个场都是单位 SDF）。
            #     ② **在旧路径错的地方，新路径才对**：多核演化态里实测变体-变体界面的
            #        `|∇φ_k|/|∇φ_l|` 中位 = **2.762**（理想 1.000）、`|cos(∇φ_k,∇φ_l)|` = 0.810
            #        ⇒ 那里的 winner 场**不是单位 SDF** ⇒ `div(∇φ_k/|∇φ_k|)` **不是**
            #        界面的几何曲率；而 `div(∇d/|∇d|)` 做了归一化、与各场的尺度无关 ⇒
            #        **才是**几何曲率。
            #     ③ 已知答案两连（新路径）：纯曲率流下凸球**单调收缩**（V/V0 0.912→0.661）；
            #        Gibbs–Thomson 理论 `R_c = 2γ/Δf = 125 nm`，实测 `R0=R_c` 时 `V/V0 = 0.989`
            #        （应 1.000）✓ —— 曲率项**定量正确**。
            #   ⚠ 记账：这**改变了所有用曲率的归档结果**（板条尖端、Gibbs–Thomson、Ostwald）。
            #     回归守卫：T9-D（最薄角 <20°）、T19-C（键/干净阶梯 ≤1.15）、T11-A′/B。
            if getattr(self, 'pair_curvature', True):
                # ★★ 定向：**必须按区域编号** `σ = sign(l−k)`，不能沿用 winner/runner-up 次序 ——
                #   `karr/larr` 跨界面会互换 ⇒ `∇(φ_karr−φ_larr)` 的方向跨界面翻转
                #   ⇒ `div(∇d/|∇d|)` **跟着翻号**（实测：外侧 κ<0 ⇒ −γκ>0 ⇒ 反而加速，
                #   连 R0=100 nm 的球都涨 4783×）。按编号定向后 `d` 的符号一侧恒负、一侧恒正，
                #   `∇d` 方向一致 ⇒ κ 跨界面连续 ✓
                _sg = np.where(karr < larr, 1.0, -1.0)
                _dd = _sg * (pha - phb)
                _gd = self.par.gradient(_dd, self.dx, edge_order=2)
                _gn = np.sqrt(sum(_g ** 2 for _g in _gd)) + 1e-30
                _kap_idx = self.curvature_of(0, grad=_gd, gn=_gn)
                # ★★★ A1（2026-09-28）**补上丢掉的 winner 定向因子** —— 这是 T11j
                #   "`pair_curvature=True` 仍全涨（R0=100 nm 都涨 6185×）"的**真正原因**。
                #
                #   病灶：`_dd = σ·(φ_karr−φ_larr)` 是**按区域编号**定向的（为了使 κ 跨界面连续），
                #     所以 `_dd < 0` 恒在**编号较小**的那个区域里 —— 而**不是**在 winner 里。
                #     而下游的符号约定是 `dG = ... − stk·κ`，要求
                #     **κ > 0 ⟺ winner 区域是凸的**（凸 ⇒ 回退 ⇒ v<0）。
                #     于是当 `karr > larr` 时，编号定向给出的 `κ` 与"winner 凸"**恰好反号**
                #     ⇒ 曲率项把"回退"变成"前进" ⇒ 球无限涨 ✓ 与实测（全涨）吻合。
                #
                #   修法（一行）：`κ_winner = σ · div(∇(σ·Δφ)/|∇(σ·Δφ)|)`。
                #     验算：`karr<larr`（σ=+1）⇒ `_dd=φ_karr−φ_larr`，∇_dd 由 winner 指向外
                #       ⇒ 凸 winner 给 `div=+2/R` ⇒ `κ=+2/R` ✓；
                #     `karr>larr`（σ=−1）⇒ `_dd=φ_larr−φ_karr`，∇_dd 由外指向 winner
                #       ⇒ 凸 winner 给 `div=−2/R` ⇒ `κ=(−1)(−2/R)=+2/R` ✓。
                #     ⇒ 两种情况都给 `κ=+2/R`（winner 凸）⇒ **跨界面连续且符号正确**。
                kap_cell = _kap_idx if getattr(self, '_pc_legacy', False) else _sg * _kap_idx
            else:
                kap_cell = kap_w                  # T3：已按 winner 索引（旧行为）
            # ★★★ A1（2026-09-28）：**旧告警的前提被证伪，改成"条件告警"**。
            #   旧告警断言："`pair_kernel=False` 时变体-变体界面的曲率取自 winner 场
            #   ⇒ 两侧不对称 ⇒ 形貌结论可能有偏"。
            #   `T22_verify_paircurv.py` 实测这条**不成立**：
            #     · 约定是 `v = M(Δf − γκ)`、**winner 长大为正**；跨界面时 winner 互换
            #       ⇒ 两侧算的是**同一个物理速度**（要求 `κ_l ≈ −κ_k`），不是互相抵消。
            #     · 凸球 + γ>0 + Δf=0 ⇒ 默认路径**单调收缩**（V/V0 0.912→0.661）✓
            #     · Gibbs–Thomson：理论 `R_c = 2γ/Δf`；实测 `R0 = R_c` 时 `V/V0 = 0.989`
            #       （≈ 不动 ✓）、`0.5R_c` 收缩、`2R_c` 长大 ⇒ **定量正确** ✓
            #     · 反面对照：把 σ 去掉的旧写法（`_pc_legacy`）**不收缩**（1.000→0.969）、
            #       **没有临界半径**（全涨）⇒ 对照有分辨力 ✓
            #   ⇒ 默认路径**不是缺陷**。真正的**前提条件**是"两个场的 SDF 在界面附近
            #     互为镜像"（`∇φ_k ≈ −∇φ_l`、`|∇φ_k| ≈ |∇φ_l|`）—— 这里**直接量它**，
            #     只在被违反时告警（避免"每天都在打印一条不成立的告警"）。
            if (not getattr(self, '_mirror_checked_step', None)) or True:
                # ★ A1 记账：**必须每一步都量**（首版只在第一次 `advance` 时量一次，
                #   而那时种子还没碰撞 ⇒ 测到的是"没有变体-变体界面"的状态）。
                _hp = (karr > 0) & (larr > 0)
                self._n_vv = int(_hp.sum())
                if _hp.sum() > 0:
                    _gk = self.par.gradient(pha, self.dx, edge_order=2)
                    _gl = self.par.gradient(phb, self.dx, edge_order=2)
                    _nk = np.sqrt(sum(t ** 2 for t in _gk)) + 1e-30
                    _nl = np.sqrt(sum(t ** 2 for t in _gl)) + 1e-30
                    _cos = sum(_gk[i] * _gl[i] for i in range(3)) / (_nk * _nl)
                    self._pair_mirror = float(np.median(np.abs(_cos)[_hp]))
                    self._pair_scale = float(np.median((_nk / _nl)[_hp]))
                    if (self._pair_mirror < 0.8 or not (0.7 < self._pair_scale < 1.4)) \
                            and not getattr(self, '_warned_pair_kernel', False):
                        import warnings as _w
                        _w.warn('variant-variant interfaces: mirror-SDF precondition FAILS '
                                '(median |cos| = %.3f, |grad k|/|grad l| = %.3f) => the '
                                'winner-field curvature would NOT be the interface '
                                'curvature; the difference-field path is used instead '
                                '(see T22_verify_paircurv.py).'
                                % (self._pair_mirror, self._pair_scale),
                                RuntimeWarning, stacklevel=2)
                        self._warned_pair_kernel = True
                else:
                    self._pair_mirror = np.nan
                    self._pair_scale = np.nan
        dG_cell = (self.df[karr] - self.df[larr]) + (edk - edl) - stk * kap_cell
        # ★★ 记账（2026-09-25，查明 M2"塌缩"的真凶）：把本步驱动力存下来，供
        #   `suggest_dt` 按**总驱动**定 CFL。**只用 Δf 估 dt 会严重低估界面速度** ——
        #   实测 M2：弹性项中位 4.9e8 是 Δf(1e8) 的 ~5 倍 ⇒ 按 Δf 定出的 dt 实际每步
        #   位移是 **0.6–0.75 dx**（不是 0.15），一阶迎风必然失真。
        # AUDIT-#3 修：原来 dG_max = max|dG_cell| **不含 Mfac** => Mfac 小的界面上
        #   dt 被按"未压制的驱动力"定，最多保守 33 倍（白算机时）。
        #   现在改存"有效驱动"，在 Mfac 应用之后重算（见下面 _dG_max_from_mfac）。
        self.dG_max = float(np.max(np.abs(dG_cell)))
        self._dG_cell_ref = dG_cell          # 供 Mfac 应用后重算 dG_max
        if drag is not None:
            # ★★ 溶质拖曳（P3.3 / 框架 §6.3 [RULE] K5）：**隐式自洽**解
            #     v = M[ΔG − P_drag(v)]，P_drag = P0/(1+v/v*)（双盒闭式，K1 已验）。
            #     绝不能用线性闭式 v = MΔG(1−a v)：在被钉扎的驱动下它会**凭空给出速度**
            #     （模块 7 K3 实测偏差 98%），而隐式解给出 v=0 ✓。
            #     脱钉判据（本模块数值验证）：v>0 ⟺ ΔG>P0 或 M·ΔG>v*。
            from windowB_drag import solve_v
            P0, vstar = drag
            v_cell, _pin = solve_v(dG_cell, self.M, P0, vstar)
        else:
            v_cell = self.M * dG_cell
        # ---- P0.5 (2026-09-26): 界面**迁移率**各向异性（facet pinning）----------
        #   物理与 D8 正对照（_chk_m8_mobpin.py，真实驱动力 df=1e8 下）：
        #     gamma(n) 通道被驱动力完全淹没（P0.3），而 M(n) 是**动力学**量、
        #     无热力学凸性约束 => 强度可任意大，实测能把形状取向精确钉住（主轴偏差 0.0 deg）。
        #   形式： M(n) = M0 * [1 - a*(n.n*)^2]        (pin_min=True, 默认)
        #          => n 平行 n* 时迁移率最小（法向长得慢）、面内长得快
        #          => 形状是"沿 n* 法向的薄片" = **板条**的几何（不是"沿 n* 的针"）
        #          这与惯习面物理一致：板条的**宽面**是惯习面，其法向 = n*。
        #      M(n) = M0 * [1 - a*(1-(n.n*)^2)]    (pin_min=False)
        #          => 沿 n* 长得最快 => 形状沿 n* 拉长（"针状"形态）
        #   ⚠ 记账：D8 的 a00..a100 用的是 pin_min=False（当时 mref = 快生长方向），
        #     所以它给的是"沿 mref 拉长"；那组数据证明的是**机制有效**（主轴 0.0 deg、
        #     长径比单调 1.00->2.15），不是"板条已得到"。板条要用 pin_min=True + n*=惯习面法向。
        # ★★ P1' (2026-09-26): **物理形式** M(n) = M0*exp[-beta*(n.n*)^2]，
        #   beta = dG_misfit/(k_B T)（位移型界面靠界面位错保守滑移迁移：
        #   Olson-Cohen / Christian；位错只能在其滑移面=惯习面内滑移 =>
        #   法向生长必须容纳失配 => 额外激活能 ∝ (n.n_hab)^2 的几何投影）。
        #   标定见 LATH_FACET_PLAN §9：位错环形成能 => beta~3.8；板条纵横比反推 => beta~3.0
        #   => 取 beta=3.5（带 [3,6]）。M_min = 3% M0 => 界面不会被冻结（数值安全）。
        _mfac_dt = 1.0                          # AUDIT-#3: 累积的 Mfac（用于重定 dt）
        if mob_beta > 0.0 and nd_ref_ is not None:
            c2b_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)
            # ★ P2：**第二钉扎轴** w = n_hab x a（板条宽度方向）。
            #   只对"变体-母相"界面加（板条成形主要发生在从母相长大的阶段）；
            #   变体-变体界面保持单轴（那里 ncmp 已是不变平面，w 无独立意义）。
            _expo = -mob_beta * (c2b_ if pin_min else (1.0 - c2b_))
            if mob_beta_w > 0.0 and getattr(self, 'wtab', None) is not None:
                ki2 = np.clip(karr, 0, nreg - 1)
                li2 = np.clip(larr, 0, nreg - 1)
                w_of = np.where((karr > 0)[..., None], self.wtab[ki2], self.wtab[li2])
                okw = np.isfinite(w_of).all(-1)
                c2w_ = np.clip(np.einsum('...i,...i->...', ndir_, np.where(
                    okw[..., None], w_of, 0.0)) ** 2, 0.0, 1.0)
                # EXPERT-#5 修：第二钉扎轴 w **只对变体-母相界面**施加（与上面注释一致）。
                #   原写法只要 winner 是变体就用它的 w => 变体-变体界面也被加了 w 轴钉扎，
                #   于是实际模型是"变体-母相:双轴 / 变体-变体:winner 的双轴"，
                #   而不是设计中的"变体-变体:只按相容法向单轴"（会改变变体间界面选择）。
                _has_pair_ = (karr > 0) & (larr > 0)
                _use_w = (~_has_pair_) & okw
                _expo = _expo - mob_beta_w * np.where(_use_w, c2w_, 0.0)
            _mfac_dt = np.exp(_expo)
            v_cell = v_cell * _mfac_dt
        # AUDIT-#6 修：mob_beta 与 mob_aniso 是两套等价机制的**不同参数化**，
        #   同时给非零会相乘 => 双重调制（静默的错）。这里显式拒绝。
        if mob_beta > 0.0 and mob_aniso > 0.0:
            raise ValueError('mob_beta 与 mob_aniso 不能同时给非零（会双重调制）')
        if mob_aniso > 0.0 and nd_ref_ is not None:
            c2r_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)
            Mfac = 1.0 - mob_aniso * (c2r_ if pin_min else (1.0 - c2r_))
            _mfac_dt = Mfac
            v_cell = v_cell * Mfac

        # ★★ （本轮修·关键）界面速度的**配对规范形**（跨界面连续化）。
        #    `v_cell` 是"winner 长大为正"的约定 ⇒ 跨过界面时 winner 换成 runner-up
        #    ⇒ 同一界面两侧的 `v_cell` **符号相反**。速度延拓要求被延拓的场在界面上
        #    **连续**；否则最近点延拓会把一侧的符号搬到另一侧 / 两侧种子互相抵消 ✗。
        #    规范形按 min(k,l) 定向 ⇒ 跨界面连续：V_c = M(df_min − df_max) = sigma·v_cell。
        #    随后每胞用**同一标量**：φ_karr 取 +V_ab = +sigma·V_c，φ_larr 取 −sigma·V_c。
        # AUDIT-#3: 用**有效驱动**重定 dt（原来用未压制的 dG）
        if not isinstance(_mfac_dt, float):
            self.dG_max = float(np.max(np.abs(self._dG_cell_ref * _mfac_dt)))
        sigma = np.where(karr < larr, 1.0, -1.0)
        vcanon = sigma * v_cell
        # ★★ 记账：和单畴一样，**必须做速度扩展**，而且多畴对带宽更敏感 ——
        #   实测（平界面 + 常数驱动 ΔG，40 步后的 v/MΔf，应 = 1.000）：
        #      无扩展 band=2dx → 0.250 ; band=6dx → 0.750 ; band=12dx → 2.000（乱）
        #      EDT 扩展 band=5dx → 0.500 ; 10dx → 0.750 ; **20dx → 1.0000** ✓
        #   物理原因：扩展让速度**沿法向为常数** ⇒ 整个剖面是**纯平移**（保 SDF、保速度）；
        #   带太窄时带外剖面不动 ⇒ 带边折点累积 ⇒ 有效速度塌（与单畴 P6 同源）。
        #   ⇒ 多畴默认 `extend='edt', band_cells=20`（宽带 + 扩展才自洽）。
        #   ⚠ 这解释了为什么旧的 `_chk_w2.py`（阶跃初值 + 默认扩展）得到 1.0000：
        #     那是**退化构型**下的巧合；用真 SDF 初值必须靠宽带+扩展才复现 1.0000。
        #    多畴的额外要求（★ 本轮修正）：延拓必须**跨越界面两侧**（按**无序对**
        #    {karr,larr} 判定配对身份），且被延拓的量必须是**跨界面连续**的规范形
        #    `vcanon`。旧的 `karr == karr[最近界面胞]` 约束把界面的 runner-up 一侧
        #    整个排除 —— 这是本轮用**亚胞射线交点**口径抓到的真 bug（见下）。
        if pair_kernel:
            # ★★ 配对口径：界面 = 差分场 d = φ_karr − φ_larr 的小值集，速度沿 d 的
            #    法向延拓 ⇒ 界面两侧拿到**同一个标量速度** ⇒ 差分 d 只**平移**、不被拉陡
            #    （对比：按区域延拓时 |∇φ| 0.5→530 ✗）。
            #    ★ 本轮修两处：(i) 延拓**规范形** `vcanon`（`v_cell` 跨界面符号翻转，
            #    把两侧种子放一起会**互相抵消** ✗）；(ii) 带按 `|∇d|` 折算（`d` 不是
            #    距离函数、|∇d|≈2 ⇒ 旧写法 `|d| ≤ 1.0dx` 在 48³ 上只选到 **1 层**胞）。
            dfield = pha - phb
            gdd = np.gradient(dfield, self.dx, edge_order=2)
            gdn = np.sqrt(sum(g ** 2 for g in gdd)) + 1e-30
            iface = (np.abs(dfield) <= iface_band * self.dx * gdn) \
                & (np.abs(v_cell) > 0)
            band = np.abs(dfield) <= band_cells * self.dx * gdn
            if iface.any() and not iface.all():
                v_ext = extend_along_normal(np.where(iface, vcanon, 0.0), dfield,
                                            self.dx, iters=int(band_cells / 0.4) + 6)
                coef = np.where(band, sigma * v_ext, 0.0)
            else:
                band = iface
                coef = np.where(iface, sigma * vcanon, 0.0)
        else:
            phiw = np.take_along_axis(self.phi, karr[None], 0)[0]
            iface = (np.abs(phiw) <= iface_band * self.dx * (1.0 + 1e-9)) \
                & (np.abs(v_cell) > 0)
            # ★ 守卫：`distance_transform_edt(~iface)` 要求 `~iface` 非空（否则索引为垃圾）
            if extend and iface.any() and not iface.all():
                ind = distance_transform_edt(~iface, return_distances=False,
                                             return_indices=True)
                dist = distance_transform_edt(~iface)
                v_at = np.where(iface, vcanon, 0.0)
                kat = karr[tuple(ind)]
                lat = larr[tuple(ind)]
                # ★★ 本轮修的真 bug（被亚胞射线交点口径抓到）：旧写法用
                #   `karr == kat`（"与最近界面胞**同区域**"）。但 `iface` 往往
                #   **只落在 winner 一侧**（实测：`dx = L/N` 的浮点尾差让
                #   |φ_winner| = dx 的胞判为带外 ⇒ iface 只剩 winner=0 的胞）
                #   ⇒ `kat ≡ 0` ⇒ **runner-up 一侧从不被推进**。实测后果（z 剖面）：
                #   φ_1 只在 z>z0 侧平移、z<z0 侧冻结 ⇒ 差分场 d=φ_k−φ_l 不平移而只被
                #   **拉陡** ⇒ 射线口径 40 步位移 6.31dx（应 4dx）、单步 0.0909dx
                #   （应 0.1dx）；而 `region()` 计数法靠"符号翻转"**凑巧**给出 1.0000
                #   —— 计数法掩盖结构错误的教科书案例（审计 §10 的 0.000 亦须重判）。
                #   正确掩模按**界面的配对身份**（无序对 {k,l}），两侧一视同仁。
                same_pair = ((karr == kat) & (larr == lat)) | \
                            ((karr == lat) & (larr == kat))
                band = (dist <= band_cells) & same_pair
                # ★★ T11e（2026-09-28）：**配对符号的来源**（默认不改行为，供判决实验）。
                #   现写法用**本胞**的 `sigma`；而 `v_at[ind]` 带的已经是**种子胞**的
                #   规范形（`vcanon = sigma_种子 · v_cell`）⇒ 两者相乘 =
                #   `sigma_本胞/ sigma_种子 · v_cell`，**跨界面次序翻转时会变号**。
                #   `pair_sig_from_seed=True` 时改用**种子胞的 sigma**，
                #   使 `coef` 跨界面**连续**（这正是注释里写的设计意图）。
                if getattr(self, 'pair_sig_from_seed', False):
                    _sig_at = sigma[tuple(ind)]
                else:
                    _sig_at = sigma
                coef = np.where(band, _sig_at * v_at[tuple(ind)], 0.0)
            else:
                band = np.zeros(self.phi.shape[1:], bool)
                for k in range(nreg):
                    band |= ((karr == k) | (larr == k)) & (np.abs(self.phi[k])
                                                           <= band_cells * self.dx)
                band = band & (np.abs(v_cell) > 0)
                coef = np.where(band, sigma * vcanon, 0.0)
        # ★★ D17（2026-09-28）**投影型（保几何）平流** —— P1 的结构性修法。
        #   把"法向速度"投影成**矢量**速度场 `V = v_canon·n_orient`，再用
        #   `upwind_flux_vec` 对 `φ_t + V·∇φ = 0` 做迎风通量。
        #   ① `v_canon_ext = sigma·coef`：两个分支下都等于"带内延拓后的标量 v_canon"
        #      （延拓分支 `coef = sigma·v_at[ind]` ⇒ `sigma·coef = v_at[ind]`；
        #        退化分支 `coef = sigma·vcanon` ⇒ `sigma·coef = vcanon`），**跨界面连续** ✓
        #   ② `n_orient = ∇d/|∇d|`，`d = sigma·(φ_karr−φ_larr)` —— 与 T11j 修的
        #      `pair_kernel` 用**同一个**定向（按区域编号，不按 winner 次序）
        #      ⇒ `∇d` 跨界面不翻号 ✓（这是仓库里踩过的坑，不要再改回去）
        #   ③ 两个场共用同一个 `V` ⇒ 差分场 d 只平移（结构性保证）
        _is_proj = (adv_grad in ('proj', 'proj2'))
        if _is_proj:
            _vc_ext = sigma * coef
            _dd = np.where(karr < larr, 1.0, -1.0) * (pha - phb)
            _gd = self.par.gradient(_dd, self.dx, edge_order=2)
            _gn = np.sqrt(sum(_g ** 2 for _g in _gd)) + 1e-30
            Vvec = [_vc_ext * (_g / _gn) for _g in _gd]
        else:
            Vvec = None
        # ★★★ R1 任务②（2026-09-29）：**逐场推进改为多核并行**。
        #   为什么这一处是"并行化收益最大、风险最小"的：
        #     ① **天然无依赖**：第 k 个场只读 `self.phi[k]` 与 `Vvec`（只读），
        #        只写 `self.phi[k]`（第 k 行，各 k **互不相交**）⇒ 不需要 halo、
        #        不需要同步、不需要通信。
        #     ② 它是**单步里最贵的一块**：`upwind_flux_vec(order=2)` 每次调用约
        #        **60 个 DRAM 级 pass**，被每个活跃场各调一次（最多 13 次）
        #        ⇒ 实测 0.854 s × 13 ≈ 11 s（N=192，占 `advance` 的 ~1/3）。
        #     ③ 实测加速比 ×2.43 @20 线程（`_w2_r1par_N192.log`，算子级）。
        #   ★★★ **自查抓到的一处我自己的错**（记账，`AGENTS §3.24` 的同类陷阱）：
        #     我最初以为这个循环体里写了 `self.dG_max`（共享标量）⇒ 并行会有竞态，
        #     于是加了一行 `self.dG_max = max_k max|vnk| / M` 去"修"它。
        #     **逐行核对后确认：本循环体里根本没有 `dG_max` 赋值** ——
        #     它的唯一来源在 `advance` 的前半段（`:2664` 的 `max|dG_cell|`，
        #     或 `:2737` 的 `max|dG_cell·Mfac|`），**在循环之前就已定值、无竞态**。
        #     ⇒ 我那一行是**凭想象加的行为改动**，会静默改掉 `dG_max` 的语义
        #       （`suggest_dt` / `_t21b_1step.py` / `prod_boxB_mob.py` / `_chk_m6_route.py`
        #        都在读它）⇒ **已删除**。本循环**只**并行化，**不碰** `dG_max`。

        def _step_k(k):
            vnk = coef * (np.where(karr == k, 1.0, 0.0)
                          - np.where(larr == k, 1.0, 0.0))
            if not np.any(vnk != 0):
                return
            if _is_proj:
                # ★★ D17：矢量速度 + 迎风通量（两场共用同一个 V）
                self.phi[k] = self.phi[k] - dt * self.par.upwind_flux_vec(
                    self.phi[k], Vvec, self.dx,
                    order=(2 if adv_grad == 'proj2' else 1))
            elif adv_grad == 'central':
                g = self.par.gradient(self.phi[k], self.dx, edge_order=2)
                gmag = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
                self.phi[k] = self.phi[k] - dt * vnk * gmag
            else:
                sgn = np.where(vnk > 0, 1.0, -1.0)
                gmag = self._upwind_grad(self.phi[k], sgn)
                self.phi[k] = self.phi[k] - dt * vnk * gmag

        self.par.for_each([(lambda k=k: _step_k(k)) for k in range(nreg)],
                          tag='advance.k_loop')
        return self._finish_advance(reg0, dt)

    def _finish_advance(self, reg0, dt=None):
        """推进一步的**收尾**（两条推进路径共用，避免两处分叉）：
           区域/计数、按平流取 `reg_adv`、定期重初始化、Stefan 记账。
           ★ 记账：Stefan 必须只对"**平流**扫过的胞"记账。旧写法在 `reinitialize()`
             之后才取 reg1 ⇒ 把**重初始化微移界面**造成的区域翻转也算成"前沿扫过"
             ⇒ 凭空吞吐溶质（实测：关重初始化 M4=1.16e-2、每 20 步重初始化 5.37e-2 ✗）。"""
        reg = self.region()
        self._cnt = getattr(self, '_cnt', 0) + 1
        # AUDIT-#10 修：原来这里又写了一次 self.region()（中间无修改 => 与 reg 相同）。
        #   逻辑本来就对（此处仍在 reinitialize 之前 => 只反映【平流】造成的扫过），
        #   只是重复计算；直接复用 reg。
        reg_adv = reg
        # ★★ T11：重初始化的触发改成"**物理时间**优先"（见 __init__ 的记账）
        if dt is not None:
            self._t_since_reinit = getattr(self, '_t_since_reinit', 0.0) + float(dt)
        _do_re = False
        if getattr(self, 'reinit_dt', None):
            if self._t_since_reinit >= self.reinit_dt:
                _do_re = True
        elif self.reinit_every and self._cnt % self.reinit_every == 0:
            _do_re = True
        if _do_re:
            self.reinitialize()
            self._t_since_reinit = 0.0
        # ★★★ W1-3（2026-09-28，`C4`）：**种核后的强制 reinit**。
        #   为什么单独一条：`nucleate()` 是在 `advance()` **之外**被每步调用的，
        #   它由 `seed_plate` 在盘内覆写 `φ_j` ⇒ 盘边界有 O(|旧 φ_j|) 的跳变，
        #   而定时 reinit 可能因跳过容差而不执行 ⇒ 跳变一路带下去（**且不报错**）。
        #   ⇒ 只要`nucleate()` 本轮真发生过事件（`_need_reinit`），就**强制**补一次。
        #   ⚠ 不形核的算例**逐位不变**（标志不会被置位）。
        if getattr(self, '_need_reinit', False):
            self._need_reinit = False
            self.reinitialize(force=True)
            self._t_since_reinit = 0.0
            self._forced_reinit = getattr(self, '_forced_reinit', 0) + 1
        self._stefan(reg0, reg_adv)
        return reg

    def _advance_perfield(self, dt, karr, larr, ed, stiff, iface_band,
                          band_cells, adv_grad):
        """★ 按**场**推进（2026-09-25，方案 (a)）：每个 φ_k 用它**自己最近界面**
           `{k, l_k}`（`l_k(x) = argmin_{j≠k} φ_j(x)`）的配对速度，速度沿该界面的法向
           延拓到带内，然后 `φ_k −= dt·V_k·|∇φ_k|`（Godunov 迎风）。

           ★ 记账（为什么需要它）：旧写法每胞只推进局部 `(winner, runner-up)` **两个场**
             ⇒ **"被推进的场集合"在空间上跳变**（一侧推进、紧邻一侧冻结）⇒ φ 上出现
             跳变、再被 `|∇φ|` 项自放大 ⇒ 带胞与 `|∇φ|` 静默退化（§9.5/§10.4 的全部
             隔离实验都指向这里，而不是配对扩展）。
             本写法每胞推进**全部 nreg 个场**（各自带内）⇒ 跳变只剩"速度值的跳变"
             （在 `l_k` 切换的中性面上），**不再有"零速区"** ✓。
           ★ 另一个便利：这里 `V_k` **总是以 k 为被减数** ⇒ 跨 k 的界面**天然连续**
             （不需要 §10.2 里 `sigma`/`vcanon` 那套规范化）；
             曲率必须取**差分场** `d = φ_k − φ_{l_k}` 的（单场自己的曲率在界面两侧
             **符号相反**：球内 φ_k = r−R 给 +2/R，球外 φ_l 给 −2/R ⇒ 两侧会互相打架 ✗）。
           ★ 代价（如实记账）：每步 `nreg` 次差分场曲率 + `2·nreg` 次 EDT ⇒ 比旧路径
             O(nreg) 倍（N=64/nreg=13 约 ~0.5–1 s/步）。
        """
        for k in range(self.nreg):
            lk = np.where(karr == k, larr, karr)     # k 的最近竞争者
            d = self.phi[k] - np.take_along_axis(self.phi, lk[None], 0)[0]
            gd = np.gradient(d, self.dx, edge_order=2)
            gdn = np.sqrt(sum(g ** 2 for g in gd))
            scale = np.maximum(gdn, 1e-30)           # d 不是距离函数（|∇d| ≈ 2）
            nd = [g / scale for g in gd]
            kap = sum(np.gradient(nd[i], self.dx, edge_order=2)[i] for i in range(3))
            edl = np.take_along_axis(ed, lk[None], 0)[0]
            stk = 0.5 * (stiff[k] + np.take_along_axis(stiff, lk[None], 0)[0])
            V = self.M * ((self.df[k] - self.df[lk]) + (ed[k] - edl) - stk * kap)
            iface = (np.abs(d) <= iface_band * self.dx * scale) & (np.abs(V) > 0)
            if np.any(iface) and not iface.all():
                ind = distance_transform_edt(~iface, return_distances=False,
                                             return_indices=True)
                dist = distance_transform_edt(~iface)
                Vext = np.where(dist <= band_cells, V[tuple(ind)], 0.0)
            else:
                band = np.abs(d) <= band_cells * self.dx * scale
                Vext = np.where(band & (np.abs(V) > 0), V, 0.0)
            if not np.any(Vext != 0):
                continue
            if adv_grad in ('proj', 'proj2'):
                # ★ 守卫（D17 记账）：`_advance_perfield` 也必须支持 proj 系列，
                #   否则把 `adv_grad='proj2'` 传进来会**静默退化**成 Godunov 迎风
                #   （那是语义分叉，不是等价）。这条正是 AGENTS §3.24「改一半」的教训。
                #   这里 `Vext` 就是"场 k 自己的法向速度"⇒ 投影成 `V_k·n_k` 再迎风对流。
                gk_ = np.gradient(d, self.dx, edge_order=2)
                gnk_ = np.sqrt(sum(g_ ** 2 for g_ in gk_)) + 1e-30
                Vv = [Vext * (g_ / gnk_) for g_ in gk_]
                self.phi[k] = self.phi[k] - dt * upwind_flux_vec(
                    self.phi[k], Vv, self.dx, order=(2 if adv_grad == 'proj2' else 1))
                vmax = float(np.max(np.abs(Vext)))
                self.dG_max = (vmax / self.M) if self.M else 0.0
                continue
            if adv_grad == 'central':
                g = np.gradient(self.phi[k], self.dx, edge_order=2)
                gmag = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
            else:
                sgn = np.where(Vext > 0, 1.0, -1.0)
                gmag = self._upwind_grad(self.phi[k], sgn)
            self.phi[k] = self.phi[k] - dt * Vext * gmag
            vmax = float(np.max(np.abs(Vext)))
            self.dG_max = (vmax / self.M) if self.M else 0.0

    def suggest_dt(self, cfl=0.15, dt_prev=None, grow_max=2.0):
        """按**实际最大界面速度**定步长：`dt = cfl·dx / max|v|`（`v = M·ΔG`）。
           上一步的驱动力由 `advance` 写在 `self.dG_max`。
           ★ 记账（2026-09-25，M2 的 CFL 真凶）：**必须用总驱动**（Δf + 弹性 − γκ），
             不能只用 Δf。实测 M2 里弹性项比 Δf 大 ~5 倍 ⇒ 只按 Δf 定 dt 会让实际每步
             位移达 0.6–0.75 dx（超 CFL 4–5 倍）⇒ 界面剖面失真、几何测度静默塌缩。
           `grow_max` 限制 dt 相对上一步的放大倍数（速度下降时不让 dt 突跳）。"""
        dmax = getattr(self, 'dG_max', 0.0)
        if not dmax or dmax <= 0 or not self.M:
            return None
        dt = cfl * self.dx / (self.M * dmax)
        if dt_prev is not None:
            dt = min(dt, grow_max * dt_prev)
        return dt
    def _stefan(self, reg0, reg1, k_part=None, dbg=None):
        """③ 本轮修：Stefan 跳跃的**正确去向**——界面扫过时被排出的溶质
           **先存进面过剩 Γ**（即 ∂Γ/∂t 那一项），再由 update_Gamma 的面-体交换与
           面扩散分发出去；**不再直接甩给邻居**（旧写法既非物理、又带 1.6% 不守恒 ✗）。
           收缩时反向：产物胞变母相需要的溶质，**先从面 Γ 取**，不足的部分才由邻居补
           （记账：Γ 不足时从邻居补，仍是精确守恒 ✓）。

        ★★ T4（2026-09-28）：`k_part` 默认改为**取实例属性 `self.k_part`**（B1 = 1.0）。
           `k_part=1.0` ⇒ `ctgt == self.c` ⇒ `dq ≡ 0` ⇒ `amount ≡ 0` ⇒ **c 逐位不变**，
           且 `Gam_mol` 不被写入 ⇒ 这条路径对 B1 是**恒等变换**。
           （旧默认 0.6303 是**液/固**分配系数，被误用到位移型相变上。）"""
        if k_part is None:
            k_part = float(getattr(self, 'k_part', 1.0))
        # ★★ T3（2026-09-28）：`k_part == 1.0` ⇒ `ctgt ≡ self.c` ⇒ `dq ≡ 0` ⇒ `amount ≡ 0`
        #   ⇒ 整段是**恒等变换**；而 `surface_chem=False`（T4 的 B1 默认）时 Γ 通道本就关闭
        #   ⇒ 可以直接返回。旧写法每步仍做 `surface_band()` + `cell_area_geom()`
        #   （实测占单步 **14%**，`_prof_step.py`），纯属空算。
        #   ⚠ 等价性前提：Gam/Gam_mol 此前为 0（`surface_chem=False` 期间不会被写），
        #     所以跳过的 `self.Gam = Gam_mol/A_c` 同步也是恒等变换 ✓。
        if k_part == 1.0 and not getattr(self, 'surface_chem', True):
            return
        m = self.surface_band()
        A_c = self.cell_area_geom()
        if not hasattr(self, 'Gam_mol') or self.Gam_mol.shape != A_c.shape:
            self.Gam_mol = self.Gam * A_c          # 惰性初始化（应对 __new__/外部构造）
        if dbg is not None:
            b0, s0 = self.totals()
            dbg['t0'] = b0 + s0
        for kind in ('grow', 'shrink'):
            if kind == 'grow':
                swept = (reg0 == 0) & (reg1 != 0)          # 母相 -> 产物
                ctgt = k_part * self.c
            else:
                swept = (reg0 != 0) & (reg1 == 0)          # 产物 -> 母相
                ctgt = self.c / max(k_part, 1e-6)
            if not swept.any():
                if dbg is not None:
                    b1, s1 = self.totals()
                    dbg['log'].append((dbg['step'], kind + '(空)', (b1 + s1) - dbg['t0'],
                                       int(swept.sum())))
                    dbg['t0'] = b1 + s1
                continue
            dq = (ctgt - self.c)
            self.c[swept] = ctgt[swept]
            amount = -(dq * self.rho * self.dx ** 3)       # 需从系统其余部分拿走的摩尔量
            if dbg is not None:
                b2, s2 = self.totals()
                dbg['log'].append((dbg['step'], kind + ' a)置c后', (b2 + s2) - dbg['t0'], 0))
                dbg['t0'] = b2 + s2
            # (a) 先存/取面 Γ
            # ★★ W-6c：**直接按摩尔存/取**（不再经过 A_c 的除法/乘法，避免测度漂移）
            msk = swept & (A_c > 0)
            if kind == 'grow':
                self.Gam_mol = np.where(msk, self.Gam_mol + amount, self.Gam_mol)
                amount = np.where(msk, 0.0, amount)
            else:
                take = np.where(msk, np.minimum(self.Gam_mol, -amount), 0.0)
                self.Gam_mol = np.where(msk, self.Gam_mol - take, self.Gam_mol)
                amount = amount + take
            # 派生 Gam 保持一致（供读 Gam 的判据/物理使用），并同步 
            #   —— 否则 update_Gamma 的 guard 会误判成"外部写了 Gam"而每步重同步一次。
            self.Gam = np.where(A_c > 0, self.Gam_mol / np.maximum(A_c, 1e-30), 0.0)
            self._Gam_derived = self.Gam.copy()
            if dbg is not None:
                b2, s2 = self.totals()
                dbg['log'].append((dbg['step'], kind + ' b)取面后', (b2 + s2) - dbg['t0'], 0))
                dbg['t0'] = b2 + s2
            # ★ 收口（本轮）：接收者 = **全部 6 个邻居 + 自己 = 7 个** ⇒ 除数恒为 7 ✓。
            #   此前除数用 `wsum = #被扫邻居 + 1`（薄扫层里只有 ~2）⇒ 分出去的总量 = 应有量×7/wsum
            #   ≈ ×3.5 ⇒ 守恒漏（探针实测：体相应取 2.05e-21，却被拿走 7.19e-21 = 3.5 倍 ✓ 完全吻合）。
            # AUDIT-#5 修：原来用 np.roll 分配（**周期边界**）=> 域边界的排出溶质会从
            #   对面边界冒出（非物理）。改成**非周期移位**：只分给"落在域内"的邻居，
            #   越界方向的那份自然留在源胞手上 => 既不跨域、又逐位守恒。
            #   接收者数由**实际**决定（自己 + 域内被扫过的邻居），不再硬编码 7。
            def _shift_np(arr, d):
                out = np.zeros_like(arr)
                src_s = [slice(None)] * 3
                dst_s = [slice(None)] * 3
                for ax in range(3):
                    if d[ax] > 0:
                        src_s[ax], dst_s[ax] = slice(0, -1), slice(1, None)
                    elif d[ax] < 0:
                        src_s[ax], dst_s[ax] = slice(1, None), slice(0, -1)
                out[tuple(dst_s)] = arr[tuple(src_s)]
                return out
            _dirs = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
            nrecv = np.ones(swept.shape)                      # 自己
            for d in _dirs:
                nrecv += _shift_np(swept.astype(float), d)     # 域内且被扫过的邻居
            share = np.where(swept, amount / np.maximum(nrecv, 1.0)
                             / (self.rho * self.dx ** 3), 0.0)
            self.c += share                                   # 自己那份
            for d in _dirs:
                self.c += _shift_np(share, d)                 # 邻居那份（非周期）
            if dbg is not None:
                b2, s2 = self.totals()
                dbg['log'].append((dbg['step'], kind + ' c)分发后', (b2 + s2) - dbg['t0'], 0))
                dbg['t0'] = b2 + s2
            if dbg is not None:
                b1, s1 = self.totals()
                dbg['log'].append((dbg['step'], kind, (b1 + s1) - dbg['t0'], int(swept.sum())))
                dbg['t0'] = b1 + s1

    def reinitialize(self, band_cells=6, mode='pair', force=False):
        """★ EXPERT-#3 修（2026-09-26）：**按界面配对**重初始化（默认 mode='pair'）。

        为什么必须改：多区域的真实界面由  决定，**不是** 。
          旧实现把每个 phi_k 当**独立单相**做 Sussman => 即使各场自己的零等值面各自不动，
           的零等值面仍会移动。
          **实测**（_verify_reinit.py，两变体平面界面）：
            不重初始化      => d=0 在 0.02500 um
            独立 reinit 各 phi_k（旧实现）=> d=0 移到 **-0.21313 um**（跳 0.238um ≈ **4.8 个胞**！）
            对差分场 reinit  => 0.02500 um（正确）
          => 每 25 步一次的 reinit 会**反复打乱变体-变体界面**，很可能就是"等轴化"的真主因。

        做法（对每个活跃配对 (k,l), k<l）：
          1. d = phi_k - phi_l，只在 |d| <= band 的带内
          2. d_new = sussman_reinit(d)  => SDF 且**零等值面不动**
          3. **对称回写**：phi_k += 0.5*(d_new-d)，phi_l -= 0.5*(d_new-d)
             => d_kl == d_new（界面保持），且 phi_k+phi_l 不变（不引入整体漂移）
        记账：
          * 多配对叠加处（三叉线）各配对各自贡献 => 近似处理，见文档。
          * mode='perfield' 保留旧行为，仅供对照/回归。
        """
        if mode != 'pair':
            reg = self.region()
            for k in range(self.nreg):
                near = np.abs(self.phi[k]) <= band_cells * self.dx
                if not near.any():
                    continue
                newp = self.sussman_reinit(self.phi[k])
                self.phi[k] = np.where(near, newp, self.phi[k])
            return
        # ★ R1（2026-09-29）：**只为记账**的墙钟计时（不改变任何数值/分支）。
        import time as _tm
        _tw0 = _tm.perf_counter()
        self._reinit_wall_last = 0.0
        self._reinit_pairs_last = 0
        reg = self.region()
        self._reinit_band_before = self._band_bonds(reg)
        # 活跃配对：区域数少时可全对；否则用 region 的邻居关系先筛
        pairs = set()
        for ax in range(3):
            a = reg
            b = np.roll(reg, -1, axis=ax)
            sel = a != b
            if sel.any():
                for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                    if x != y:
                        pairs.add((int(min(x, y)), int(max(x, y))))
        if not pairs:
            self._reinit_all_skipped_last = True
            self._reinit_band_after = self._reinit_band_before
            return
        # ★ 关键：**逐胞只用它自己的界面配对**（karr,larr），否则多配对（含母相）的
        #   修正会互相叠加、把界面推错（实测：叠加时界面跑到 -0.047um，逐胞后回到解析值附近）。
        #
        # ★★★ R1 任务①（2026-09-29，**子代理 `_r1_reinit_when.py` 实测驱动**）：
        #   **懒构造**（lazy）。原来这里**无条件**先做
        #       `np.argsort(self.phi, axis=0)`  ← 造一个 (nreg,N³) int64 临时量
        #       `delta = np.zeros_like(self.phi)` ← 再造一个 (nreg,N³) float64
        #   **在逐对跳过判据（`reinit_skip_tol`）之前**。
        #   而生产触发口径下实测：**8 个配对全部被跳过、100 次 Sussman 一次都没跑**
        #     （`_r1_reinit_when.py`：doneΔ=0 / skipΔ=8，6 次触发，每次只多花 0.47 s）。
        #   ⇒ 全跳过时这两笔开销**白付**，且它们**一次都没被用到**
        #     （`_karr/_larr` 只在 `is_kl` 掩模里用；`delta` 只在有配对被处理时累加）。
        #   实测量级（N=96）：`argsort(13 场)` = **0.177 s**、`region()` = 0.042 s；
        #     按 N³ 折算到 N=192 约 **1.4–1.8 s/次触发**；内存上 N=192 的 argsort
        #     临时量是 **13×7.08e6×8 B = 736 MB**（int64），`delta` 又是 736 MB。
        #   改法：把这两样**推迟到第一次真正要做 reinit 时**再建。
        #   ⚠ **逐位不变**（证明）：跳过分支里这两个量**没有被读过**；
        #     若一个配对都没做，`delta` 恒为 0 ⇒ 原来的 `self.phi = self.phi + 0.0`
        #     对有限值**逐位不变** ⇒ 直接 return 等价。
        #   ⚠ 同时删掉原来的 `_karr = np.argmin(self.phi, axis=0)` —— 它是**死代码**
        #     （下一行立刻被 `_order[0]` 覆盖）。
        _karr = _larr = delta = None
        _did_any = 0
        self._reinit_all_skipped_last = False
        for (k, l) in pairs:
            # ★★ T2 修（P0-3，2026-09-28）：对**半差分** d2 = (φ_k−φ_l)/2 做重初始化，
            #   目标 |∇d2| = 1  ⟺  |∇d| = 2  ⟺  |∇φ_k| = |∇φ_l| = 1（VDF 的正确 SDF 条件）。
            #   旧写法对 **d 本身**做 Sussman、目标 |∇d| = 1 ⇒ 把 |∇φ_k| 推向 **0.5**
            #   并继续塌陷。实测（`_audit_faces2.py`，单因素：reinit 0 vs 25）：
            #     reinit=0  : 带内 median|∇φ| 0.81–0.96，带胞 7824
            #     reinit=25 : 带内 median|∇φ| **0.867 → 0.157**，带胞 **20871**（膨胀 2.7×）
            #   ⇒ 这不是"轻微不守恒"，而是**把界面带撑大、把几何测度静默改掉**。
            #   为什么 d2 是对的：VDF 里 ∇φ_k = +n、∇φ_l = −n（界面法向）
            #     ⇒ ∇d = 2n、|∇d| = 2，而 d2 = d/2 满足 |∇d2| = 1 —— 正是 Sussman 的不动点。
            d2 = 0.5 * (self.phi[k] - self.phi[l])
            near = np.abs(d2) <= band_cells * self.dx
            if not near.any():
                continue
            # ★★★ R1 任务①（2026-09-29）：**只在该配对界面的包围盒里做 Sussman**。
            #   为什么可以（论证见模块级 `_band_bbox`）：Sussman 的迎风依赖锥
            #     **指向零等值面内部**，而回写掩模本来就是 `|d2| ≤ band·dx`
            #     ⇒ 带外的迭代结果**根本不被使用**，算了也是白算。
            #   ⚠ 这条是**纯结构性**加速：全域与子盒的结果对带内胞**逐位相同**
            #     （由 `_r1_reinit_bbox.py` 的逐位判据把关）。
            #   ⚠ `reinit_bbox` 是**敏感度旋钮**：False ⇒ 退回旧的全域行为（对照用）。
            #   ★★★ **实测否决（R1，2026-09-29）**：`_r1_reinit_bbox.py` 的端到端逐位守卫
            #     **B-1 FAIL** —— 真实状态（N=48、4 核、6 步）上子盒与全域 `phi` 的
            #     最大绝对差 **3.446e-07 m**（而 B-2 正对照 margin=1 给出**同一个数**
            #     3.446e-07 ⇒ 子盒路径等价于"margin=1"，**不是**等价于全域）。
            #   我原来的论证**错在哪**：我只算了"特征线 1 胞/迭代"，
            #     但 `upwind_grad2` 的**数值依赖锥是每迭代 ±2 胞**
            #     （`Dm2[i]` 用到 `phi[i−2..i+1]`；`Dp2` 用到 `phi[i+2]`）
            #     ⇒ `iters=100` 时依赖半径 ≈ **200 胞**，任何实用余量都不够。
            #   ⇒ **`reinit_bbox` 默认改为 `False`（关闭）**；代码保留，供"已知近似模式"使用。
            #     （与 `AGENTS §3.16`「传承结论也要能算数才算数」同类：**实测否决推理**。）
            _bbox = None
            if getattr(self, 'reinit_bbox', False):
                _mg = getattr(self, 'reinit_bbox_margin', None)
                if _mg is None:
                    import math as _m
                    _mg = 2 + 2 * int(self.reinit_iters) + 1
                _bbox = _band_bbox(d2, band_cells, self.dx, _mg)
                if _bbox is not None:
                    self._reinit_bbox_used = getattr(self, '_reinit_bbox_used', 0) + 1
                    _vol = 1
                    for _s in _bbox:
                        _vol *= (_s.stop - _s.start)
                    self._reinit_bbox_frac = _vol / float(self.phi[0].size)
            # EXPERT-#3c 记账：本路径的正确性依赖"窄带 + 输入近似 SDF"。
            #   Sussman 的不动点是 |grad| = 1 的场；若带内 |grad d2| 明显偏离 1，
            #   迭代会把斜率推向 1 并**同时移动零等值面**（不是 bug，是必然）。
            #   这里加**运行期告警**，避免将来在别处误用这条路径。
            _gd = np.gradient(d2, self.dx, edge_order=2)
            _gdn = np.sqrt(sum(_gi ** 2 for _gi in _gd))
            _med = float(np.median(_gdn[near]))
            # ★★★ A2（2026-09-28）：**"已经够 SDF 就不要动它"**。
            #   依据（`T23_verify_reinit.py` 实测）：Sussman 的不动点是 `|∇d2| = 1` 的场；
            #   输入偏离 1 时，迭代在把斜率推向 1 的**同时**会把**零等值面平移** ——
            #   实测**每次 reinit 移动零等值面最多 0.054 胞**（`Δmedian(φ_karr)/Δx`），
            #   且**不幂等**（第 4/5 次 `ΔV/V` 非零）。
            #   ⇒ 若带内 `|∇d2|` 中位已经在 1±`reinit_skip_tol` 内，**reinit 只会带来害处**
            #     （位移）而几乎没有好处（场已经是 SDF）⇒ 直接跳过。
            #   ★ 这同时省机时：`reinit_iters=100` 的 Sussman 已是单步相对瓶颈（T12 记账）。
            _skip_tol = float(getattr(self, 'reinit_skip_tol', 0.05))
            self._reinit_last_med = _med
            # ★★★ W1-3（2026-09-28）：`force=True` ⇒ **跳过容差不生效**（`C4` 的修法之一）。
            #   为什么需要：`seed_plate` 的 `phi[j]=max(phi[j],−sdf)` 会在新核盘边界造出
            #   O(|旧 φ_j|) 的**跳变**，而兜底是定时 reinit。若那一刻恰被判据跳过，
            #   跳变就会一路带到后续推进里（`region()` 仍正确 ⇒ **不报错**）。
            #   ⇒ 种核之后**强制**做一次 reinit，不看跳过容差。
            if (not force) and abs(_med - 1.0) <= _skip_tol:
                self._reinit_skipped = getattr(self, '_reinit_skipped', 0) + 1
                continue
            self._reinit_done = getattr(self, '_reinit_done', 0) + 1
            self._reinit_pairs_last = self._reinit_pairs_last + 1
            import time as _tm2
            _tp0 = _tm2.perf_counter()
            # ★ R1：**懒构造**（见上面 `_karr = _larr = delta = None` 的记账）。
            #   到这一步才确定"确实有配对被处理" ⇒ 现在才付 `argsort`/`delta` 的钱。
            if delta is None:
                _order = np.argsort(self.phi, axis=0)
                _karr, _larr = _order[0], _order[1]
                del _order
                delta = np.zeros_like(self.phi)
            if abs(_med - 1.0) > 0.5:
                import warnings as _w
                _w.warn('pair reinit: band |grad(d/2)| median=%.3f 明显偏离 1; '
                       'Sussman will move the zero-level set (input not SDF).'
                       % _med, RuntimeWarning, stacklevel=2)
            dn = self.sussman_reinit(d2, bbox=_bbox)
            self._reinit_wall_last = getattr(self, '_reinit_wall_last', 0.0) + (
                _tm2.perf_counter() - _tp0)
            corr2 = np.where(near, dn - d2, 0.0)      # 对 **d2** 的修正量
            # 该胞的界面身份必须是 (k,l)（无序）
            is_kl = ((_karr == k) & (_larr == l)) | ((_karr == l) & (_larr == k))
            corr2 = np.where(is_kl, corr2, 0.0)
            # 回写：φ_k += c、φ_l −= c  ⇒  d_new = d + 2c = 2·d2_new ✓，
            #       且 φ_k+φ_l 逐位不变（不引入整体漂移）✓
            delta[k] += corr2
            delta[l] -= corr2
            _did_any += 1
        if _did_any == 0:
            # ★ R1 记账：**一个配对都没做** ⇒ `delta` 恒为 0（甚至没被构造）
            #   ⇒ 原来的 `self.phi = self.phi + 0` 对有限值**逐位不变** ⇒ 直接返回等价。
            #   （`_band_bonds` 也不重算了：`region()` 未变 ⇒ 键数不变。）
            self._reinit_all_skipped_last = True
            self._reinit_reg_flips_last = 0
            self._reinit_band_after = self._reinit_band_before
            self._reinit_wall_total = getattr(self, '_reinit_wall_total', 0.0) + (
                _tm.perf_counter() - _tw0)
            return
        self.phi = self.phi + delta
        # ★★★ A2（2026-09-28）**硬守卫：区域指派必须逐个胞保持不变**。
        #   为什么用这个判据：多区域 VDF 里"几何"的**定义**就是 `argmin_k φ_k`
        #   ⇒ "零等值面不动"的**精确、离散、可逐位核对**的表述就是 `region()` 不变。
        #   （T23 首版用 `ΔV/V` 与 `Δmedian(φ_karr)` 都是**间接**量：前者受整数计数限制、
        #     后者是统计量，两者都会漏掉少量翻转的胞。）
        #   做法：把发生翻转的那些胞的修正量**原样退回** ⇒ `region()` **由构造保证**不变，
        #   其余胞照常享受 SDF 重整。退回造成的不连续被修正量本身（~0.1 Δx）界定。
        if getattr(self, 'reinit_guard_region', True):
            _reg_new = self.region()
            _flip = (_reg_new != reg)
            _nf = int(_flip.sum())
            self._reinit_reg_flips = getattr(self, '_reinit_reg_flips', 0) + _nf
            self._reinit_reg_flips_last = _nf
            if _nf:
                self.phi = self.phi - np.where(_flip[None], delta, 0.0)
        # ---- 修后健康度检查（判据可升级为硬失败，供 T2 判据脚本使用）----
        _n1 = self._band_bonds(self.region())
        self._reinit_band_after = _n1
        if getattr(self, 'reinit_strict', False) and self._reinit_band_before > 0:
            _ratio = _n1 / float(self._reinit_band_before)
            if _ratio > 1.2:
                raise RuntimeError(
                    'pair reinit 后界面带胞数膨胀 %.3f× (%d -> %d)：'
                    '重初始化把界面带撑大了，几何测度已不可信（P0-3 的指纹）。'
                    % (_ratio, self._reinit_band_before, _n1))
        self._reinit_wall_total = getattr(self, '_reinit_wall_total', 0.0) + (
            _tm.perf_counter() - _tw0)

    @staticmethod
    def _band_bonds(reg):
        """界面"键"总数（6 邻域逐轴跨界计数）—— 带健康度的**离散测度**。
        用途：P0-3 的判据"reinit 不得把界面带撑大 > 1.2×"。"""
        n = 0
        for ax in range(3):
            n += int((reg != np.roll(reg, -1, axis=ax)).sum())
        return n


def M1_multiregion_conservation(N=48, nstep=20):
    """多区域静态守恒：v_n=0（df=0、γ=0）时各区域体积应逐位不变"""
    g = LevelSetMulti(N, N * 1e-9, gamma=0.0, Mob=1.0, nv=2)
    g.seed_sphere(1, [0.4 * N * 1e-9] * 3, 8e-9)
    g.seed_sphere(2, [0.65 * N * 1e-9] * 3, 6e-9)
    v0 = [g.volume(k) for k in range(g.nreg)]
    for _ in range(nstep):
        g.advance(1e-12)
    v1 = [g.volume(k) for k in range(g.nreg)]
    drift = max(abs(a - b) / max(abs(a), 1e-30) for a, b in zip(v0, v1))
    print('---- M1 多区域静态守恒 ----')
    print('   体积漂移（最大相对）= %.2e   %s' % (drift, 'PASS' if drift < 1e-6 else 'FAIL'))
    return drift < 1e-6


class M2Out(object):
    """M2 的返回值：既支持 out['f_trans']（新代码），也把未知属性代理给内部 g
       （旧代码  后用 g.volume(...) 的那批脚本）。
       ★ 记账：加这个包装是为了"返回值从 g 改成 dict"这一步不破坏既有调用者。
    """

    def __init__(self, g, d):
        object.__setattr__(self, '_g', g)
        object.__setattr__(self, '_d', d)

    def __getitem__(self, k):
        return self._d[k]

    def get(self, k, default=None):
        return self._d.get(k, default)

    def keys(self):
        return self._d.keys()

    def __contains__(self, k):
        return k in self._d

    def __getattr__(self, k):
        return getattr(object.__getattribute__(self, '_g'), k)

    def __setattr__(self, k, v):
        setattr(object.__getattribute__(self, '_g'), k, v)


def M2_twelve_variants(N=64, dx=1e-8, nstep=300, df=1e8, gamma=0.15, aniso=0.4,
                       Mob=1e-9, rfrac=0.22, adv_grad='upwind',
                       pair_kernel=False, iface_band=2.0, probe=0, cfl=0.15,
                       plate_dx=2.0, per_field=False, aniso_elastic=False, quiet=False,
                       t_end=None, surface_chem=True,
                       C_override=None):
    # t_end：给定**总物理时间**时，按累计时间跑（而不是固定步数）。★ 记账：
    #   界面每步位移被 CFL 钉在 ~0.15dx，而 dt ∝ 1/dG_max ⇒ **同一 nstep ≠ 同一时刻**；
    #   比较不同驱动下的分数必须在**同一 t**（否则低驱动因 dt 更大而虚假领先）。
    """12 变体 RVE（level-set 表示）：看是否（i）不冻结晶核、（ii）给出板条形状。

       ★★ 符号约定（2026-09-25 由判据 T2.1b-7 判决，_chk_t21b7.py）：
          df > 0 = **变体有利**（会长大）；df < 0 = 变体不利（会缩小）。
          验证（nv=1 的 slab）：df=+1e8 => dV1=+18432、v/(M|df|)=+0.9989；
                            df=-1e8 => dV1=-18432、v/(M|df|)=-1.0000。
          这与 PF3D 的 dF/dphi_v = -dG（梯度下降 => dG>0 才长大）一致。
          ⚠ **默认值 2026-09-25 从 -1e8 改成 +1e8**：改前所有 M2 运行
          （含 §6.7 与审计引用的「转变分数 14.5%」）其实是在**溶解**晶核，
          报出的分数是**弹性自协调**撑起来的（T2.1b 开工时用单步增量发现，
          见 WINDOWB_SURFACE_AUDIT §11）。**改前的 f_trans 数值一律作废**。
       与格点 KMC 版（windowB_gibbs）对照：那里 Λ≳5 时转变被冻在 5–23% ✗。

       ★★ 记账（2026-09-25 两个真修正，缺一都会让 M2 的几何量彻底失真）：
       1) **`dt` 必须按总驱动自适应**（`suggest_dt`）：弹性项在界面带上中位 4.9e8，
          是 Δf(1e8) 的 ~5 倍 ⇒ 只用 Δf 估 dt 会让**实际每步位移达 0.6–0.75 dx**
          （超 CFL 4–5 倍）。实测修前 25 步内带胞 12601→35、|∇φ_winner| 0.73→6e5；
          修后同样 25 步带胞 9567→**9671**、|∇φ_winner| 稳定在 0.48–0.62、12 个变体
          **全部存活**，几何首次给出合理数字（长:短 3.9–5.2、与相容法向夹角中位 20.7°）。
          ⇒ §9.4/§9.5 的"M2 塌缩/配对一致性被破坏"全部是**这一步的超 CFL 症状**。
       2) **`Λ` 默认 10 → 0.4**：`γ(θ)=γ0(1+Λ sin²θ)` 的 Herring 稳定性要求
          `γ+γ_θθ = γ0(1+2Λ−3Λ sin²θ) > 0`，最坏在 `sin²θ=1` ⇒ **Λ < 1**。
          Λ=10 时实测该量跨 **[−1.35, +3.15]（含负）⇒ 非凸/不适定**（界面会被"起皱"
          驱动）。0.4 与 W1 的正对照同一个值（W1 已验证），且落在 Ti64 晶界能各向异性
          的常见范围（~0.2–0.4）。"""
    _p = (lambda *a, **k: None) if quiet else print
    from windowB_pf3d import C_iso3, C_cubic, _lam_full
    from windowB_ti64_variants import variants
    # ★★ 记账（2026-09-25）：均匀模量近似的**参考模量**由"各向同性等效"改成**母相 β(bcc) 立方**
    #   —— β-Ti 的 Zener 各向异性 A = 2C44/(C11−C12) = 2·36/(134−110) = **3.0**，是强各向异性，
    #   用各向同性等效会丢掉弹性相互作用的**方向性**（而 M2 的板条取向正是靠它）。
    #   张量本身已过 `_chk_hex.py` HX-7（立方不变性机器精度）；常数 ★【文献值待核对】。
    #   ⚠ 仍未做：逐变体模量（12 个转动 hcp 张量已建好并验证 = HX-6，但 FFT 谱法要求均匀 C
    #   ⇒ 要做 inhomogeneous 需换参考介质 + 极化迭代；见审计 §10.9）。
    # ★ C_override：隔离实验用（C_override=None 表示**关掉弹性**，只留化学驱动）。
    #   用途：把「界面/化学」与「弹性相互作用」分开（见 _t21b_noel.py 的记账）。
    #   C_override=None -> 默认（bcc β-Ti 立方）；'off' -> **关掉弹性**（C=None）；
    #   否则当作显式张量。
    _no_el = (C_override == 'off')
    if C_override is None or _no_el:
        C = C_cubic(134.0e9, 110.0e9, 36.0e9)    # bcc β-Ti ★文献值待核对
    else:
        C = C_override
    #   C 仍用于算 npref（晶核取向，几何量）；弹性求解器是否建由 C_use 决定。
    C_use = None if _no_el else C
    eps0, Fs, meta = variants()
    nv = len(eps0)
    g = LevelSetMulti(N, N * dx, C=C_use, eps0=eps0, gamma=gamma, Mob=Mob,
                      df=[0.0] + [df] * nv, workers=6, reinit_every=25,
                      aniso_elastic=aniso_elastic)
    # 各变体的弹性最省能法向（= 晶核取向）
    # ★ Round 141：改用**收敛的** `argmin_normal`（原 400 点随机抽样未收敛，
    #   `E(400点)/E_min` 中位 234、夹角中位 82° —— 见 `_chk_lam_batch.py`）。
    npref = {}
    for v in range(nv):
        npref[v + 1] = _argmin_normal(C, np.asarray(eps0[v], float))[0]
    R = rfrac * N * dx
    t = plate_dx * dx
    for v in range(nv):
        g.seed_plate(v + 1, (rng.random(3) * (N * dx - 2 * R) + R), npref[v + 1], R, t)
    g.init_parent()
    v0 = np.array([g.volume(k) for k in range(g.nreg)])
    _p('   [诊断] 初始各区域体积分数 = %s' % np.round(v0 / v0.sum(), 4))
    _p('   [诊断] phi 的最小值: 母相 %.3e ; 变体1 %.3e ; 空变体13 %.3e'
          % (g.phi[0].min(), g.phi[1].min(), g.phi[g.nreg - 1].min()))
    v = Mob * abs(df) * 0.5                    # 前沿速度估计
    # ★★ 记账（本轮修的真 bug）：前沿速度是 **M·|Δf|**，不是 0.5 倍。旧写法
    #   `v = M|Δf|·0.5` 配 `dt = 0.3dx/v` ⇒ 实际每步位移是 **0.6 dx**（不是 0.3）。
    #   后果（实测，隔离实验见审计 §10.2）：一阶迎风在 0.6dx/步下失真、6dx 厚的
    #   板片 10 步被吃光、`band_health` 静默塌缩（带胞 12601→35、|∇φ_winner| 中位
    #   0.73→6.0e5）；把每步位移降到 0.10–0.15dx 后同一算例 25 步内带胞只降到 ~1900、
    #   |∇φ| 中位 ~4.9（仍退化，但量级完全不同 ⇒ dt 是**主导因素**）。
    #   ⇒ 改用**显式 CFL**：`dt = cfl·dx/(M|Δf|)`。
    v = Mob * abs(df)
    dt = cfl * dx / v
    _p('---- M2 12 变体 RVE（level-set）----')
    _p('   N=%d dx=%.1f nm 域=%.2f um | df=%.1e γ=%.2f Λ=%.1f | v=M|df|=%.3f m/s '
          'dt0=%.2e ⇒ 初值每步位移 %.3f dx（之后按**总驱动**自适应）'
          % (N, dx * 1e9, N * dx * 1e6, df, gamma, aniso, v, dt, dt * v / dx))
    _p('   %6s %9s %9s %9s %9s %10s' %
          ('step', 'f_trans', 'V_max/V', 'min(V)>0', 'dt*(M|dG|mx)/dx', '带胞'))
    _nstop = nstep if t_end is None else 1000000
    _tacc = 0.0
    for k in range(_nstop + 1):
        _done = (k == nstep) if t_end is None else (_tacc >= t_end)
        if k % 60 == 0 or _done:
            vt = np.array([g.volume(j) for j in range(g.nreg)])
            f = 1.0 - vt[0] / (N * dx) ** 3
            nb, medg, okg = g.band_health()
            _p('   %6d %9.4f %9.4f %9s %12.3f %10d'
                  % (k, f, vt.max() / v0.sum(), str(bool((vt[1:] > 0).all())),
                     dt * (g.M * getattr(g, 'dG_max', 0.0)) / dx, nb))
        if _done:
            break
        g.advance(dt, aniso=aniso, npref=npref, adv_grad=adv_grad,
                  pair_kernel=pair_kernel, iface_band=iface_band,
                  per_field=per_field)
        # ★★ W-6 修（2026-09-25）：**必须每步调 update_Gamma** —— 否则被 Stefan 扫出的
        #   溶质全部滞留在面 Gamma 里（既不弛豫到 McLean、也不由面扩散/回吐分发），
        #   且界面移走后离带胞的 Gamma 会脱离账本（实测 rel 约 5e-6/步）。
        #   关掉它只在做'纯平流/纯面储存'的隔离实验时才有意义。
        if surface_chem:
            g.update_Gamma(dt)
        # ★ 自适应 dt：按**实际总驱动**（含弹性）定 CFL，见 `suggest_dt` 的记账
        _tacc += dt
        ndt = g.suggest_dt(cfl=cfl, dt_prev=dt)
        if ndt:
            dt = ndt
        if probe and (k + 1) % probe == 0:
            nb, medg, okg = g.band_health()
            _p('   [带健康 probe step=%4d] 带胞=%6d 带内|∇φ_win|中位=%8.3f %s'
                  % (k + 1, nb, medg, 'OK' if okg else '**退化**'))
    reg = g.region()
    vt = np.array([g.volume(j) for j in range(g.nreg)])
    # ★ P1 修复后必须用**几何（coarea）界面面积测度**：`g.area(k)` 是"异键数×dx²"的
    #   格点测度，对球实测 **+51.9%** ✗（见 WINDOWB_SURFACE_AUDIT §2 的 A1）。
    #   `area_total_geom()` 对球 +0.3% ✓ ⇒ S_v、t=2f/S_v 才可信。
    sv_geom = g.area_total_geom() / (N * dx) ** 3
    sv_latt = sum(g.area(j) for j in range(1, g.nreg)) / (N * dx) ** 3
    nb, medg, okg = g.band_health()
    if not okg:
        _p('   ⚠⚠ 界面带已退化（带胞 %d、带内 |∇φ| 中位 %.2f）⇒ **下面的 S_v / 板条厚度'
              '不得引用**：多畴速度扩展/带掩模仍有问题（见审计 §9.5/§10）' % (nb, medg))
    _p('   末态: 转变分数 %.4f ; 各变体体积分数 %s' %
          (1 - vt[0] / (N * dx) ** 3, np.round(vt[1:] / vt[1:].sum(), 3)))
    f_t = 1 - vt[0] / (N * dx) ** 3
    _p('   S_v(几何 coarea) = %.3e 1/m ⇒ 板片厚 t = 2f/S_v = %.1f nm ; '
          '（格点键测度 S_v = %.3e ⇒ t = %.1f nm，仅作对照）'
          % (sv_geom, 2 * f_t / max(sv_geom, 1e-30) * 1e9,
             sv_latt, 2 * f_t / max(sv_latt, 1e-30) * 1e9))
    if not quiet:
        geom_stats(g)
    out = dict(f_trans=float(f_t), v_frac=(vt / vt.sum()).tolist(),
               v_abs=vt.tolist(), S_v_geom=float(sv_geom),
               band=nb, band_ok=bool(okg), g=g, k_used=k, t_total=_tacc,
               dt_last=dt)
    return M2Out(g, out)


if __name__ == '__main__' and False:
    pass


# ============================================================ W1：各向异性 Wulff 形状（① 的判据）
def _wulff_polar(Lam, n=1441):
    """γ(θ)=γ0(1+Λ sin²θ)（θ = 法向与 x̂ 的夹角）的 **Wulff 形状极坐标表示**。
       Wulff 形状 = 半平面族 {x·n ≤ γ(n)} 的交 ⇒ **支撑函数 h(n) = γ(n)**，
       边界由包络 x(θ) = γ(θ)n(θ) + γ'(θ)t(θ) 给出（该点外法向恰为 n(θ)）。
       返回 (ψ, ρ/γ0)：ψ = 位置角，ρ = 到中心的距离。
       ★ 记账（一条会误判的坑）：**不要**拿 "R ∝ γ+γ_θθ" 去比**极径** ——
           γ+γ_θθ 是**曲率半径** 1/κ（Wulff 形状满足 (γ+γ_θθ)κ = 1），
           不是极径；两者只在各向同性时相同。Λ=0.4 下二者差 ~12% ⇒ 用错公式必误判。"""
    th = np.linspace(-np.pi, np.pi, n)
    g = 1.0 + Lam * np.sin(th) ** 2
    gp = Lam * np.sin(2.0 * th)
    x = g * np.cos(th) - gp * np.sin(th)
    y = g * np.sin(th) + gp * np.cos(th)
    psi = np.unwrap(np.arctan2(y, x))
    rho = np.hypot(x, y)
    o = np.argsort(psi)
    return psi[o], rho[o]


def _bin_polar(psi, rho, nbin):
    edges = np.linspace(-np.pi, np.pi, nbin + 1)
    ctr = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(psi, edges) - 1, 0, nbin - 1)
    out = np.full(nbin, np.nan)
    for b in range(nbin):
        s = (idx == b)
        if s.sum():
            out[b] = rho[s].mean()
    return ctr, out


def _shape_metrics(pts2, nrm2, ctr2, Lam, npref2, nbin=36):
    """把 2D 横截面上的界面点折算成 W1 的四条量：
         (a) **支撑函数**判据 h ≡ (x−x_c)·n 必须 ∝ γ(n)  ⇒ 比值 h/γ 的离散度
         (b) 归一化极径 ρ(ψ) 与**精确 Wulff 极径**的最大偏差（按各向异性幅度归一）
         (c) 长径比 = ρ_max/ρ_min，以及 ρ_max 的位置角（Herring 结果应沿 ŷ 拉长）
         (d) 界面点数（量测可靠性的门槛）"""
    d = pts2 - ctr2[None, :]
    rho = np.linalg.norm(d, axis=1)
    psi = np.arctan2(d[:, 1], d[:, 0])
    ctr, rb = _bin_polar(psi, rho, nbin)
    ok = ~np.isnan(rb)
    rn = rb[ok] / rb[ok].mean()
    nd = nrm2 @ (np.asarray(npref2, float) / np.linalg.norm(npref2))
    # ★ 记账（本轮修的一个判据 bug）：γ(θ)=γ0(1+Λ sin²θ)，θ = 法向与 x̂ 的夹角
    #   ⇒ γ = 1 + Λ(1 − (n·x̂)²)。写成 `1 + Λ(n·x̂)²` 会让 γ 的各向异性**反相**
    #   （实测：h/γ 离散度从 0.33 一路涨到 0.66，看起来像"越弛豫越不像 Wulff" ✗）。
    gam = 1.0 + Lam * (1.0 - nd ** 2)
    h = np.einsum('ij,ij->i', d, nrm2)
    ratio = (h / gam)
    ratio = ratio[np.isfinite(ratio) & (gam > 0)]
    spread = float((ratio.max() - ratio.min()) / abs(ratio.mean())) if len(ratio) else np.nan
    # ★ 稳健口径：极差(h_spread)对个别离群点极敏感；判据用 **RMS 相对偏差**
    h_rms = float(np.std(ratio) / abs(np.mean(ratio))) if len(ratio) else np.nan
    pth, prho = _wulff_polar(Lam)
    pr = np.interp(ctr[ok], pth, prho)
    pr = pr / pr.mean()
    dev = float(np.max(np.abs(rn - pr)) / (pr.max() - pr.min()))
    # ★ 无偏形状量：傅里叶拟合 r(ψ)=a0+a2cos2ψ+b2sin2ψ+a4cos4ψ+b4sin4ψ
    #   记账：**不要**用分箱极径的 max/min 当长径比 —— 极值附近的分箱平均会把 max 压低、
    #   min 抬高（各 ~1.5%），实测把 Λ=0.4 的长径比从 1.40 系统性拉到 1.356（-11% 幅度）✗。
    #   傅里叶系数对同样的形状给出无偏估计，且**理论值用同一套拟合**得到 ⇒ 可比。
    ps, rs = _bin_polar(psi, rho, 720)
    o2 = ~np.isnan(rs)
    A = np.stack([np.ones(o2.sum()), np.cos(2 * ps[o2]), np.sin(2 * ps[o2]),
                  np.cos(4 * ps[o2]), np.sin(4 * ps[o2])], -1)
    coef, *_ = np.linalg.lstsq(A, rs[o2], rcond=None)
    tA = np.stack([np.ones_like(pth), np.cos(2 * pth), np.sin(2 * pth),
                   np.cos(4 * pth), np.sin(4 * pth)], -1)
    tcoef, *_ = np.linalg.lstsq(tA, prho, rcond=None)   # 比值 a2/a0 与整体标度无关
    f_m = np.array([coef[0], np.hypot(coef[1], coef[2]), np.hypot(coef[3], coef[4])])
    f_t = np.array([tcoef[0], np.hypot(tcoef[1], tcoef[2]), np.hypot(tcoef[3], tcoef[4])])
    an2 = f_m[1] / f_m[0]
    an2_th = f_t[1] / f_t[0]
    an4 = f_m[2] / f_m[0]
    an4_th = f_t[2] / f_t[0]
    asp_fit = float((f_m[0] + f_m[1] + f_m[2]) / (f_m[0] - f_m[1] + f_m[2]))
    asp_fit_th = float((f_t[0] + f_t[1] + f_t[2]) / (f_t[0] - f_t[1] + f_t[2]))
    return dict(n=len(pts2), aspect=float(rb[ok].max() / rb[ok].min()),
                psi_max=float(ctr[ok][int(np.argmax(rb[ok]))]),
                R_eq=float(rho.mean()), h_spread=spread, dev=dev,
                h_rms=h_rms,
                ctr=ctr[ok], rn=rn, pr=pr, psi=psi, rho=rho, ratio=ratio,
                a2=float(an2), a2_th=float(an2_th), a4=float(an4),
                a4_th=float(an4_th), asp_fit=asp_fit, asp_fit_th=asp_fit_th,
                cos2=float(coef[1]),
                psi_axis=float(0.5 * np.degrees(np.arctan2(coef[2], coef[1]))))


def W1_wulff(N=64, dx=2e-9, R0=1.2e-8, Lam=0.4, nstep=600, herring=True,
             nbin=36, nz=4, tag='', plot=None, M=1e-9, gamma=0.15,
             adv_grad='central', dtfac=0.05, reinit_every=20, verbose=None,
             mode='shape'):
    """① 的解析正对照：**各向异性 Wulff 形状**（Gibbs–Thomson 的 Herring 项）。

    几何：沿 z 的柱体（`ndim=2` 薄板，z 向平移不变 ⇒ 与真 2D 逐位等价），n_pref = x̂。
    演化：**定容弛豫** —— v_n = M[df − γ_eff(n)κ]（df=0 走纯各向异性曲率流），每步再用
          `project_volume` 把体积钉回初值 ⇒ 「面积守恒的各向异性平均曲率流」，
          其唯一稳定平衡态 = Wulff 形状 ✓（等价于用户要的 `df = γ⟨κ⟩_A` 定容，见
          `project_volume` 的记账）。
    判据（全部用**无偏**量；量测口径见 `_shape_metrics`）：
      (a) **傅里叶 2 次模** a2/a0（长径比的线性测度）与理论差 < 15%；
      (b) 拉长方向 = ±ŷ（理论：γ 在 n=ŷ 最大 ⇒ Wulff 沿 ŷ 拉长），误差 < 25°；
      (c) **支撑函数** h=(x−x_c)·n 与 γ(n) 成正比 ⇒ h/γ 离散度 < 10%；
      (d) 数值底噪由 Λ=0 对照给出（应 a2≈0、长径比≈1.00）。
    反向对照：herring=False（拿 γ 当刚度）必须 **FAIL** —— 其实测长径比只有 ~1.10、
    拉长轴转到 **x̂**（与 Herring 结果正交互补），h/γ 离散 ~43% ✗。

    ★ 记账（本轮修掉的三个 harness/数值错误）：
      1) **旧的"定容"是坏的**：用两点标定 + 积分控制，标定步本身用 `df=1e8`、`dt=1.33e-8 s`
         ⇒ 两步内把 R 从 10 nm 吹到 ~58 nm（标定毁掉了初始形状）✗ ⇒ 判据必失败。
         现在用**投影式定容**：无标定、无反馈增益、无临界核不稳定性 ✓。
      2) **量测偏置**：用 36 个角度分箱取极径极值当长径比，会在极值附近把 max 压低、
         min 抬高，实测把 Λ=0.4 的长径比从 1.40 拉到 1.356（−11% 幅度）✗
         ⇒ 改用**傅里叶拟合**（与理论同一套拟合流程）。
      3) **推进格式的口径依赖**：一阶 Godunov 迎风 |∇φ| 带一个**与取向有关**的误差，
         把有效各向异性压低 ~8%（实测 a2 比值 0.90–0.93，且**不随 dx 收敛**）；
         换中心差分 |∇φ| 后 a2 比值 **0.99–1.01** ✓。故本判据用 `adv_grad='central'`
         （光滑 SDF 下二阶、实测稳定），并把 upwind 的结果一并打印作为口径对照。
    """
    g = LevelSetSurface(N, N * dx, gamma=gamma, Mob=M, R0=R0,
                        reinit_every=reinit_every, ndim=2, nz=nz)
    x = (np.arange(N) + 0.5) * dx
    X, Y = np.meshgrid(x, x, indexing='ij')
    c0 = 0.5 * N * dx
    rperp = np.sqrt((X - c0) ** 2 + (Y - c0) ** 2)
    g.phi = rperp[..., None] - R0 * np.ones((1, 1, g.Nz))   # 圆柱（xy 截面为圆）
    V0 = g.volume()            # ★ 用**三维**测度配 `area()`（见 project_volume 的记账）
    npref = np.array([1.0, 0.0, 0.0])
    v0 = M * gamma / R0
    dt = dtfac * dx / v0
    zs = g.Nz // 2
    tau = R0 ** 2 / (3.0 * M * gamma)          # 形状模（m=2）线性时间常数
    if verbose is None:
        verbose = max(1, nstep // 4)
    print('---- W1 Wulff 形状（Λ=%.2f, herring=%s, adv=%s）%s ----'
          % (Lam, herring, adv_grad, tag))
    print('   N=%d dx=%.2f nm 柱体 R0=%.2f nm (R0/dx=%.1f) | dt=%.3e s (%.3f 胞/步) | '
          '%d 步 = %.1f 个形状时间常数'
          % (N, dx * 1e9, R0 * 1e9, R0 / dx, dt, dt * v0 / dx, nstep, nstep * dt / tau))
    print('   %6s %9s %9s %8s %9s %9s %8s %7s' %
          ('step', 'a2/a0', 'a2_th', '比', 'a4/a0', '长轴(°)', 'h/g 离散', '点'))
    hist = []
    for k in range(nstep + 1):
        if k % verbose == 0 or k == nstep:
            P, Nn = g.interface_points(band=1.5, zslice=zs)
            if len(P) < 20:
                print('   k=%4d 界面点太少(%d) ⇒ 发散' % (k, len(P)))
                return False, dict(a2=np.nan)
            met = _shape_metrics(P[:, :2], Nn[:, :2], g.region_center()[:2], Lam,
                                 np.array([1.0, 0.0]), nbin=nbin)
            met['step'] = k
            met['R_eq'] = g.radius_2d()
            hist.append(met)
            print('   %6d %9.4f %9.4f %8.3f %9.4f %9.1f %9.4f %7d'
                  % (k, met['a2'], met['a2_th'], met['a2'] / met['a2_th'], met['a4'],
                     met['psi_axis'], met['h_spread'], met['n']))
        if k == nstep:
            break
        g.advance(dt, df=0.0, aniso=Lam, npref=npref, herring=herring,
                  adv_grad=adv_grad)
        g.project_volume(V0)
    fin = hist[-1]
    ratio = fin['a2'] / fin['a2_th'] if fin['a2_th'] > 1e-6 else np.inf
    # 拉长方向到 {±90°}(mod 180°) 的角距离
    axerr = abs((fin['psi_axis'] % 180.0) - 90.0)
    if mode == 'floor':
        # Λ=0 档：理论无各向异性 ⇒ 不能套形状判据，只查"量测到的伪各向异性有多大"
        ok = (fin['a2'] < 0.010) and (fin['a4'] < 0.020) and (abs(fin['asp_fit'] - 1.0) < 0.02)
        print('   末态 a2/a0=%+.5f（应≈0） a4/a0=%.5f（网格 4 次伪模） 拟合长径比=%.5f'
              % (fin['a2'], fin['a4'], fin['asp_fit']))
        print('   判定[数值底噪]: %s' % ('PASS' if ok else 'FAIL'))
        return ok, fin
    print('   末态 a2/a0 = %.4f（理论 %.4f，比 %.3f） | 拉长方向 %.1f°（理论 ±90°，误差 %.1f°）'
          % (fin['a2'], fin['a2_th'], ratio, fin['psi_axis'], axerr))
    print('        h/γ 离散 %.4f | 与 Wulff 极径偏差 %.4f（含分箱偏置，保守）'
          % (fin['h_spread'], fin['dev']))
    ok = (abs(ratio - 1.0) < 0.15) and (axerr < 25.0) and (fin['h_rms'] < 0.10)
    print('        h/γ 稳健 RMS = %.4f（判据 <0.10）; a2 比 %.3f（判据 |比-1|<0.15）; '
          '轴误差 %.1f°（判据 <25°）' % (fin['h_rms'], ratio, axerr))
    print('   判定[herring=%s adv=%s]: %s' % (herring, adv_grad, 'PASS' if ok else 'FAIL'))
    if plot:
        _plot_w1(hist, Lam, herring, plot)
    return ok, fin


def W1_control(Lam=0.4, nstep=600, N=64, dx=2e-9, R0=1.2e-8, nbin=36,
               adv_grad='central', dtfac=0.05):
    """W1 的**三档对照**（同一初始形状、同一推进格式，只差 Herring 项与各向异性幅值）：
         ① Λ=0       : 数值底噪（平衡必须是正圆 ⇒ 量出**纯数值**各向异性）
         ② herring=T : 正对照，应 PASS
         ③ herring=F : 反向对照，应 FAIL（拿 γ 当刚度 ⇒ 长轴转到 x̂、长径比腰斩）
       同时给出 upwind 口径下 ② 的结果，量化推进格式带来的口径偏差。"""
    res = {}
    print('==== ① Λ=0 数值底噪（理论 a2=0、长径比=1.000）====')
    ok0, f0 = W1_wulff(Lam=0.0, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                       herring=True, adv_grad=adv_grad, dtfac=dtfac, tag='（数值底噪）',
                       mode='floor')
    res['floor_a2'] = f0.get('a2', np.nan)
    res['floor_a4'] = f0.get('a4', np.nan)
    res['ok_floor'] = ok0
    print('==== ② Herring 正对照（Λ=%.2f）====' % Lam)
    ok1, f1 = W1_wulff(Lam=Lam, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                       herring=True, adv_grad=adv_grad, dtfac=dtfac, tag='（正对照）',
                       plot='/mnt/f/speed_up/pipeline/ca_pf_framework/FIG_W1_wulff_herring.png')
    print('==== ③ 反向对照：herring=False（拿 γ 当刚度）====')
    ok0b, f0b = W1_wulff(Lam=Lam, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                         herring=False, adv_grad=adv_grad, dtfac=dtfac, tag='（反向对照）',
                         plot='/mnt/f/speed_up/pipeline/ca_pf_framework/FIG_W1_wulff_naive.png')
    print('==== ④ 口径对照：upwind |∇φ| ====')
    oku, fu = W1_wulff(Lam=Lam, nstep=nstep, N=N, dx=dx, R0=R0, nbin=nbin,
                       herring=True, adv_grad='upwind', dtfac=dtfac, tag='（上风口径）')
    res.update(ok_h=ok1, ok_n=ok0b, ok_up=oku)
    ok = bool(ok1) and (not ok0b)
    print('---- W1 总判定 ----')
    print('   ① 数值底噪      : a2/a0 = %+.4f（应 ≈0）' % res['floor_a2'])
    print('                      a4/a0 = %+.4f（网格 4 次伪模）' % res['floor_a4'])
    print('   ② Herring       : a2/a0 = %.4f / 理论 %.4f = %.3f ; 长轴 %.1f° ; h/γ %.4f ⇒ %s'
          % (f1['a2'], f1['a2_th'], f1['a2'] / f1['a2_th'], f1['psi_axis'],
             f1['h_rms'], 'PASS' if ok1 else 'FAIL'))
    print('   ③ 非 Herring    : a2/a0 = %.4f / 理论 %.4f = %.3f ; 长轴 %.1f° ; h/γ %.4f ⇒ %s'
          % (f0b['a2'], f0b['a2_th'], f0b['a2'] / f0b['a2_th'], f0b['psi_axis'],
             f0b['h_rms'], 'PASS' if ok0b else 'FAIL'))
    print('   ④ 上风口径(仅报告): a2 比值 %.3f ⇒ 一阶迎风的取向偏置 %.1f%%'
          % (fu['a2'] / fu['a2_th'], 100 * (fu['a2'] / fu['a2_th'] - 1)))
    print('   ⇒ W1（Herring 项必需、且 Wulff 形状量测无误）: %s' % ('PASS' if ok else 'FAIL'))
    return ok
def _plot_w1(hist, Lam, herring, path, ttf='/mnt/c/Windows/Fonts/simhei.ttf'):
    """W1 的可视化：形状轮廓 / 归一化极径 vs Wulff 理论 / h-γ 比值"""
    import os
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    if os.path.exists(ttf):
        try:
            fm.fontManager.addfont(ttf)
            plt.rcParams['font.family'] = fm.FontProperties(fname=ttf).get_name()
        except Exception:
            pass
    plt.rcParams['axes.unicode_minus'] = False
    fin = hist[-1]
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    # (a) 轮廓 + 理论 Wulff
    pth, prho = _wulff_polar(Lam)
    kk = prho / prho.mean() * fin['R_eq'] * 1e9
    ax[0].plot(pth * 180 / np.pi, kk, 'k--', lw=2, label='Wulff 理论（包络 h=γ）')
    m = np.abs(fin['psi']) <= np.pi
    ax[0].plot(np.degrees(fin['psi'][m]), fin['rho'][m] * 1e9, '.', ms=2, alpha=0.5,
               label='量测界面点')
    ax[0].set_xlabel('位置角 ψ (°)'); ax[0].set_ylabel('极径 (nm)')
    ax[0].set_title('Q1: 形状轮廓 vs Wulff 理论（herring=%s, Λ=%.2f）' % (herring, Lam))
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    # (b) 归一化极径
    ax[1].plot(fin['ctr'] * 180 / np.pi, fin['rn'], 'o-', label='量测（归一）')
    ax[1].plot(fin['ctr'] * 180 / np.pi, fin['pr'], 'k--', label='Wulff 理论（归一）')
    ax[1].set_xlabel('位置角 ψ (°)'); ax[1].set_ylabel('归一化极径 ρ/⟨ρ⟩')
    ax[1].set_title('Q2: 归一化极径（偏差 %.3f）' % fin['dev'])
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    # (c) h/γ
    ax[2].hist(fin['ratio'] / (fin['ratio'].mean() + 1e-30), bins=30, alpha=0.8)
    ax[2].set_xlabel('h/γ（归一）'); ax[2].set_ylabel('计数')
    ax[2].set_title('Q3: 支撑函数 h/γ（离散度 %.3f，应为常数）' % fin['h_spread'])
    ax[2].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print('   [图] 已写 %s' % path)


def M3_McLean(N=32, dx=2e-9, nstep=400):
    """面上场 Γ 的局部平衡：应收敛到 McLean/Langmuir 解析值（新表示下重做 H3）"""
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=0.0)
    # 一个平面界面：区域1 占 z<L/2。★ 记账（本轮修）：必须用**真 SDF** φ = z − L/2，
    # 不能用 ±1e-9 的**阶跃**。阶跃场里 |∇φ| 只在 1 层胞非零 ⇒ `cell_area_geom` 的
    # coarea 估计（Σ|∇φ|dx²/3，"/3" 对应 SDF 的 ±1.5dx 三层带）**偏小 3 倍**；
    # 真 SDF 的带恰好是 3 层、每层 |∇φ|=1 ⇒ Σ = dx² 每列 = 正确面积 ✓。
    g.phi[1] = (np.arange(N)[None, None, :] * dx - 0.5 * N * dx) * np.ones((N, N, N))
    g.init_parent()
    g.c[:] = 0.036
    for _ in range(nstep):
        g.update_Gamma(2e-11)
    # ★ 记账（本轮修）：界面胞集合必须用**面积掩模** `cell_area_geom() > 0`
    #   （= `update_Gamma` 内部用的同一个掩模），**不能**用 `surface_band()`：
    #   后者按"邻胞区域号不同"取，在**周期 BC**下会把 `z=0` 的 wrap 层误判成界面
    #   （实测量到 layer 0 与 layer 24 两层，各 384 胞）。那里 Γ 恒为 0 且会被
    #   `update_Gamma` 的 (3') 清零 ⇒ 把它算进均值会**恰好把 Γ 砍半**
    #   （实测 Γ_model/Γ_McLean = 0.477 ⇒ 就是这个假象，不是物理）。
    m = g.cell_area_geom() > 0
    Geq = g.Gamma_eq(g.c[m])
    rel = float(np.abs(g.Gam[m] - Geq).max() / max(np.abs(Geq).max(), 1e-30))
    print('---- M3 面上场偏析平衡（level-set 表示，重做 H3）----')
    print('   T=%.0f K: Γ_model=%.4e mol/m² ; Γ_McLean=%.4e ; 最大相对差 %.2e   %s'
          % (g.T, float(g.Gam[m].mean()), float(Geq.mean()), rel,
             'PASS' if rel < 0.05 else 'FAIL'))
    return rel < 0.05


def geom_stats(g, topk=6, min_cells=200):
    """几何统计（G4 的正确测度，在 level-set 表示下重做）：
       · 每个变体的回转张量半轴比（长:短）—— 板条应显著各向异性
       · 最小本征值的本征向量 = 板片法向 ⇒ 与"该变体参与的 rank-1 相容对法向"比夹角"""
    from scipy import ndimage
    from windowB_bench3d import rank1_normal
    from windowB_ti64_variants import variants
    eps0, _, _ = variants()
    nv = len(eps0)
    comp = {}
    for a in range(nv):
        for b in range(a + 1, nv):
            res, n = rank1_normal(eps0[b] - eps0[a])
            if res < 1e-9:
                comp[(a + 1, b + 1)] = n
    reg = g.region()
    st = ndimage.generate_binary_structure(3, 3)
    rows = []
    for k in range(1, g.nreg):
        m = (reg == k)
        if m.sum() < min_cells:
            continue
        lab, n = ndimage.label(m, structure=st)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        for j, sz in enumerate(sizes, 1):
            if sz < min_cells:
                continue
            pts = np.argwhere(lab == j).astype(float) * g.dx
            pts -= pts.mean(0)
            G = (pts.T @ pts) / len(pts)
            w, V = np.linalg.eigh(G)
            rows.append((sz, k, w, V[:, 0]))
    rows.sort(key=lambda r: -r[0])
    print('   [几何] 最大的 %d 个域（回转半轴比 长:短；n=板片法向）:' % min(topk, len(rows)))
    angs = []
    for sz, k, w, nvec in rows[:topk]:
        r = (w[2] / max(w[0], 1e-30)) ** 0.5
        best = min((np.degrees(np.arccos(min(1.0, abs(float(nvec @ nrm)))))
                    for (a, b), nrm in comp.items() if k in (a, b)), default=np.nan)
        if not np.isnan(best):
            angs.append(best)
        print('     V%2d 体积=%6d 胞  长:短=%.2f  n=[%+.2f %+.2f %+.2f]  与相容法向夹角 %.1f°'
              % (k, int(sz), r, *nvec, best))
    if angs:
        print('   [几何] 法向 vs 相容法向: 中位 %.1f°  最小 %.1f°' % (np.median(angs), min(angs)))
    return rows


def M4_conservation(N=32, dx=2e-9, nstep=150, df=-1e8, tag='溶解(历史工况)',
                    tol=1.0e-3, verbose=True):
    """体相 + 面过剩的守恒。

    ★ W-6d（2026-09-25）三处改动，都是为了让它**有信息量**：
      1) 门槛 2.5e-2 -> **1e-3**（2.5% 太松，PASS 没有信息量）；
      2) 同时上报**两个工况**：@BT@df=-1e8@BT@（溶解，历史工况）与 @BT@df=+1e8@BT@（成长，物理工况，
         符号按判据 T2.1b-7 的判决）；两者的残差**差 30 倍**，只报一个会把缺陷藏起来；
      3) 把"Stefan 只做了推给邻居、没做面储存/回吐"那条旧备注删掉（机制早已实现，W-6）。
    """
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, df])
    g.seed_sphere(1, [0.5 * N * dx] * 3, 5 * dx)
    g.init_parent()
    g.c[:] = 0.036
    mb0, ms0 = g.totals()
    dt = 0.2 * dx / (1e-9 * 1e8)
    for _ in range(nstep):
        g.advance(dt)
        g.update_Gamma(dt)
    mb1, ms1 = g.totals()
    rel = abs((mb1 + ms1) - (mb0 + ms0)) / abs(mb0 + ms0)
    if verbose:
        print('    %-14s : 相对漂移 %.3e   面 %+.3e   体 %+.3e   %s（门槛 %.0e）'
              % (tag, rel, ms1 - ms0, mb1 - mb0, 'PASS' if rel < tol else 'FAIL', tol))
    return rel


def M4_report(N=32, nstep=150):
    """M4 两工况 + 门槛判定（任一 FAIL 则整体 FAIL）。★ 记账：残差主要是**体相**在丢溶质
       （两面工况的  都恰好为 0）⇒ W-6e 要查  的记账去向。"""
    print('---- M4 守恒（体相 + 面过剩，level-set 表示）—— 两工况 ----')
    r1 = M4_conservation(N=N, nstep=nstep, df=-1e8, tag='溶解(历史)')
    r2 = M4_conservation(N=N, nstep=nstep, df=+1e8, tag='成长(物理)')
    print('    记账：面量按摩尔/胞（Gam_mol）记账、带外强制回吐（W-6c/W-6d），')
    print('           派生 Gam 后同步 （否则兼容 guard 每步误触发 => 体相丢溶质）。')
    print('          ★ W-6e（2026-09-25）：上述同步就是把本判据从 8.9e-2 压到 2e-16 的那一步。')
    print('          "Stefan 只做了推给邻居、没做面储存/回吐"那条旧备注**已作废**（机制早已实现）。')
    ok = (r1 < 1.0e-3) and (r2 < 1.0e-3)
    print('    M4 判定: %s（溶解 %.2e / 成长 %.2e，门槛 1e-3）'
          % ('PASS' if ok else 'FAIL', r1, r2))
    return ok


if __name__ == '__main__':
    print('=' * 92)
    print('Gibbs 面场（level-set）+ 体相场：判据 S0/S1')
    print('=' * 92)
    res = {}
    res['S0'] = S0_curvature()
    res['S1'] = S1_GibbsThomson()
    res['M1'] = M1_multiregion_conservation()
    res['M3'] = M3_McLean()
    res['M4'] = M4_conservation()
    M2_twelve_variants()
    print('\n总判定: %s' % ('ALL PASS' if all(res.values())
                          else 'FAIL -> %s' % [k for k, v in res.items() if not v]))
    raise SystemExit(0)
