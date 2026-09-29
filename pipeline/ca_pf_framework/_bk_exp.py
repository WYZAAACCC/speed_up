#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_exp.py —— **阶段 3 生产装置**：在一个盒子里播 M 根同变体板条，看它们
能否各自长大、沿 @@\\mathbf n^*@@ 堆叠成块、被低角晶界分隔（F3）、而不是合并。

## 与 `_bk_smoke_f3.py` 的区别

| | smoke | **本文件（生产）** |
|---|---|---|
| 板条表 | 复制 `eps0`（无 θ） | **`windowB_lath.LathTable`**：逐板条变体 + 小转动 ⇒ F3 面能 = @@\\gamma_{\\rm RS}(\\theta)@@ |
| 板条数 | 2 | **M（`--laths`）** |
| 布条方式 | 面对面 | **沿 @@\\mathbf n^*@@ 堆叠**（`--gap-nm`） |
| 量具 | 内嵌 | **`_bk_measure.measure_state`**（16 条对照已验证） |
| 记账 | 无 sha | **meta.json 记引擎 sha + 全部参数 + 臂定义** |
| 落盘 | snap | snap（全量 φ+region）+ series.csv + meta.json，**目录带时间戳不覆盖** |

## 臂（`--arm`）

| 臂 | 含义 |
|---|---|
| `dry` | F3 面能 = @@\\gamma_{\\rm RS}(\\theta)@@（**C-1/C-3 的物理结论**，主臂） |
| `wet` | F3 面能 = @@\\gamma_f@@（规定值；= 用户要的"Gibbs 面薄膜"） |
| `gpos` | **量具正对照**：@@\\gamma_\\Sigma@@=100 J/m²（界面必须明显移动） |
| `gneg` | **量具负对照**：所有板条播进**同一个场**（F3 必须恒为 0） |
| `g0` | **极限对照**：@@\\gamma_\\Sigma@@=0（界面无面能） |

## 用法

    python3 _bk_exp.py --dry-run                       # 只构造+播种+初始测量
    python3 _bk_exp.py --arm dry --steps 400 --N 192 --dx-nm 62.5
