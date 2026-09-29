#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_selfac_struct.py —— **自协调的群级（block/colony 级）结构**：从 12 个 Burgers 变体
的转变应变张量**直接算出**「哪些变体组合能自协调、最少要几个」的全表。

## 为什么需要它（R30，目标第 (2) 项）

已有的框架文档覆盖的是**块内**（同类板条 + 低角晶界，`BLOCK_DERIVATION.md`）与
**配对级**相容性（`R1_PAIR_CRITERION.md`：66 对的 `E_min` 与经典几何判据）。
**缺的是群级**：「马氏体板条堆叠形成的块之间相互影响与协调产生的组织」——
即**若干个变体构成一个自协调组**（self-accommodating group）的条件与最小规模。
本脚本只做**纯晶体学/连续介质力学**的推导与穷举，不碰引擎、不跑仿真。

## 判据的物理定义（先写死，不得事后挪动）

**A. 经典自协调判据（宏观形状应变）**
变体 i 的应力自由转变应变 @@\\boldsymbol\\varepsilon^0_i@@（小应变，`eps0 = sym(F) − I`）。
一组变体 G 配体积分数 @@f_i\\ge0,\\ \\sum f_i=1@@ 时，宏观形状应变为
@@\\bar\\varepsilon(G)=\\sum_{i\\in G} f_i\\,\\boldsymbol\\varepsilon^0_i@@。

* 体积（迹）部分 **不可能** 被抵消：所有变体的 `tr ε⁰` 相同（贝恩畸变的体积项）
  ⇒ 判据只能加在**偏量**上：@@\\bar e=\\sum f_i\\,\\mathrm{dev}\\,\\boldsymbol\\varepsilon^0_i@@
* **自协调残差** @@r(G)=\\min_{f}\\lVert\\bar e\\rVert_F \\Big/ \\overline{\\lVert\\mathrm{dev}\\varepsilon^0\\rVert_F}@@
  ⇒ @@r=0@@ 即"这一组可以完全自协调"。

**B. 相容对（共格界面）判据**
两变体的界面能共格（不变平面 / 位移型）⟺ @@\\Delta\\boldsymbol\\varepsilon=\\boldsymbol\\varepsilon^0_k-\\boldsymbol\\varepsilon^0_l@@
有不变平面 ⟺ `det Δε = 0`（在 `tr Δε = 0` 时等价于中间特征值 @@\\lambda_2=0@@）。
本仓库已有一版更细的判据：**模型自己的各向异性微弹性能**
@@E_{\\min}(k,l)=\\min_{\\mathbf n}\\tfrac12\\Delta\\boldsymbol\\varepsilon:\\Lambda(C,\\mathbf n):\\Delta\\boldsymbol\\varepsilon@@
（`R1_PAIR_CRITERION.md` §1；代码 `windowB_pf3d.argmin_normal`）。
本脚本**两个都算**并给出它们的一致性。

**C. 群级"共格连通"**
把"相容对"当边 ⇒ 图 @@\\mathcal G@@。**全共格团**（clique）就是"组内任意两两都能共格"的
变体集合 —— 这是最强的一档自协调（所有界面都是不变平面）。

## ⚠ 仪器口径（本仓库最贵的教训：先问"我怎么证伪它"）

1. **必须做正对照**：`windowB_ti64_variants.variants()` 自带的 **C4** 判据
   「12 个 `dev(eps0)` 之和 = 0」要在这里**独立重算**并报告残差 —— 它是"全 12 变体自协调"
   的已知答案。若本脚本的 `r({1..12})` 不是 ~0，说明本脚本的偏量/范数口径错了。
2. **必须做分辨力对照**：把 12 个变体**随机重标号/随机替换成"人为扰动过的张量"**，
   看 `r` 会不会跟着变（若不变 ⇒ 判据对这组数据没有分辨力）。
3. 单位/量纲：`eps0` 无量纲；`r` 无量纲。

跑法：  python3 _r30_selfac_struct.py
        python3 _r30_selfac_struct.py --maxk 6 --tol 1e-6