"""
import argparse
import csv
import json
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
import _bk_measure as BM                                        # noqa: E402
import windowB_km as KM                                         # noqa: E402
import windowB_closure as CL                                    # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402
from windowB_km import (ALPHA_KM_REF, M_S_TI64, T0_TI64, DS_REF,
                        DG_CRIT_REF)                            # noqa: E402

COLS = ['step', 't_s', 'wall_s', 'dt', 'V0', 'Vt', 'M', 'nreg_used',
        'nslab_n', 'nf3_col', 'runs', 'ncomp_min', 'ncomp_max', 'ncompbig_max',
        # ★ Round 10：**逐板条的体积与厚度，每一步都存**。
        #   为什么必须加：`Vt` 只有总量，而 V-2（"每根都在长"）与"咬入是否把
        #   旧片削薄"都只能靠**快照**判 —— 而快照默认 50 步一个 ⇒ 中间过程全丢。
        #   用户的要求是"全过程数据留盘、量具有 bug 也能事后重测"
        #   ⇒ 这两列必须在**每个测点**上写。用 `'/'` 连接（与 `runs` 同格式），
        #   这样 COLS 固定、M 可变。
        'vols', 'ths',
        # ★★★ R18：**逐对 F3 面积**（`i-j:A/...`，µm²）。加它的理由（R17 的线索）：
        #   实测引擎臂在**每次形核后的 10 步内** `f3_area` 掉 7–13%，
        #   而驱动层 `gs5` 只掉 0.6% ⇒ "每次新事件把已存在的界面推开一部分"。
        #   但**总量**看不出是**哪几对**被吃 ⇒ 必须逐对、且**每个测点**都记。
        #   `--pair-every 0`（默认）⇒ 不记 ⇒ 与改动前逐位相同（列会是空串）。
        'f3_pairs',
        'nf3', 'f3_area_m2', 'f3_area_stair', 'f3_pos_m', 'f3_pos_dx',
        'f3_std_m', 'n_lath', 'w_lath', 'a_lath', 'box_touch', 'finite',
        'psi_mean']
assert len(COLS) == len(set(COLS))


def read_series(path):
    """读 `series.csv` ⇒ `{列名: np.ndarray}`；整型列给 int，数值列给 float，
    其余（如 `runs='5/3/1/2/4/6'`）原样给 str。

    ★★ 为什么不能用 `np.genfromtxt(..., names=True, dtype=None)`：
    `runs` 这一列是**斜杠分隔的字符串**，而 genfromtxt 的类型自动升级会按
    `bool→int→float→complex→longdouble` 一路试到底，最后抛
    `ValueError: Cannot convert string '1/2'`。
    实测后果：`dry_gs2` **老老实实跑完 200 步**（数据全部落盘、完好），
    却在收尾打印判决时崩掉 ⇒ **主判据一个字都没打出来**，
    日志尾部看起来像"跑挂了"。（`--dry-run` 走不到这里，所以之前没暴露。）
    """
    import csv as _csv
    with open(path, newline='') as f:
        rows = list(_csv.DictReader(f))
    if not rows:
        return {}
    out = {}
    for c in rows[0]:
        vals = [r[c] for r in rows]
        for conv in (int, float):
            try:
                out[c] = np.array([conv(v) for v in vals])
                break
            except (TypeError, ValueError):
                continue
        else:
            out[c] = np.array(vals, dtype=object)
    return out


def sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def build_table(laths, omega_max_deg, omega_mode, a_ax=None, gamma0=0.15):
    """按 `--laths` 建板条表。`a_ax` 给出时把倾转轴定为板条长轴。"""
    M = len(laths)
    om = WL.default_omega(M, omega_max_deg, axis=a_ax, mode=omega_mode)
    return WL.LathTable(laths, omegas=om, eps0_var=EPS0, npref_var=NPF,
                        gamma0=gamma0)


def _block_span_n(g, n_hab, BM_):
    """当前 α′ 集合沿 n* 的 (中心, 最小投影, 最大投影)。只在小包围盒上算。"""
    reg = g.region()
    m = (reg > 0)
    if not m.any():
        return None
    bb = BM_._bbox_of(m, pad=2)
    cc = BM_._sub_coord(bb, g.dx)
    pn = (n_hab[0] * cc[0][:, None, None] + n_hab[1] * cc[1][None, :, None]
          + n_hab[2] * cc[2][None, None, :])
    v = pn[m[bb]]
    return float(v.min()), float(v.max())


def run(a):
    N, L = a.N, a.dx_nm * 1e-9 * a.N
    dx = L / N
    tag = a.tag or time.strftime('%m%d_%H%M%S')
    outdir = os.path.join(a.out, '%s_%s' % (a.arm, tag))
    os.makedirs(outdir, exist_ok=True)
    P = lambda s: print(s, flush=True)
    P('=' * 104)
    P('_bk_exp  臂=%s  N=%d  Δx=%.2f nm  L=%.3f µm  steps=%d  tag=%s'
      % (a.arm, N, dx * 1e9, L * 1e6, a.steps, tag))
    P('=' * 104)

    # ---------------- 臂定义 ----------------
    laths = [int(x) for x in a.laths.split(',') if x.strip()]
    M = len(laths)
    single_field = (a.arm == 'gneg')
    if single_field:
        laths_eff = [laths[0]]
        P('★ 负对照 gneg：**%d 根板条全部播进同一个场 φ_%d** ⇒ F3 应恒为 0'
          % (M, laths[0]))
    else:
        laths_eff = laths

    n_hab = np.asarray(NPF[laths[0]], float); n_hab /= np.linalg.norm(n_hab)
    # ★★ 拿 a/w 轴：**直接调静态方法**，不再造一个临时 `LevelSetMulti`
    #   （临时对象会再跑一遍 `_argmin_normal`；实测 4 臂并发时构造 >15 min）。
    _nref0, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[laths[0] - 1], float))
    _R0 = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[laths[0] - 1], float), _nref0)
    w_ax = np.asarray(_R0[2], float); w_ax /= np.linalg.norm(w_ax)
    a_ax = np.asarray(_R0[1], float); a_ax /= np.linalg.norm(a_ax)

    lt = build_table(laths_eff, a.omega_max_deg, a.omega_mode, a_ax=a_ax,
                     gamma0=a.gamma0)
    P(lt.summary())
    gmax, g2ab, wets = lt.wetting_report()
    P('润湿判据（(4.6)）：γ_RS 最大 %.4f  vs  2γ_αβ = %.4f  ⇒ %s'
      % (gmax, g2ab, '**润湿**' if wets else '不润湿（C-1）'))
    if a.arm == 'wet':
        P('★ 臂 wet：F3 面能被**规定**为 γ_f=%.4f J/m²（人为亚稳膜）' % a.gamma_film)
        lt.gtab[np.isfinite(lt.gtab)] = float(a.gamma_film)
    elif a.arm == 'gpos':
        lt.gtab[np.isfinite(lt.gtab)] = 100.0
    elif a.arm == 'g0':
        lt.gtab[np.isfinite(lt.gtab)] = 0.0
    # ★★★ `auto`：**面带 ψ 判决臂**（`BLOCK_DERIVATION` §4.6 / 预言 P-2）。
    #   F3 面能按 γ_Σ(ψ) 混合，ψ 在 F3 胞上按局域 Allen–Cahn 演化。
    #   ⚠ `psi0` **不能取 1.0**：ψ≡0 与 ψ≡1 都是 (4.9) 的**精确不动点**
    #     （f'(0)=f'(1)=g'(0)=g'(1)=0）⇒ 从 1.0 出发一步都不动。
    #     取 0.99 等价于给一个无穷小扰动（见 `windowB_film.py` 的记账）。

    eps0 = [np.asarray(EPS0[v - 1], float).copy() for v in laths_eff]
    npref = {i + 1: np.asarray(NPF[v], float) for i, v in enumerate(laths_eff)}
    nv = len(laths_eff)

    # ================= ★★★ R29：athermal 形核律的**钟**（T → 驱动力 → 事件）=========
    #   用户要求：「能否使用类似形核率等等的方式让模型在现有物理公式与框架的基础上
    #   合理运转」。本块把 `windowB_closure` 的 C-2/C-3 闭式接进引擎：
    #     ① 温度钟 `T(t) = T_start − q·t`（`windowB_km.linear_cool`）；
    #     ② 驱动力 `df(T) = drive_of_T(T; T0, DS)` —— 引擎 T6 已有 `set_T` 入口；
    #     ③ 板条数 `n(T) = α_KM·(M_s − T)` —— **`n` 从规定值变成导出量**；
    #     ④ 步长 `dt = cfl·dx/(MOB·ΔG_v(T))` —— 随降温自动变小（速度变大）。
    #   ⚠ 全部 gated 在 `--nuc-law athermal` 上 ⇒ 默认 `cadence` 路径**逐位不变**。
    _athermal = (a.nuc_law == 'athermal')
    _alpha = float(a.alpha_km)
    # ★ 时钟起点默认 = C-2 的 **T_1**（预摆的第 1 片就是第 1 根，见
    #   `windowB_closure.T_start_of_clock`）。从 `M_s` 起会让事件序列整体错位一根。
    _Tstart = (float(a.T_start) if float(a.T_start) > 0
               else CL.T_start_of_clock(_alpha))
    _Tend = float(a.T_end)
    _L_lath = float(a.plate_L) * 1e-9
    _q_source = 'user'
    if _athermal:
        _dG_start = float(KM.drive_of_T(_Tstart, T0_TI64, DS_REF))
        if _dG_start <= 0:
            raise SystemExit('✗ athermal：T_start=%.2f K 必须 < T0=%.1f K'
                             % (_Tstart, T0_TI64))
        _v_worst = CL.v_of_MOB(MOB, _dG_start)
        _q_cap = CL.q_max_ordered(_v_worst, _alpha, _L_lath)
        if float(a.cool_rate) > 0.0:
            _q = float(a.cool_rate)
        else:
            _q = _q_cap * float(a.cool_ratio)
            _q_source = 'C-3 有序性上界 × %.2f' % float(a.cool_ratio)
        _ok_o, _ratio_o, _ = CL.ordered_ok(_q, MOB, _alpha, _L_lath,
                                           dG_worst=_dG_start)
        _n_law = CL.n_lath_int(_Tend, _alpha)
        _T_of_t = KM.linear_cool(_Tstart, _Tend, (_Tstart - _Tend) / _q)
        _dG_of_T = (lambda T: KM.drive_of_T(T, T0_TI64, DS_REF))
        _df_start = float(_dG_of_T(_Tstart))
        P('★★★ R29 athermal 形核律：α_KM=%.4e /K  冷速 q=%.4e K/s（%s）'
          % (_alpha, _q, _q_source))
        P('   时钟起点 T_start = T_1 = M_s − 1/α_KM = %.2f K（**不是 M_s**：'
          'n(M_s)=0 ⇒ t=0 预摆的那片就是第 1 根）' % _Tstart)
        P('   T: %.1f → %.1f K，t_sim=%.4e s；df: %.4e → %.4e J/m³'
          % (_Tstart, _Tend, _T_of_t.t_cool, _df_start, float(_dG_of_T(_Tend))))
        P('   导出板条数 n = floor(α_KM·(M_s − T_end)) = **%d**（当前 nv=%d）'
          % (_n_law, nv))
        P('   形核温度 T_k = M_s − k/α_KM: %s'
          % ' '.join('T%d=%.1f' % (k, CL.T_of_k(k, _alpha)) for k in range(1, _n_law)))
        P('   C-3 有序性：Δt_grow/Δt_nuc = **%.3f**（判据 ≤1）%s'
          % (_ratio_o, '' if _ok_o else '  ⚠ **违反 ⇒ 本次运行处于 burst regime，必须记账**'))
        P('   C-3 步数下界 = %.0f（从 T_1 起）；C-5 β_h 下界 = %.3f（当前 --beta-h %.2f）'
          % (CL.steps_min_ordered(_alpha, _L_lath, dx, 0.15, _Tend, _Tstart),
             CL.beta_h_min(a.steps, dx, a.plate_T * 1e-9), a.beta_h))
        if nv < _n_law:
            P('   ⚠⚠ **表示上限不足**：nv=%d < 导出的 n=%d ⇒ 块会被截断在 nv 根'
              % (nv, _n_law))
        _beta_floor = CL.beta_h_min(a.steps, dx, a.plate_T * 1e-9)
        if _beta_floor > a.beta_h:
            P('   ⚠⚠ **C-5 不满足**：%d 步 / Δx=%.1f nm / t=%.0f nm 需要 β_h ≥ %.3f，'
              '而当前 %.2f ⇒ 板条会增厚 ≈ e^{%.2f}× ⇒ 厚度判据 V-8b 不适用'
              % (a.steps, dx * 1e9, a.plate_T, _beta_floor, a.beta_h,
                 _beta_floor - a.beta_h))
    else:
        _q = float('nan'); _n_law = -1; _T_of_t = None; _dG_of_T = None
        _df_start = float(DF)

    t0 = time.time()
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=a.gamma0, Mob=MOB,
                        df=[0.0] + [_df_start] * nv, workers=a.nthreads,
                        reinit_every=0, reinit_dt=a.reinit_dt,
                        reinit_band_cells=a.reinit_band,
                        dG_of_T=_dG_of_T, T_of_t=_T_of_t,
                        T=(_Tstart if _athermal else None))
    g.lath = lt
    # ★★★ R12：`--arm eng` —— **引擎侧自发形核**的接线。
    #   `vgroup` 告诉引擎哪些场同变体（本臂 6 个场全是变体 1）；
    #   `nfsv` 让同变体形核播进**新的空场**（否则只会加厚第一片）；
    #   `attach` 让新核与源板条**共用一张界面**（C-1 干晶界 regime）。
    n_eng_ev = 0
    _ed_dummy = None
    # ★★ `nuc_cfg` 必须**等 `vmap` 建好之后**再调（`vgroup=vmap`）——
    #   第一版把它放在 `g.lath = lt` 旁边，`vmap` 还没定义 ⇒ UnboundLocalError。
    #   故这里只置一个"待接线"标志，真正的 `nuc_cfg` 在 `vmap` 之后（见下）。
    if a.arm == 'auto':
        # `psi0` 取 0.99（**不能取 1.0**，见上面记账）
        g.film = dict(gamma_f=float(a.gamma_film), W=0.05, L=1.0e8, psi0=0.99)
        P('★ 臂 auto：面带 ψ 开启（γ_f=%.3f, W=0.05, L=1e8, psi0=0.99）'
          % a.gamma_film)
    P('构造 %.1f s（%d 个场；`lath` 已挂上 ⇒ F3 走 γ_RS）' % (time.time() - t0, g.nreg))
    P('   n*=%s  w=%s  a=%s  (n*·a=%.4f)'
      % (np.array2string(n_hab, precision=4), np.array2string(w_ax, precision=4),
         np.array2string(a_ax, precision=4), float(n_hab @ a_ax)))

    # ---------------- 播种：沿 n* 堆叠 M 片 ----------------
    c0 = np.array([L / 2] * 3)
    T, gap = a.plate_T * 1e-9, a.gap_nm * 1e-9
    span = (M - 1) * (T + gap)
    P('播种 %d 片（%s nm）沿 n* 堆叠：厚 %.0f nm、间隔 %.0f nm、跨度 %.2f µm；'
      '沿 a 长 %.0f nm、沿 w 宽 %.0f nm'
      % (len(laths_eff), laths_eff, a.plate_T, a.gap_nm, (span + T) * 1e6,
         a.plate_L, a.plate_W))
    # ================= ★★★ G-1 方案 B：**生长中的同变体邻位形核** =================
    #   文献机制（Furuhara 2008）：「A BLOCK IS FORMED BY REPEATED NUCLEATION OF THE
    #   SAME VARIANT OF LATHS ADJACENT TO EACH OTHER」。
    #   ⇒ t=0 **只播第 1 片**；此后每 `--nuc-every` 步，在当前块的**外侧**播下一片
    #     （**同一个变体、新的场**）⇒ 片与片之间自动成为 F3（低角晶界）。
    #   ★ 与"预先把 6 片摆好"的区别：核是**在长大过程中逐个出现**的，且每次出现前
    #     都要**先量当前块的实际延伸**（因为块已经长大了）⇒ 是"生长后堆叠"。
    #   ★ **零引擎改动**：场表 / `LathTable` 在构造时就按 `--laths` 建好，
    #     未播种的场一直是空的（φ=1e3 ⇒ 永远不是 argmin）。
    # ★ R12：`arm=eng` 也要"只播第 1 片 + `init_parent`"，但它**不走驱动层形核**
    #   （`--nuc-every 0`）⇒ 形核由下面的 `g.nucleate()` 负责。
    # ★ R28：**默认走引擎形核**（见下面的 `use_engine`）。
    use_engine = (a.arm == 'eng') or (a.nuc_mode == 'engine') or (
        a.nuc_mode == 'auto' and bool(a.grow_stack) and a.nuc_every <= 0)
    grow = bool(a.grow_stack) or (a.arm == 'eng') or use_engine
    n_seeded = 0

    def _seed_next():
        nonlocal n_seeded
        j = n_seeded + 1
        if j > nv:
            return None
        # ★★ Round 10：**补厚度**（`--nuc-compensate`）。
        #   张力（Round 9 实测）：界面要落在共享平面上 ⇒ 重叠 o 必须 ≥ 1 胞；
        #   但界面落在重叠区**中面** ⇒ 每张被重叠的面被吃 `o/2`，
        #   而**内层片两张宽面都是 F3、`Δf = Δe_el ≡ 0`，没有任何体驱动力**
        #   去补回来（§5.1）⇒ 被削薄就只会继续缩、碎裂
        #   （`gs3` 实测：板条 1 被撕成 20 个碎片，且碎片把 `f3_area` 刷到
        #    7.95 µm²，比预摆对照的 6.77 还大 —— 那是**污染**不是成绩）。
        #   ⇒ 出路不是调 o，而是**把会被咬掉的预先补上**：
        #       片 1..M−1：内外两张面都会被咬 ⇒ 播 `T + o`
        #       片 M     ：只有内面被咬       ⇒ 播 `T + o/2`
        #     这样每片的**稳态厚度都回到 T**，块总厚仍是 M·T。
        #   ⚠ 近端面必须仍在 `edge − o`（否则几何就变了）⇒ 中心相应移到
        #     `edge − o + T_j/2`。多出来的厚度加在**外侧**。
        o = a.nuc_overlap_nm * 1e-9
        _fr = float(a.nuc_compensate_frac)
        Tj = (T + _fr * (o if j < nv else 0.5 * o)) if (o > 0 and a.nuc_compensate) else T
        if j == 1:
            c = c0.copy()
        else:
            sp = _block_span_n(g, n_hab, BM)
            cproj = float(c0 @ n_hab)
            if sp is None:
                c = c0.copy()
            else:
                vlo, vhi = sp
                side = 1.0 if (j % 2 == 0) else -1.0
                edge = (vhi if side > 0 else vlo)
                # ★★ 记账（Round 3 实测更正）：原先放 **1.5 胞（94 nm）** 的间隙，
                #   想让两侧"长到一起"。实测**不会**发生：
                #     间隙里是**母相 β** ⇒ 两侧都是 F1（α′/β）界面，有驱动力，
                #     但**宽面被 β_h 重钉扎** ⇒ 实测宽面推进只有 **0.26 nm/步**
                #     （端板条 Δn=+13 nm/50 步）⇒ 47 nm 要 **~180 步** > 200 步预算。
                #   ⇒ 物理上"sympathetic 邻位形核"本来指**在已有板条的界面上形核**
                #     （Furuhara 2008 的 repeated nucleation adjacent to each other）
                #     ⇒ 新核应当**贴着**已有块放。间隙由 `--nuc-gap-nm` 控制（默认 0）。
                # ★★ Round 9 实测新增（`_bk_pair.py`，gs2 末态）：
                #   "贴着放"**还不够**。`edge` 是**格心**投影，`T=250 nm = 4Δx`，
                #   于是新片的零水平集落在**非格点**位置 ⇒ 两列阶梯错开 ⇒
                #   界面被劈成两半：
                #       1-2 界面：F3 直接接触 0.4601 + **1 胞厚 β 膜 0.9492**
                #                 = 1.4093 µm² ≈ 整片足迹 ⇒ 覆盖率仅 0.33
                #       2-4：0.4081 + 0.9102；4-6：0.5136 + 0.7617（+侧全如此）
                #       而 −侧 3-1、5-3 是满的（1.5477 / 1.4804，几乎无 β）
                #   机理：`seed_plate` 用真 SDF 且把其它场抬到 `-sdf`，`argmin` 把
                #   界面定在**两个零水平集的中面**。所以**只要种子与旧片有重叠**，
                #   界面就是一张完整的阶梯面；**恰好相切**时中面退化成旧片的
                #   零水平集，台阶对不上的地方就留 1 胞 β（阶梯错位伪影，非物理）。
                #   ⇒ 用 `--nuc-overlap-nm` 让新片**咬进**旧片（物理上就是
                #     "在界面上形核"，共用一张界面，不是隔缝相望）。
                c = c0 + ((edge - cproj) + side * (Tj / 2 - o)) * n_hab
                c = c - L * np.floor(c / L)          # 周期折回
        g.seed_plate(j, c, n_hab, a.plate_W * 0.5e-9, Tj,
                     elong=a.plate_L / a.plate_W, along=a_ax, flat_end=True)
        n_seeded = j
        return j

    if grow:
        j0 = _seed_next()
        g.init_parent()
        P('★★ 生长中的同变体邻位形核：t=0 只播第 %d 片（场 %d）；'
          '此后每 %d 步在外侧播下一片（同一变体、新场）⇒ 片间自动成 F3'
          '； 咬入旧片 %.1f nm（`--nuc-overlap-nm`；0=相切，实测 F3 覆盖率仅 0.62）'
          '； 补厚度 %s（前 %d 片播 T+o，末片播 T+o/2）'
          % (j0, j0, a.nuc_every, a.nuc_overlap_nm,
             'ON' if a.nuc_compensate else 'OFF', max(nv - 1, 0)))
    elif len(laths_eff) == 1 and M > 1:
        for i in range(M):
            off = (i - (M - 1) / 2.0) * (T + gap)
            g.seed_plate(1, c0 + off * n_hab, n_hab, a.plate_W * 0.5e-9, T,
                         elong=a.plate_L / a.plate_W, along=a_ax, flat_end=True)
        n_seeded = M
        g.init_parent()
    else:
        for i in range(M):
            off = (i - (M - 1) / 2.0) * (T + gap)
            g.seed_plate(i + 1, c0 + off * n_hab, n_hab, a.plate_W * 0.5e-9, T,
                         elong=a.plate_L / a.plate_W, along=a_ax, flat_end=True)
        n_seeded = M
        g.init_parent()
    margin = 0.5 * L - 0.5 * (span + T) - 0.5 * a.plate_L * 1e-9
    P('   沿 n* 到盒壁余量 %.2f µm；沿 a 余量 %.2f µm（**700 步长跑会撞壁，见 §4.1**）'
      % ((0.5 * L - 0.5 * (span + T)) * 1e6, margin * 1e6))
    if margin < 0.5e-6:
        P('   ⚠⚠ 沿 a 余量 < 0.5 µm ⇒ **本算例会在中期撞盒壁**（`box_touch` 会置 1）')
    if span + T > L:
        raise SystemExit('✗ 堆叠跨度 %.2f µm > 盒 %.2f µm —— 播不下'
                         % ((span + T) * 1e6, L * 1e6))

    vmap = {i + 1: laths_eff[i] for i in range(nv)}
    # ★★★ R12：`--arm eng` —— **引擎侧自发形核**的接线（放在 `vmap` 之后）。
    #   `vgroup` 告诉引擎哪些场同变体（本臂 6 个场全是变体 1）；
    #   `nfsv` 让同变体形核播进**新的空场**（否则只会加厚第一片）；
    #   `attach` 让新核与源板条**共用一张界面**（C-1 干晶界 regime）。
    if use_engine:
        # ★ R28：**自动补厚度** —— 界面落在重叠区中面 ⇒ 每片被吃 `o/2`
        #   （两侧被吃的片吃 `o`）⇒ 引擎路径下把 `o` 加回 `t_nuc`。
        #   这样「只给 `--grow-stack`」的最简命令行也能复现 `eng12`。
        _t_nuc = a.eng_t_nm * 1e-9
        if use_engine and a.eng_t_nm <= 250.0 and a.nuc_overlap_nm > 0:
            _t_nuc = (250.0 + a.nuc_overlap_nm) * 1e-9
        g.nuc_cfg(a.eng_r_nm * 1e-9, _t_nuc, gamma=a.gamma0, n_init=0,
                  p_auto=0.0, harden_f=1.0, sym_gap_cells=0, max_per_step=1,
                  seed=a.eng_seed, var_rule='ed',
                  vgroup=vmap, nfsv=True, attach=True,
                  attach_overlap=a.nuc_overlap_nm * 1e-9,
                  elong=((a.eng_elong if a.eng_elong > 1.0
                          else (a.plate_L / a.plate_W if use_engine else 1.0))),
                  along=(a_ax if (a.eng_elong > 1.0 or use_engine) else None),
                  # ★ R23：默认**不传** ⇒ 由引擎自动决定（attach 下 = False）。
                  #   `--eng-force-reinit` 可强制打开（用于复现 eng5–eng10）。
                  force_reinit_after_event=(True if a.eng_force_reinit else None),
                  t_last_reduce=((a.eng_t_last_reduce_nm if a.eng_t_last_reduce_nm > 0
                                  else (a.nuc_overlap_nm * 0.5 if use_engine else 0.0))
                                 * 1e-9))
        _ed_dummy = np.zeros((g.nreg, 1, 1, 1))
        P('★★★ 臂 eng：**形核交给引擎**（`nucleate` 的 stack 通道 + attach + nfsv）'
          '；R=%.0f nm t=%.1f nm（**含自动补厚**），咬入 %.1f nm，节奏 %s，seed=%d'
          % (a.eng_r_nm, _t_nuc * 1e9, a.nuc_overlap_nm,
             ('每步' if a.eng_cadence == 0 else '每 %d 步' % a.eng_cadence),
             a.eng_seed))
        P('   %s'
          % ('✅ **速率由 athermal 律给出**（`--nuc-law athermal`）：'
             '`n(T) = α_KM(M_s − T)` ⇒ 事件温度 `T_k` 由 `α_KM` 与冷却给出，'
             '**不再是驱动层的节奏**。'
             if _athermal else
             '⚠ 记账：**速率仍由驱动层的节奏规定** —— 引擎的 sympathetic 通道'
             '在没有 `--nuc-law athermal` 时**没有速率律**（`use_fcrit` 只覆盖 `fresh`）。'))
        P('   核形状：%s'
          % ('**长条** elong=%.2f 沿 a 轴（与驱动层一致）' % a.eng_elong
             if a.eng_elong > 1.0 else
             '**圆盘**（引擎原行为）—— 实测足迹只有长条板的 1/5，'
             'F3 面积会小 ~7 倍'))
    np.savez_compressed(
        os.path.join(outdir, 'seeds.npz'), phi=g.phi.astype(np.float32),
        region=g.region(), n_hab=n_hab, w_ax=w_ax, a_ax=a_ax,
        vmap_keys=np.array(sorted(vmap)), vmap_vals=np.array([vmap[k] for k in sorted(vmap)]),
        N=N, L=L, arm=a.arm, laths=np.array(laths_eff))

    kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=a.beta_h,
              mob_beta_w=a.beta_w, adv_grad=a.adv, norm_smooth=a.norm_smooth,
              facet_lam=a.facet_lam, facet_eps=a.facet_eps)
    dt = 0.15 * dx / (MOB * DF)
    if _athermal:
        # ★ athermal 路径**逐步**按当前 ΔG_v 定 dt（见主循环）⇒ 这里打的是**首步**值。
        #   原先无条件打 `dt = 0.15·dx/(MOB·DF)`（DF=3.5e8 的常数），
        #   对 athermal 是**误导**（真实首步 dt = 0.15·dx/(MOB·ΔG_v(T_1))）。
        dt = 0.15 * dx / (MOB * max(_df_start, 1e-300))
        P('dt **首步** = %.4e s（%d 步 ⇒ 名义 t_sim=%.3e s，实际随 ΔG_v(T) 逐步缩小）；'
          'norm_smooth=%d' % (dt, a.steps, a.steps * dt, a.norm_smooth))
    else:
        P('dt=%.4e s（标称 %.2f nm/步）；%d 步 ⇒ t_sim=%.3e s；norm_smooth=%d'
          % (dt, 0.15 * dx * 1e9, a.steps, a.steps * dt, a.norm_smooth))
    P('-' * 104)

    if a.dry_run:
        mm = BM.measure_state(g.region(), dx, n_hab, w_ax, a_ax, vmap)
        P('--dry-run：初始测量 ' + json.dumps(
            {k: (round(v, 6) if isinstance(v, float) else v)
             for k, v in mm.items()}, ensure_ascii=False))
        return 0

    csvf = open(os.path.join(outdir, 'series.csv'), 'w', newline='')
    cw = csv.writer(csvf); cw.writerow(COLS)
    with open(os.path.join(outdir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(arm=a.arm, tag=tag, N=N, L=L, dx_nm=dx * 1e9, steps=a.steps,
                       laths=laths_eff, nv=nv, vmap=vmap,
                       omega_max_deg=a.omega_max_deg, omega_mode=a.omega_mode,
                       theta_deg={('%d-%d' % (i + 1, j + 1)):
                                  float(np.degrees(lt.theta[i + 1, j + 1]))
                                  for i in range(nv) for j in range(i + 1, nv)},
                       gamma_RS={('%d-%d' % (i + 1, j + 1)):
                                 (float(lt.gtab[i + 1, j + 1])
                                  if np.isfinite(lt.gtab[i + 1, j + 1]) else None)
                                 for i in range(nv) for j in range(i + 1, nv)},
                       plate=dict(L=a.plate_L, W=a.plate_W, T=a.plate_T),
                       gap_nm=a.gap_nm, norm_smooth=a.norm_smooth,
                       beta_h=a.beta_h, beta_w=a.beta_w, adv=a.adv,
                       reinit_band=a.reinit_band, nthreads=a.nthreads,
                       # ★★ 2026-09-29 补：这几个**决定这次跑的到底是什么**的开关
                       # 原先**没写进 meta.json**（`reinit_dt` / `grow_stack` /
                       # `nuc_every` / `nuc_gap_nm` / `phi_every`），
                       # 直接违反用户「全过程数据要能事后重测」的要求：
                       # 光看 meta 无法判断一个臂是"预装 6 根"还是"长出来的"。
                       # 除了逐个列出，还整份 dump `vars(a)`（argparse 命名空间），
                       # **今后任何新增的 CLI 开关都会自动进 meta**，不再依赖记得加。
                       reinit_dt=a.reinit_dt, reinit_every=0,
                       grow_stack=bool(a.grow_stack), nuc_every=a.nuc_every,
                       nuc_gap_nm=a.nuc_gap_nm, phi_every=a.phi_every,
                       nuc_overlap_nm=a.nuc_overlap_nm,
                       nuc_compensate=bool(a.nuc_compensate),
                       snap_every=a.snap_every, every=a.every,
                       out_root=a.out, exp_args=vars(a),
                       gamma0=a.gamma0, DF=DF, Mob=MOB, dt=dt, t_sim=a.steps * dt,
                       df_const=(None if _athermal else float(DF)),
                       df_start=(float(_df_start) if _athermal else None),
                       n_hab=n_hab.tolist(), w_ax=w_ax.tolist(), a_ax=a_ax.tolist(),
                       sha_windowB_surface=sha256(os.path.join(_HERE, 'windowB_surface.py')),
                       sha_windowB_lath=sha256(os.path.join(_HERE, 'windowB_lath.py')),
                       sha_windowB_par=sha256(os.path.join(_HERE, 'windowB_par.py')),
                       sha_exp=sha256(os.path.abspath(__file__)),
                       sha_measure=sha256(os.path.join(_HERE, '_bk_measure.py')),
                       git=subprocess_out(['git', '-C', os.path.dirname(
                           os.path.dirname(_HERE)), 'rev-parse', 'HEAD'])),
                  f, ensure_ascii=False, indent=1)

    P0, t_sim, wall0, tstep = None, 0.0, time.time(), []
    nfail = 0
    # ★★★ R29：athermal 钟的逐步状态（`--nuc-law cadence` 下**全部不参与**）
    n_ath_ev = 0                 # 由 athermal 律触发的形核次数
    n_ath_tgt = 0                # 当前的累计目标根数（不含预摆的第 1 片）
    T_hist = []                  # 每次事件时的 (step, t, T, df)
    if _athermal:
        # 预摆的第 1 片视为"在 M_s 处形核" ⇒ 累计计数从 1 起算
        n_ath_tgt = 1
    for it in range(0, a.steps + 1):
        if it > 0:
            tw = time.time()
            if _athermal:
                # ★ 钟：先走时间、再把 T 换成驱动力，然后才推进几何。
                #   （语义与 `LevelSetMulti.advance_T` 一致；这里显式写开是为了
                #     让 `dt` 能按**当前** ΔG_v 自适应 —— 降温 ⇒ ΔG_v 涨 ⇒ dt 变小。）
                g.t += dt
                g.set_T(g.T_of_t(g.t))
                _df_now = float(g.df[1])
                dt = 0.15 * dx / (MOB * max(_df_now, 1e-300))
            g.advance(dt, **kw)
            tstep.append(time.time() - tw)
            t_sim += dt
            if not np.all(np.isfinite(g.phi)):
                P('✗✗ `phi` 非有限 @ step %d —— 立即中止并**保留现场**' % it)
                np.savez_compressed(os.path.join(outdir, 'CRASH_phi.npz'),
                                    phi=g.phi, step=it)
                nfail = 4
                break
        # ★★★ G-1 方案 B：**生长中的邻位形核**（在推进之前播下一片）
        if grow and a.nuc_every > 0 and it > 0 and (it % a.nuc_every == 0):
            _j = _seed_next()
            if _j is not None:
                P('   ★★ 形核事件 @ step %d：新核进入**新场 %d**（变体 %d）'
                  % (it, _j, laths_eff[_j - 1]))
        # ★★★ R12：**引擎侧自发形核**（`--arm eng`）。与上面 `_seed_next` 的区别：
        #   `_seed_next` 由**驱动层**决定"哪一步、放在哪、进哪个场"；
        #   这里把**位置与场的选择**交给引擎的 `nucleate()`（`attach` + `nfsv`），
        #   驱动层只保留**节奏**（`--eng-cadence`；0 = 每步都问一次）。
        #   ⇒ 记账：**速率仍然是被规定的** —— 引擎的 sympathetic 通道目前
        #     **没有速率律**（`use_fcrit` 只覆盖 `fresh` 通道）。这一点不得含糊。
        if use_engine and it > 0 and a.eng_cadence >= 0 and not _athermal:
            if a.eng_cadence == 0 or (it % a.eng_cadence == 0):
                _reg_e = g.region()
                _fnow = 1.0 - float((_reg_e == 0).sum()) / g.N ** 3
                _ev = g.nucleate(_ed_dummy if _ed_dummy is not None
                                 else g.elastic_driving(),
                                 f_now=_fnow, n_fresh=0, n_stack=1)
                n_eng_ev += len(_ev)
                if _ev:
                    _kk = _ev[0][0]
                    P('   ★★ **引擎形核** @ step %d：场 %d，模式 %s（累计 %d 次）'
                      % (it, _kk, _ev[0][1], n_eng_ev))
        # ★★★ R29：**athermal 律触发的形核**（`--nuc-law athermal`）。
        #   判据不是"第几步"，而是**累计核数**：
        #       `n_target(T) = floor(α_KM·(M_s − T))`，`T = T_of_t(t)`。
        #   ⇒ 事件出现在 `T_k = M_s − k/α_KM`，与步数无关 ⇒ **速率由物理给出**。
        #   ⚠ 与 `cadence` 路径**互斥**（上面那条已加 `not _athermal`）⇒ 默认逐位不变。
        if _athermal and use_engine and it > 0:
            _Tnow = float(g.T)
            _tgt = min(int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12)), nv)
            while n_ath_tgt < _tgt and n_ath_tgt < nv:
                _reg_e = g.region()
                _fnow = 1.0 - float((_reg_e == 0).sum()) / g.N ** 3
                _ev = g.nucleate(_ed_dummy if _ed_dummy is not None
                                 else g.elastic_driving(),
                                 f_now=_fnow, n_fresh=0, n_stack=1)
                n_ath_tgt += 1
                if _ev:
                    n_eng_ev += len(_ev)
                    n_ath_ev += 1
                    T_hist.append(dict(step=it, t=float(g.t), T=_Tnow,
                                       df=float(g.df[1]), field=int(_ev[0][0]),
                                       n_target=int(_tgt), k=int(n_ath_tgt)))
                    P('   ★★ **athermal 形核** @ step %d：T=%.1f K（T_%d 理论=%.1f K）'
                      '，df=%.4e，场 %d（累计 %d/%d）'
                      % (it, _Tnow, n_ath_tgt, CL.T_of_k(n_ath_tgt, _alpha),
                         float(g.df[1]), _ev[0][0], n_ath_tgt, _n_law))
                else:
                    P('   ⚠ athermal 事件 #%d 被引擎拒（无可用空场/落位失败）@ step %d'
                      % (n_ath_tgt, it))
        if (it % a.every) and (it != a.steps):
            continue
        reg = g.region()
        mm = BM.measure_state(reg, dx, n_hab, w_ax, a_ax, vmap)
        # ψ 的带（只在 F3 胞上；`g.psi is None` 时不算）
        if g.psi is not None:
            karr_m, larr_m = g.par.argmin2(g.phi)
            karr_m = karr_m.astype(np.intp); larr_m = larr_m.astype(np.intp)
        else:
            karr_m = larr_m = None
        pm = mm['f3_pos_n']
        if P0 is None and np.isfinite(pm):
            P0 = pm
        nc = [mm['ncomp_%d' % k] for k in range(1, nv + 1)]
        ncb = [mm['ncompbig_%d' % k] for k in range(1, nv + 1)]
        # ★★ Round 10 修：中位数**必须只统计非空场**。
        #   原写法对**所有** `k=1..nv` 取中位数，而生长臂早期大部分场是空的
        #   （`n_k = 0`）⇒ 中位数被 0 绑架。实测 `dry_gs3` 在 step 0–50 打出
        #   `n/w/a=0/0/0 nm`（那时明明有 1–2 根 250/619/2400 nm 的板条），
        #   到 step 60 又跳成 124 —— 全是空场把中位数拉到 0 的假象。
        #   ⇒ 只对 `vol_k > 0` 的场取中位数；全空则给 0（`vols` 列可辨）。
        _occ = [k for k in range(1, nv + 1) if mm['vol_%d' % k] > 0]
        _med = (lambda f: float(np.median([f(k) for k in _occ])) if _occ else 0.0)

        # ★ R18：逐对 F3 面积（只在命中 `--pair-every` 时算）
        _pair_now = bool(a.pair_every > 0 and it % a.pair_every == 0)

        def _pair_str(reg_, mm_):
            out_ = []
            for _ii, _i in enumerate(_occ):
                for _j in _occ[_ii + 1:]:
                    if vmap[_i] != vmap[_j]:
                        continue
                    _A = BM._area_from_faces(
                        BM._faces_between(reg_ == _i, reg_ == _j), n_hab, dx)
                    if _A > 0:
                        out_.append('%d-%d:%.6g' % (_i, _j, _A * 1e12))
            return '/'.join(out_)

        row = dict(
            step=it, t_s=round(t_sim, 12), wall_s=round(time.time() - wall0, 2),
            dt=dt, V0=mm['vol_0'], Vt=sum(mm['vol_%d' % k] for k in range(1, nv + 1)),
            M=M, nreg_used=mm['nreg_used'], nslab_n=mm['nslab_n'],
            nf3_col=mm['nf3_col'], runs=mm['runs'].replace(',', '/'),
            ncomp_min=int(np.min(nc)), ncomp_max=int(np.max(nc)),
            # ★ 显著分量数（≥32 体素）：`ncomp_max` 会把 1–2 体素的离散孤儿算成
            #   "碎裂"（`dry_gs2` 实测 ncomp_max=4，实际是 1 根完整板条 + 3 个孤儿）。
            #   两个口径**都存**，判决用新的、原始值留档，任何人都能自己重判。
            ncompbig_max=int(np.max(ncb)),
            vols='/'.join('%.6g' % (mm['vol_%d' % k] * 1e18)
                          for k in range(1, nv + 1)),
            ths='/'.join('%.6g' % (mm['n_%d' % k] * 1e9)
                         for k in range(1, nv + 1)),
            # ★ R18：逐对 F3 面积。只在 `--pair-every` 命中时算（它要按对做
            #   6 次 `np.roll`，N=96 时约 2–3 s ⇒ 不能每步都算）。
            f3_pairs=('' if not _pair_now else _pair_str(reg, mm)),
            nf3=mm['f3_faces'], f3_area_m2=mm['f3_area'],
            f3_area_stair=mm['f3_area_stair'], f3_pos_m=pm,
            f3_pos_dx=((pm - P0) / dx if (np.isfinite(pm) and P0 is not None)
                       else float('nan')),
            f3_std_m=mm['f3_std_n'],
            # ★★ Round 10 修：中位数**必须只统计非空场**（见上面 `_occ` 的记账）。
            n_lath=_med(lambda k: mm['n_%d' % k]),
            w_lath=_med(lambda k: mm['w_%d' % k]),
            a_lath=_med(lambda k: mm['a_%d' % k]),
            box_touch=int(mm['box_touch']),
            finite=int(np.all(np.isfinite(g.phi))),
            psi_mean=(float(g.psi[np.isfinite(
                lt.gtab[np.clip(karr_m, 0, g.nreg - 1),
                        np.clip(larr_m, 0, g.nreg - 1)])].mean())
                if (g.psi is not None) else float('nan')))
        # ★ 防御：`cw.writerow([row[c] for c in COLS])` 里少一个键就是 KeyError，
        #   而它出现在**第 0 步写第一行**时 —— 那时构造已经花掉 60 s，
        #   且发生在长跑开头而不是起跑前。这里提前硬失败，把话说明白。
        _miss = [c for c in COLS if c not in row]
        if _miss:
            raise KeyError('series.csv 的 COLS 与 row 不一致，row 里缺: %s' % _miss)
        cw.writerow([row[c] for c in COLS]); csvf.flush()
        if (it % a.snap_every == 0) or (it == a.steps):
            # ★★ 落盘策略（用户要求"全过程数据留 F 盘，量具有 bug 也能事后重测"）：
            #   · **`region`（int8, 7 MB）每个快照都存** —— 这是
            #     `_bk_measure.measure_state` 的**唯一输入**（体积/分量/nslab/nf3col/
            #     三轴尺寸/面积/位置全都只吃它）⇒ **量具可完全事后重测**。
            #   · **`phi`（7×28 MB float32）按 `--phi-every` 单独控制** ——
            #     只有"曲率/界面形状"这类测量需要它，而 `savez_compressed` 压 198 MB
            #     实测要 ~60 s（是单步耗时的可见一部分）。
            #   · 默认 `--phi-every 0` = 与 `snap_every` 相同 ⇒ **行为与改动前一致**。
            d = dict(region=reg, step=it, n_hab=n_hab, w_ax=w_ax, a_ax=a_ax,
                     N=N, L=L, arm=a.arm,
                     vmap_keys=np.array(sorted(vmap)),
                     vmap_vals=np.array([vmap[k] for k in sorted(vmap)]))
            if a.phi_every > 0 and (it % a.phi_every == 0 or it == a.steps):
                d['phi'] = g.phi.astype(np.float32)
            np.savez_compressed(os.path.join(outdir, 'snap_%05d.npz' % it), **d)
        P('  [%4d] Vt=%.4f µm³ | **nslab=%d** nf3col=%d runs=%-13s | F3面=%-6d '
          '面积=%.4f µm² | Δpos=%+7.3f dx std=%5.1f nm | nc=%d..%d(显著%d) | '
          '厚度(在位的场) %s nm | 壁=%d | %.2fs/步'
          % (it, row['Vt'] * 1e18, mm['nslab_n'], mm['nf3_col'], row['runs'],
             mm['f3_faces'], mm['f3_area'] * 1e12,
             (row['f3_pos_dx'] if np.isfinite(row['f3_pos_dx']) else float('nan')),
             (mm['f3_std_n'] * 1e9 if np.isfinite(mm['f3_std_n']) else float('nan')),
             row['ncomp_min'], row['ncomp_max'], row['ncompbig_max'],
             ' '.join('%d:%.0f' % (k, mm['n_%d' % k] * 1e9)
                      for k in range(1, nv + 1) if mm['vol_%d' % k] > 0)
             or '（无）',
             row['box_touch'],
             (np.mean(tstep[-a.every:]) if tstep else 0.0)))
    csvf.close()

    # ★★★ R15：把**形核通道的诊断计数落盘**。原先 `g._nuc['dbg']` 只在内存里，
    #   于是"`nfsv` 到底有没有因为没空场而拒绝事件"这类判据（本轮预登记的 G-5）
    #   **无法从落盘数据复核** —— 而用户的要求正是"全过程数据留盘、量具/判据
    #   有 bug 也能事后重测"。⇒ 写成 `nuc_dbg.json`（只在 `arm=eng` 时）。
    if use_engine and getattr(g, '_nuc', None) is not None:
        try:
            with open(os.path.join(outdir, 'nuc_dbg.json'), 'w',
                      encoding='utf-8') as f:
                json.dump(dict(n_eng_ev=n_eng_ev,
                               nuc_law=a.nuc_law,
                               n_athermal_ev=n_ath_ev,
                               n_target_final=n_ath_tgt,
                               T_events=T_hist,
                               n_events_by_mode={
                                   m: sum(1 for _k, mm in g._nuc_events if mm == m)
                                   for m in sorted(set(mm for _k, mm
                                                       in g._nuc_events))},
                               dbg={k: int(v) for k, v in
                                    g._nuc.get('dbg', {}).items()},
                               nuc_cfg={k: (v if not isinstance(v, np.ndarray)
                                            else v.tolist())
                                        for k, v in g._nuc.items()
                                        if k not in ('rng', 'dbg')}),
                          f, ensure_ascii=False, indent=1)
            P('★ 形核诊断已落盘: nuc_dbg.json（n_eng_ev=%d, dbg=%s）'
              % (n_eng_ev, g._nuc.get('dbg', {})))
        except Exception as exc:                                # pragma: no cover
            P('⚠ nuc_dbg.json 落盘失败（不影响仿真结果）: %s' % exc)

    # ★★★ R29：把**这一次到底用了哪些闭环参数**整份落盘（`closure.json`）。
    #   用户的硬要求是"全过程数据留盘、量具/判据有 bug 也能事后重测"。
    #   `--nuc-law cadence`（默认）时只写 `nuc_law` 一个字段，**不改任何归档产物**。
    try:
        _rec = CL.recommend(N=N, t_lath_nm=float(a.plate_T),
                            aspect=float(a.plate_L) / float(a.plate_T),
                            alpha_KM=_alpha, T_f=_Tend, MOB=MOB, cfl=0.15,
                            ratio_target=float(a.cool_ratio))
        _cl = dict(nuc_law=a.nuc_law,
                   alpha_KM=_alpha,
                   Ms=float(M_S_TI64), T0=float(T0_TI64), DS=float(DS_REF),
                   dG_crit=float(DG_CRIT_REF),
                   T_start=_Tstart, T_end=_Tend,
                   T_start_kind=('T_1 = M_s − 1/α_KM（预摆片 = 第 1 根）'
                                 if float(a.T_start) <= 0 else 'user'),
                   q=(None if not _athermal else float(_q)),
                   q_source=_q_source,
                   q_cap=(None if not _athermal else float(_q_cap)),
                   n_law_float=CL.alpha_km_n_lath(_Tend, _alpha),
                   n_law=int(_n_law),
                   T_k=[float(CL.T_of_k(k, _alpha)) for k in range(1, max(_n_law, 1) + 1)],
                   steps_min_ordered=CL.steps_min_ordered(_alpha, _L_lath, dx, 0.15,
                                                          _Tend, _Tstart),
                   beta_h_floor=CL.beta_h_min(a.steps, dx, a.plate_T * 1e-9),
                   beta_h_T=CL.beta_h_of_T(0.5 * (float(M_S_TI64) + _Tend)),
                   beta_h_used=float(a.beta_h),
                   geometry=dict(N=N, dx_nm=dx * 1e9, L_box=dx * N,
                                 plate_L_nm=a.plate_L, plate_W_nm=a.plate_W,
                                 plate_T_nm=a.plate_T,
                                 t_over_dx=float(a.plate_T) * 1e-9 / dx),
                   params=CL.params())
        _cl['n_lath_derived'] = dict(L_lath_um=_rec.get('L_lath', 0) * 1e6,
                                     W_lath_um=_rec.get('W_lath', 0) * 1e6,
                                     dx_nm_rec=_rec.get('dx_nm'),
                                     q_rec=_rec.get('q'),
                                     steps_rec=_rec.get('steps'),
                                     beta_h_rec=_rec.get('beta_h_use'),
                                     n_geo_cap=_rec.get('n_geo_cap'),
                                     ordered_ratio=_rec.get('ordered_ratio'),
                                     ok=_rec.get('ok'))
        with open(os.path.join(outdir, 'closure.json'), 'w', encoding='utf-8') as f:
            json.dump(_cl, f, ensure_ascii=False, indent=1)
        P('★ 闭环参数已落盘: closure.json（nuc_law=%s, α_KM=%.4e, q=%s, n=%d）'
          % (a.nuc_law, _alpha,
             ('%.4e' % _q) if _athermal else 'n/a', _n_law))
    except Exception as exc:                                    # pragma: no cover
        P('⚠ closure.json 落盘失败（不影响仿真结果）: %s' % exc)

    s = read_series(os.path.join(outdir, 'series.csv'))
    P('-' * 104)
    P('判决 臂=%-5s  M=%d  nslab_n %d→%d（应 == M=%d）  nf3_col %d→%d  '
      'F3 面积 %.4f→%.4f µm²  Δpos %s dx  nc_max %d→%d（显著 %s）'
      % (a.arm, M, s['nslab_n'][0], s['nslab_n'][-1], M, s['nf3_col'][0],
         s['nf3_col'][-1], s['f3_area_m2'][0] * 1e12, s['f3_area_m2'][-1] * 1e12,
         ('%+.3f' % s['f3_pos_dx'][-1]) if np.isfinite(s['f3_pos_dx'][-1]) else 'NaN',
         s['ncomp_max'][0], s['ncomp_max'][-1],
         ('%d→%d' % (s['ncompbig_max'][0], s['ncompbig_max'][-1]))
         if 'ncompbig_max' in s else '本臂无此列（旧版跑的数据）'))
    if a.arm == 'gneg':
        P('  负对照判据：**nf3 必须恒为 0** ⇒ 实测 %d→%d  %s'
          % (s['nf3'][0], s['nf3'][-1],
             '✓' if (s['nf3'][0] == 0 and s['nf3'][-1] == 0) else '✗✗ 量具失效'))
    else:
        P('  主判据：**nslab_n == M** 且 **nf3_col == M-1**（低角晶界把每根都分开）'
          ' ⇒ %s' % ('✓' if (s['nslab_n'][-1] == M and s['nf3_col'][-1] == M - 1)
                     else '✗ 见逐步读数'))
    return nfail


def subprocess_out(cmd):
    import subprocess
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    except Exception:
        return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', default='dry',
                    choices=['dry', 'wet', 'gpos', 'gneg', 'g0', 'auto', 'eng'])
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--dx-nm', type=float, default=62.5)
    ap.add_argument('--steps', type=int, default=400)
    ap.add_argument('--every', type=int, default=10)
    ap.add_argument('--snap-every', type=int, default=100)
    ap.add_argument('--phi-every', type=int, default=0,
                    help='存 phi 的间隔；0 = 与 snap-every 相同（region 每次都存）')
    ap.add_argument('--laths', default='1,1,1,1,1,1')
    ap.add_argument('--omega-max-deg', type=float, default=5.0)
    ap.add_argument('--omega-mode', default='ladder', choices=['ladder', 'random'])
    ap.add_argument('--plate-L', type=float, default=2400.0)
    ap.add_argument('--plate-W', type=float, default=640.0)
    ap.add_argument('--plate-T', type=float, default=250.0)
    ap.add_argument('--gap-nm', type=float, default=0.0)
    ap.add_argument('--grow-stack', action='store_true',
                    help='★ G-1 方案 B：t=0 只播第 1 片，此后每 --nuc-every 步'
                         '在当前块外侧播下一片（同变体、新场）⇒ 生长中堆叠成块')
    # ★★★ R28：**默认 0 = 形核交给引擎**（新默认）。
    #   要复现归档的**驱动层**行为，显式传 `--nuc-every 30`。
    #   **归档命令行全部显式传了 30**（见各臂 `meta.json` 的 `exp_args`）
    #   ⇒ 它们的行为**逐位不变**。
    ap.add_argument('--nuc-every', type=int, default=0)
    ap.add_argument('--nuc-gap-nm', type=float, default=0.0)
    # ★ Round 9：新核**咬进**已有块的深度（nm）。0 = 恰好相切（旧行为，
    #   实测会因阶梯错位留 1 胞 β 膜 ⇒ F3 覆盖率只有 0.62）。
    #   物理上"在界面上形核"就是共用一张界面 ⇒ 用一个正的重叠量。
    #   建议值 ≥ 1.5Δx（Δx=62.5 nm ⇒ 94 nm），保证中面离两侧零集都够远。
    ap.add_argument('--nuc-overlap-nm', type=float, default=0.0)
    # ★ Round 10：把会被"咬"掉的厚度预先补上（见 `_seed_next` 的记账）。
    #   只在 `--nuc-overlap-nm > 0` 时有意义。
    ap.add_argument('--nuc-compensate', action='store_true')
    # ★★★ R12：`--arm eng` —— 引擎侧自发形核
    ap.add_argument('--eng-cadence', type=int, default=30,
                    help='引擎形核的**节奏**（步）；0 = 每步都问一次引擎')
    ap.add_argument('--eng-r-nm', type=float, default=320.0)
    ap.add_argument('--eng-t-nm', type=float, default=250.0)
    # ★★★ R28：**形核通道选择**。
    #   `auto`（默认）：`--grow-stack` 且 `--nuc-every <= 0` ⇒ **引擎**；
    #                     给了 `--nuc-every > 0` ⇒ **驱动层**。
    #   ⇒ **所有归档命令行都带 `--nuc-every 30` ⇒ 逐位不变**；
    #     而「只给 `--grow-stack`」这一新写法自动拿到**已验的引擎路径**。
    ap.add_argument('--nuc-mode', default='auto',
                    choices=['auto', 'driver', 'engine'])
    ap.add_argument('--eng-seed', type=int, default=11)
    # ★ R22：关掉"有事件就强制 reinit"（**R23 起改为引擎自动**：attach 下默认关）。
    ap.add_argument('--eng-no-force-reinit', action='store_true',
                    help='（R22 遗留，已由引擎自动决定取代；保留以免旧命令行失效）')
    # ★ R23：末片减薄（对齐驱动层 `_seed_next` 的 `T+o/2`）。默认 0 = 不减薄。
    ap.add_argument('--eng-t-last-reduce-nm', type=float, default=0.0)
    ap.add_argument('--eng-force-reinit', action='store_true',
                    help='强制打开事件后 reinit（用于复现 eng5..eng10）')
    # ★ R18：逐对 F3 面积记录间隔（步）。0 = 不记（默认，与改动前逐位相同）。
    ap.add_argument('--pair-every', type=int, default=0)
    # ★★★ R12：**核的形状**。默认 0 ⇒ 圆盘（= 引擎原行为）。
    #   实测（`--arm eng`，R=320、200 步）圆盘给出的第一次接触面只有 0.39 µm²，
    #   而驱动层的长条板条给 1.5174 µm² ⇒ 终态 F3 面积差 **7 倍**。
    #   传 `--eng-elong 3.75` 即恢复 `L/W = 2400/640` 的长条（沿 `a` 轴）。
    ap.add_argument('--eng-elong', type=float, default=0.0,
                    help='0 = 圆盘（引擎原行为）；>1 = 长条核（沿用 a 轴）')
    # ★★★ R29：**F1/F2 的标量面能**（原先硬编码 0.15）。加这个开关的理由：
    #   闭环要求把 `γ_α′β` 从 [占位] 0.15 换成文献值（Murzinova 2017 给
    #   0.201–0.337 @975 °C、0.298–0.429 @600 °C）⇒ 必须能**单变量**地扫它。
    #   默认 0.15 ⇒ **全部归档读数逐位不变**。
    ap.add_argument('--gamma0', type=float, default=0.15,
                    help='F1/F2 标量面能 [J/m²]；F3 仍走 Read–Shockley γ_RS(θ)')
    # ★★★ R29（2026-10-01）：**形核律**。用户要求"用形核率之类的方式让模型合理运转"。
    #   `cadence`（默认）：`--eng-cadence` 规定的节奏 ⇒ **与全部归档读数逐位相同**。
    #   `athermal`：由 `windowB_closure` 的 C-2/C-3 闭式驱动 ——
    #       ① 钟：`T(t) = M_s − q·t`（`windowB_km.linear_cool`），
    #          驱动力 `df(T) = drive_of_T(T; T0, DS)`（引擎的 `set_T`，T6 已接线）；
    #       ② 板条数：`n(T) = α_KM·(M_s − T)`（C-2，位置饱和律；`A_0 ≡ A_f` 由
    #          引擎几何本身给出）⇒ **`n` 从"规定的 6"变成导出量**；
    #          第 k 根在 `T_k = M_s − k/α_KM` 出现；
    #       ③ 步长：`dt = cfl·dx/(MOB·ΔG_v(T))` ⇒ 随降温自动变小；
    #       ④ 停止：`n` 达到 `floor(α_KM·(M_s − T_end))` 或步数用尽。
    #   ⚠ 记账：`q` 由 C-3 的**有序性上界** `q ≤ MOB·ΔG_crit/(α_KM·L_lath)` 乘安全系数定，
    #     不是自由参数；`--cool-rate` 给了就显式检查它是否越界。
    ap.add_argument('--nuc-law', default='cadence',
                    choices=['cadence', 'athermal'])
    ap.add_argument('--alpha-km', type=float, default=ALPHA_KM_REF,
                    help='athermal 位置饱和律的系数 [1/K]（唯一待标定常数）')
    ap.add_argument('--cool-rate', type=float, default=0.0,
                    help='athermal 钟的冷速 [K/s]；0 = 由 C-3 的有序性上界自动定')
    ap.add_argument('--cool-ratio', type=float, default=0.8,
                    help='athermal 钟：有序比目标（Δt_grow/Δt_nuc），<1 才有安全余量')
    ap.add_argument('--T-start', type=float, default=0.0, help='0 = 用 M_s')
    ap.add_argument('--T-end', type=float, default=298.0)
    # ★★ Round 10 实测更正：`--nuc-compensate` 用**名义** `o` 补，而**补过头了**。
    #   证据（同配置三点）：
    #     `gs4`（不补）   厚度 238/238/239/230/254/250（均值 241.5，−3.4%）Vt 2.1062
    #     `gs5`（补 o）   厚度 261/289/303/285/314/282（均值 289，**+15.6%**）Vt 2.6897
    #   原因：实际重叠**小于**名义 `o` —— `edge` 是**格心**投影，本来就落在真实
    #   α′ 边界**内侧**最多约 `0.5·max|n_i|·Δx ≈ 40 nm`；`_bk_pair.py` 实测的
    #   投影间隙只有 −2…−69 nm（均值 ≈ −28 nm），远小于 62.5。
    #   ⇒ 加这个系数：`T_j = T + frac·o`。`frac=1.0` ⇒ **与 `gs5` 逐位相同**。
    ap.add_argument('--nuc-compensate-frac', type=float, default=1.0)
    ap.add_argument('--norm-smooth', type=int, default=0)
    ap.add_argument('--beta-h', type=float, default=3.5)
    ap.add_argument('--beta-w', type=float, default=2.3)
    ap.add_argument('--facet-lam', type=float, default=0.0)
    ap.add_argument('--facet-eps', type=float, default=0.05)
    ap.add_argument('--adv', default='proj2')
    ap.add_argument('--reinit-band', type=float, default=6.0)
    ap.add_argument('--reinit-dt', type=float, default=6.0e-7,
                    help='重初始化间隔（秒）。**默认 6e-7 是生产值**；'
                         '诊断时给大值（如 1e-4）≈ 关掉 reinit')
    ap.add_argument('--nthreads', type=int, default=4)
    ap.add_argument('--gamma-film', type=float, default=0.6)
    ap.add_argument('--out', default='_exp/_bk_block')
    ap.add_argument('--tag', default='')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    return run(a)


if __name__ == '__main__':
    raise SystemExit(main())