"""
import os
import sys
import json
import argparse
import itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

try:
    from windowB_pf3d import C_cubic, argmin_normal
    _HAVE_C = True
except Exception:                                               # pragma: no cover
    _HAVE_C = False


def dev(A):
    return A - np.trace(A) / 3.0 * np.eye(3)


def fro(A):
    return float(np.sqrt(np.sum(np.asarray(A, float) ** 2)))


def proj_simplex(v):
    """**欧氏**投影到单纯形 {f ≥ 0, Σ f = 1}（Duchi 2008 的排序算法）。

    ⚠ 本函数是 **R30 自我更正**的产物：第一版用的是"把负数截到 0 再归一化"，
    那是**非正交**投影 ⇒ 投影梯度法**没有收敛保证**。
    `_r30_selfac_check.py` 的独立路线（SLSQP + 单纯形随机采样）实测：
    40 个子集里有 **17 个** SLSQP 给出更低的值、最大相对差 **1.01e-01**
    ⇒ 第一版对很多子集**没收敛**（把 `r` 高估最多 10%）。
    ★ 结论本身（`k*=6`、64 个六元组）经独立路线复算**不受影响**（见该脚本输出），
      但**逐子集的 `r` 数值**必须用本修正版本重新生成。
    """
    v = np.asarray(v, float)
    n = v.size
    u = np.sort(v)[::-1]
    css = np.cumsum(u) - 1.0
    ind = np.arange(1, n + 1)
    cond = u - css / ind > 0
    rho = int(np.nonzero(cond)[0][-1])
    theta = css[rho] / (rho + 1.0)
    return np.maximum(v - theta, 0.0)


def min_residual(E, idx):
    """在单纯形上最小化 ‖Σ f_i e_i‖_F（f ≥ 0, Σ f = 1）。返回 (r, f)。

    用**正确的**欧氏单纯形投影 + 投影梯度（L = 2·‖AAᵀ‖₂ 是 ∇f 的 Lipschitz 常数）。
    独立复核见 `_r30_selfac_check.py`（SLSQP + 单纯形随机采样两条不共用代码的路线）。
    """
    A = np.stack([E[i] for i in idx], 0).reshape(len(idx), -1)   # (k, 9)
    k = len(idx)

    def obj(f):
        return float(np.sum((f @ A) ** 2))

    def grad(f):
        return 2.0 * (A @ (A.T @ f))

    L = 2.0 * float(np.linalg.norm(A @ A.T, 2)) + 1e-30
    # 多起点（单纯形顶点 + 均匀点）避免停在退化点
    starts = [np.full(k, 1.0 / k)]
    for i in range(min(k, 4)):
        e = np.zeros(k)
        e[i] = 1.0
        starts.append(e)
    best_f, best_v = None, np.inf
    for f in starts:
        f = f.astype(float)
        for _ in range(20000):
            f2 = proj_simplex(f - grad(f) / L)
            if np.max(np.abs(f2 - f)) < 1e-16:
                f = f2
                break
            f = f2
        v = obj(f)
        if v < best_v:
            best_v, best_f = v, f
    return float(np.sqrt(max(best_v, 0.0))), best_f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maxk', type=int, default=6,
                    help='穷举的最大组合规模（C(12,6)=924）')
    ap.add_argument('--tol', type=float, default=1e-6,
                    help='判定 r ≈ 0 的相对门槛')
    ap.add_argument('--json', default='_exp/r30_selfac_struct.json')
    a = ap.parse_args()

    EPS0, F, META = variants()
    EPS0 = [np.asarray(e, float) for e in EPS0]
    nv = len(EPS0)
    META = list(META)
    E = [dev(e) for e in EPS0]
    scale = float(np.mean([fro(e) for e in E]))                  # 归一化尺度
    print('=' * 78)
    print('R30 自协调群级结构   变体数 nv=%d   ‖dev ε⁰‖ 均值 = %.6e' % (nv, scale))
    print('=' * 78)

    # ---------- 正对照 1：全 12 变体（windowB_ti64_variants 的 C4 判据）----------
    s_all = np.sum(E, 0)
    print('\n[正对照 P-1] 全 12 变体 dev(ε⁰) 之和的 Frobenius 范数 = %.3e'
          % fro(s_all))
    print('             归一化 = %.3e  （`windowB_ti64_variants` C4 断言 = 0）'
          % (fro(s_all) / scale))
    r_all, f_all = min_residual(E, list(range(nv)))
    print('[正对照 P-1b] r({1..12}) = %.3e （应 ≈0）' % (r_all / scale))

    # ---------- 正对照 2：分辨力对照 ----------
    rng = np.random.default_rng(0)
    Esh = [E[i] for i in rng.permutation(nv)]                    # 只是重标号 ⇒ 不变
    r_sh, _ = min_residual(Esh, list(range(nv)))
    Ep = [E[i] + 0.02 * scale * rng.normal(size=(3, 3)) for i in range(nv)]
    Ep = [dev(e) for e in Ep]
    r_p, _ = min_residual(Ep, list(range(nv)))
    print('[正对照 P-2 ] 重标号后 r = %.3e（应与上面逐位相同 ⇒ 判据对编号不敏感）'
          % (r_sh / scale))
    print('[分辨力对照 P-3] 各张量加 2%% 随机扰动后 r = %.3e（应显著变大）'
          % (r_p / scale))

    # ---------- 迹与谱 ----------
    tr = np.array([np.trace(e) for e in EPS0])
    print('\n[事实 F-1] tr(ε⁰)：min=%.6e max=%.6e 极差=%.2e ⇒ 体积项对全部变体相同'
          % (tr.min(), tr.max(), float(np.ptp(tr))))

    # ---------- 群级：按规模 k 穷举 ----------
    print('\n[群级] 按规模穷举 r(G)（tol=%.1e）' % a.tol)
    print('  %-4s %-8s %-14s %-14s %s'
          % ('k', '组合数', 'r_min', 'r_max', 'r<tol 的组合数'))
    best = {}
    all_six = None
    for k in range(2, a.maxk + 1):
        vals = []
        for idx in itertools.combinations(range(nv), k):
            r, _ = min_residual(E, list(idx))
            vals.append((r / scale, idx))
        vals.sort(key=lambda t: t[0])
        n0 = sum(1 for v, _ in vals if v < a.tol)
        print('  %-4d %-8d %-14.3e %-14.3e %d'
              % (k, len(vals), vals[0][0], vals[-1][0], n0))
        best[k] = vals[:12]
        if k == 6:
            # ⚠ 只存**0-based** 索引（与 `best[k]` 口径一致），落盘时统一 +1。
            #   R30 审计 S4 抓到第一版在这里先 +1、落盘时又 +1 ⇒ JSON 里出现索引 13
            #   （nv=12）。结论不受影响，但下游直接读会误用。
            all_six = [idx for r, idx in vals if r < a.tol]
        if k not in (2,) and n0:
            # 最小规模一旦出现 r≈0 的组合，再往上就不必穷举（单调性：超集也是解）
            print('  ⇒ 最小自协调规模 k* = %d，共 %d 个组合达到 r<tol' % (k, n0))
            break

    print('\n  各规模下 r 最小的前几个组合（变体号从 1 计）：')
    for k, vals in best.items():
        print('   k=%d:' % k)
        for r, idx in vals[:5]:
            f = min_residual(E, list(idx))[1]
            print('      r=%.3e  (%s)  f=%s'
                  % (r, ','.join('V%d' % (i + 1) for i in idx),
                     np.array2string(f, precision=3)))

    # ---------- 配对相容性（几何判据 + 模型判据）----------
    print('\n[配对] 66 对的经典几何判据（det Δε = 0 / λ2 = 0）与模型 E_min：')
    C = None
    if _HAVE_C:
        C = C_cubic(134.0e9, 110.0e9, 36.0e9)
    rows = []
    for k in range(nv):
        for l in range(k + 1, nv):
            de = EPS0[k] - EPS0[l]
            ev = np.linalg.eigvalsh(de)
            lam2 = float(ev[1])
            emin = float('nan')
            if C is not None:
                try:
                    _n, emin, _c = argmin_normal(C, de)
                except Exception:
                    emin = float('nan')
            rows.append(dict(k=k + 1, l=l + 1, lam2=lam2, det=float(np.linalg.det(de)),
                             emin=emin))
    geo_ok = [r for r in rows if abs(r['lam2']) < 1e-12]
    geo_no = [r for r in rows if abs(r['lam2']) >= 1e-12]
    print('   共格（λ2=0）%d 对；不共格 %d 对' % (len(geo_ok), len(geo_no)))
    if geo_ok and geo_no:
        print('   E_min：共格组 范围 [%.3e, %.3e]；不共格组 范围 [%.3e, %.3e]'
              % (min(r['emin'] for r in geo_ok), max(r['emin'] for r in geo_ok),
                 min(r['emin'] for r in geo_no), max(r['emin'] for r in geo_no)))
        print('   ⇒ 零重叠？max(共格)=%.3e < min(不共格)=%.3e ⇒ %s'
              % (max(r['emin'] for r in geo_ok), min(r['emin'] for r in geo_no),
                 '是' if max(r['emin'] for r in geo_ok)
                 < min(r['emin'] for r in geo_no) else '否 ⚠'))

    # ---------- 结构分组：惯习面（正好 6 个 {110}β 面）与 <111>β 方向 ----------
    # ★ 用**生成器自己的** `meta`（`n` = 惯习面法向、`d` = 映到 <11-20>α 的 <111>β），
    #   不用 `argmin_normal` 的结果去分组 —— 后者在近平坦极小上会给近反平行的法向，
    #   用严格阈值分组会把同一张 {110} 面拆成两个（本脚本第一版就踩了这个）。
    print('\n[结构] 按晶体学把 12 个变体分组（用生成器的精确 `meta`）：')

    def group_by(key_fn, tol=1e-6):
        gs = []
        for i in range(nv):
            v = key_fn(i)
            hit = None
            for gi, (ref, members) in enumerate(gs):
                if abs(abs(float(v @ ref)) - 1.0) < tol:
                    hit = gi
                    break
            if hit is None:
                gs.append((v, [i + 1]))
            else:
                gs[hit][1].append(i + 1)
        return gs

    g_plane = group_by(lambda i: np.asarray(META[i]['n'], float))
    g_dir = group_by(lambda i: np.asarray(META[i]['d'], float))
    print('   按**惯习面** {110}β 分组：%d 组（每组 2 个变体 = 面内 60° 旋转对）'
          % len(g_plane))
    for gi, (ref, mem) in enumerate(g_plane):
        r_g, _ = min_residual(E, [m - 1 for m in mem])
        print('     面%d  n=[%s]  变体 %-12s  r=%s'
              % (gi, np.array2string(ref, precision=3, suppress_small=True)[1:-1],
                 ','.join('V%d' % v for v in mem),
                 ('%.3e' % (r_g / scale)) if len(mem) > 1 else '—'))
    print('   按**<111>β 方向**分组：%d 组（每组 3 个变体 = 共 <11-20>α 轴）'
          % len(g_dir))
    for gi, (ref, mem) in enumerate(g_dir):
        r_g, f_g = min_residual(E, [m - 1 for m in mem])
        print('     向%d  d=[%s]  变体 %-18s  r=%.3e  f=%s'
              % (gi, np.array2string(ref, precision=3, suppress_small=True)[1:-1],
                 ','.join('V%d' % v for v in mem), r_g / scale,
                 np.array2string(f_g, precision=3)))

    # ---------- ★★ 检出自协调六元组的结构：是否"每个惯习面各取一个" ----------
    ok_one = None
    neg = None
    if all_six:
        plane_of = {}
        for gi, (ref, mem) in enumerate(g_plane):
            for v in mem:
                plane_of[v] = gi
        # `all_six` 是 0-based ⇒ 这里转 1-based 只用于**打印与结构判定**
        all_six_1 = [tuple(i + 1 for i in s) for s in all_six]
        ok_one = all(len({plane_of[v] for v in s}) == 6 for s in all_six_1)
        print('\n★★ 自协调六元组的结构检验：')
        print('   r<tol 的六元组共 %d 个；"每个惯习面各取正好一个"成立？ %s'
              % (len(all_six_1), '✅ 是' if ok_one else '❌ 否'))
        if len(g_plane) == 6:
            print('   ⇒ 结构读法：6 个 {110}β 惯习面**各选一个变体** '
                  '⇒ 组合数应为 2^6 = 64；实测 %d %s'
                  % (len(all_six_1), '✅ 吻合' if len(all_six_1) == 64 else '⚠ 不吻合'))
        # 负对照：故意在某个惯习面上取两个 ⇒ 必须**不**自协调
        bad = None
        for gi, (ref, mem) in enumerate(g_plane):
            if len(mem) >= 2:
                bad = [mem[0] - 1, mem[1] - 1]
                break
        neg = None
        if bad is not None:
            others = [i for i in range(nv) if plane_of[i + 1] not in
                      {plane_of[bad[0] + 1]}][:4]
            r_bad, _ = min_residual(E, bad + others)
            neg = float(r_bad / scale)
            print('   [负对照] 同一惯习面取两个 + 任意 4 个 ⇒ r = %.3e（应 ≫ tol）%s'
                  % (neg, '✅' if neg > a.tol else '❌ 判据无分辨力'))
        best['6_all'] = [(0.0, list(idx)) for idx in all_six]


    out = dict(nv=nv, scale=scale,
               r_all=float(r_all / scale), r_all_sum_norm=float(fro(s_all) / scale),
               r_relabel=float(r_sh / scale), r_perturb=float(r_p / scale),
               n_selfac_six=(len(all_six) if all_six else 0),
               six_one_per_plane=(bool(ok_one) if all_six else None),
               r_negctrl_two_same_plane=neg,
               n_habit_planes=len(g_plane), n_dirs=len(g_dir),
               r_by_plane_pair=[float(min_residual(E, [m - 1 for m in mem])[0] / scale)
                                for _ref, mem in g_plane],
               r_by_dir_triad=[float(min_residual(E, [m - 1 for m in mem])[0] / scale)
                               for _ref, mem in g_dir],
               best={str(k): [(float(r), [int(i) + 1 for i in idx])
                              for r, idx in v] for k, v in best.items()},
               pairs=rows)
    os.makedirs(os.path.dirname(out and a.json) or '.', exist_ok=True)
    with open(a.json, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print('\n⇒ 已落盘 %s' % a.json)


if __name__ == '__main__':
    main()
