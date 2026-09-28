#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_probe_iface_types.py —— **靶③ 的量具**：α/α 界面**错取向类型**的长度分数

为什么需要它
------------
`RESEARCH_INTENT` 的靶③（变体界面分数）在全仓库**没有量具**（已核实）。
旧的 0.38/0.30 是 **Beladi 2014 = Ti-64 但 β 淬火、非 LPBF** ⇒ 按用户 2026-09-28 指示**撤出靶表**。
同工艺替代已找到：

> **Shuai et al. 2026**, *Materials* **19**, 1049, doi **10.3390/ma19061049**（LPBF Ti-64 as-built α′），
> **Table 3 + Fig. 9a**：**Type 4 (63.26°/<10 5 5 3>) ≈ 40–44%** · **Type 2 (60°/<11−20>) ≈ 32–36%** ·
> Type 3 (60.83°/<10 7 17 3>) ≈ 12–14% · Type 5 (90°/<7 17 10 0>) ≈ 12–14% · **Type 6 (10.53°/<0001>) < 2%**。
> ⚠ 测量方法 = **EBSD 界面线段长度分数（2D 截面）** ⇒ 与模型对比**必须说明切面口径**（`MEASUREMENT_SPEC §4.6`）。

方法（**用引擎自己的变体轴**，保证与引擎的变体编号一致）
--------------------------------------------------------
* 变体 `k` 的 α′ **c 轴** = 惯习面法向 `NPF[k]`；**a₁ 轴** = `atab[k]`（**必须先正交化** ——
  实测 `a·n ≈ −0.143`，`windowB_surface.py` 已记账）；
* α′ 的**旋转对称群 D6（12 个操作）**在正交三元组 `(a₁, m, c)` 里是标准的：
  绕 `c` 转 `n·60°`（6 个）+ 绕面内 `0°/60°/120°` 的 2 次轴（3 个）+ 绕 `30°/90°/150°` 的 2 次轴（3 个）；
* 变体对 `(k,l)` 的**约化错取向角**：`θ = min_{G∈D6} arccos((tr(ΔR·G) − 1)/2)`，
  其中 `ΔR = Q_l^T Q_k`，`Q = [a₁, m, c]`；
* 归类到 Table 3 的 Type 2–6（角容差可调，默认 ±1.5°）；
* **长度代理**：用 `region()` 的 6 邻域跨界计数（与 EBSD 的界面线段长度同量纲）。

判据（`MEASUREMENT_SPEC R0`：先拿已知答案跑通工具）
--------------------------------------------------
* **I-1 ★ 自校验（本量具的命门）**：由引擎自己的 12 个变体轴算出的**全部 66 个变体对**，
  其约化错取向角必须**只取 5 个值**，且与 Table 3 的 **{10.53, 60, 60.83, 63.26, 90}°** 吻合。
  ⇒ 这一条不过，**后面所有分数都不可信**（对称群或轴约定错了）。
* **I-2 覆盖性**：5 个类型都要有配对落入，且 66 对**全部**被归类（无 `unclassified`）。
* **I-3 退化对照**：给一个**只含单变体**的 `region()` ⇒ 所有分数必须为 0（且不报错）。

用法：python3 _probe_iface_types.py [--N 64] [--dx-nm 50] [--steps 40] [--tol 1.5]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

# ---------------------------------------------------------------- Table 3（Shuai 2026）
TYPES = [(2, 60.00), (3, 60.83), (4, 63.26), (5, 90.00), (6, 10.53)]
TARGET = {2: (0.32, 0.36), 3: (0.12, 0.14), 4: (0.40, 0.44), 5: (0.12, 0.14), 6: (0.00, 0.02)}


def d6_group():
    """α′ 的 D6 旋转群（12 个），在正交三元组 (a1, m, c) 里。"""
    def Rz(t):
        c_, s_ = np.cos(t), np.sin(t)
        return np.array([[c_, -s_, 0], [s_, c_, 0], [0, 0, 1.0]])

    def Rax(t):
        """绕面内与 a1 成 t 角的轴转 180°。"""
        u = np.array([np.cos(t), np.sin(t), 0.0])
        return 2 * np.outer(u, u) - np.eye(3)
    G = [Rz(np.radians(60 * n)) for n in range(6)]
    G += [Rax(np.radians(t)) for t in (0, 60, 120)]
    G += [Rax(np.radians(t)) for t in (30, 90, 150)]
    return G


def triads():
    """引擎变体 `k` 的正交三元组 `Q_k = [a1, m, c]`（已正交化、右手）。

    ★★ 修复记录（本量具第一版 I-1 自校验 FAIL 后定位）：
      第一版用 `atab[k]` 当 α′ 基面轴 `a1` —— **错的**：实测 `atab[k]·NPF[k] = −0.143`，
      即 `atab[k]` **不垂直于** c 轴 ⇒ 它不是该变体的基面 <11-20> 方向
      （大概率是**该 {110} 面内某个 <111>_β** 的残留表示，而不是严格 ⊥ 面法向的那一支）。
      ⇒ 改用 `windowB_ti64_variants.variants()` 自带的 `d`：
        该模块**按构造成立** `d ⊥ n`（`build_F` 里显式筛掉 `abs(dl @ n) > 1e-9` 的 <111>），
        且 `d` 就是 α′ 的 <11-20> 方向。变体编号按 **`n` 与引擎 `NPF[k]` 匹配**确定。
    """
    from windowB_ti64_variants import variants as _V
    _s, _F, _meta = _V()
    nrm = lambda v: v / np.linalg.norm(v)
    out = {}
    for k in range(1, NV + 1):
        # ★★ 关键：**按下标对齐**，不做全局匹配。
        #   `T16_verify_rve` 里是 `EPS0, _F, _M = variants()`，再 `NPF[v+1]` 由 `EPS0[v]` 算出
        #   ⇒ `NPF[k]` 与 `_meta[k-1]` **本就是同一个变体**。
        mt = _meta[k - 1]
        c_ = nrm(np.asarray(mt['n'], float))
        a_ = nrm(np.asarray(mt['d'], float))
        a_ = a_ - (a_ @ c_) * c_                       # 数值上再正交化一次（保险）
        a_ = nrm(a_)
        m_ = np.cross(c_, a_)
        out[k] = np.column_stack([a_, m_, c_])
        # 记账：`NPF[k]`（引擎实际用的、400 点随机搜索得到的 n*）与真值差多少
        _d = float(np.clip(nrm(np.asarray(NPF[k], float)) @ c_, -1, 1))
        out.setdefault('_err_deg', []).append(np.degrees(np.arccos(_d)))
    return out


def red_angle(Qk, Ql, G):
    """约化错取向角（度）与达到它的那个 G。"""
    dR = Ql.T @ Qk
    best, bg = 1e9, None
    for g in G:
        tr = float(np.trace(dR @ g))
        th = np.degrees(np.arccos(np.clip(0.5 * (tr - 1.0), -1.0, 1.0)))
        if th < best:
            best, bg = th, g
    return best, bg


def classify(theta, tol):
    """归类到 Table 3 的**最近**类型，且距离必须 ≤ `tol`。

    ★★★ 2026-09-28 修（**这是一处量具 bug，不是"分辨力限制"**）：
      旧写法是"按 `TYPES` 顺序，返回**第一个** `|θ−ang| ≤ tol` 的类型"，
      而默认 `tol=1.5°` **大于** `60.83 − 60.00 = 0.83°` 的间距
      ⇒ 任何 60.83° 的配对都被 `Type 2 (60.00°)` **先截住** ⇒ `Type 3` **永远取不到**。
      旧注释把这解释成"`(d,c)` 三元组丢掉了 `F` 的面内取向 ⇒ 分辨不出"
      —— **那个归因是错的**（见 `_probe_d6_variants.py` 的独立真值：理想 Burgers 12 变体集
      给出 `T6=6 T2=12 T3=24 T4=12 T5=12`，且 `windowB_ti64_variants` 与理想集逐变体偏差 **0.000°**，
      即**面内取向信息一直都在**）。
    ⇒ 判据改为"最近邻 + 距离门槛"，默认 `tol=0.4°`（< 0.83/2，无歧义）。
    """
    best, bang = None, 1e9
    for t, ang in TYPES:
        d = abs(theta - ang)
        if d < bang:
            best, bang = t, d
    return best if bang <= tol else None


ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--steps', type=int, default=40)
ap.add_argument('--tol', type=float, default=0.4,
                help='类型角容差（度）。**必须 < 0.415**（60.83 与 60.00 的半间距），'
                     '否则 Type 3 会被 Type 2 吞掉（见 classify 的记账）')
ap.add_argument('--n0', type=int, default=10)
a_ap = ap.parse_args()
N = a_ap.N
L = N * a_ap.dx_nm * 1e-9
DT = 0.15 * (L / N) / (1e-9 * 3.5e8)

# 引擎自己的 atab（形核/推进都用它）
_g = W.LevelSetMulti(16, 16 * 50e-9, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                     df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
_ATAB = _g.atab

print('=' * 104)
print('_probe_iface_types —— 靶③ 量具：α/α 界面错取向类型的长度分数')
print('  同工艺靶：Shuai 2026 (LPBF Ti-64, doi 10.3390/ma19061049), Table 3 + Fig. 9a')
print('=' * 104)

G = d6_group()
Q = triads()
fails = []

# ---------------------------------------------------------------- I-1 自校验（命门）
print('\n【I-1 ★自校验】引擎自己的 12 个变体轴 ⇒ 全部 66 个变体对的约化错取向角')
angles, pairs = [], []
for k in range(1, NV + 1):
    for l in range(k + 1, NV + 1):
        th, _ = red_angle(Q[k], Q[l], G)
        angles.append(th)
        pairs.append((k, l, th))
angles = np.array(angles)
# 聚类成"类型"（按 Table 3 归类；未归类的单独列出）
hist = {t: 0 for t, _ in TYPES}
uncl = []
for k, l, th in pairs:
    t = classify(th, a_ap.tol)
    if t is None:
        uncl.append((k, l, th))
    else:
        hist[t] += 1
found = sorted(hist.items())
print('   66 对的角度分布（按 Table 3 归类，容差 ±%.1f°）：' % a_ap.tol)
for t, ang in TYPES:
    print('      Type %d (%6.2f°) : **%2d** 对' % (t, ang, hist[t]))
print('   未归类 = **%d** 对 %s' % (len(uncl), ('（前几个：%s）' % uncl[:4]) if uncl else ''))
# ★★ I-1 判据的口径修正（**第三版，2026-09-28 —— 推翻了第二版的归因**）：
#   第一版："5 个类型都必须非空" ⇒ FAIL。
#   第二版（**错的**）：归因为"本量具分辨力不够，`(d,c)` 三元组丢掉了 `F` 的面内取向"，
#     并把判据降到"≥4 个类型 + `60.83°` 列为已知限制 I-1c"。
#   第三版（本轮，**根因**）：`classify()` 旧写法按 `TYPES` **顺序**取第一个
#     `|θ−ang| ≤ tol` 的类型，而默认 `tol=1.5°` **大于** `60.83−60.00 = 0.83°` 的间距
#     ⇒ `Type 3` **在任何 tol≥0.83 下都不可达**（被 `Type 2` 先截住）。
#     **与面内取向无关**：`_probe_d6_variants.py` 从零构造理想 Burgers 12 变体集，
#     其 66 对给出 `T6=6 T2=12 T3=24 T4=12 T5=12`，且 `windowB_ti64_variants` 的
#     `(n,d)` 与理想集逐变体偏差 **0.000°** ⇒ 面内信息**一直都在**。
#   ⇒ 判据（第三版）：(a) 66 对**全部归类**；(b) **5/5 类型都复现**；
#     (c) **配对数与理想集真值逐项相同**（群论给死的数，见 `_TRUTH_N`）。
_nonempty = sum(1 for t, _ in TYPES if hist[t] > 0)
ok1 = (len(uncl) == 0) and (_nonempty == 5)
print('   ⇒ %s（归类覆盖 66/66；复现的类型数 = %d/5）'
      % ('PASS' if ok1 else 'FAIL', _nonempty))
# ★★★ 2026-09-28：**配对数真值**（由 `_probe_d6_variants.py` 独立构造理想 Burgers 集给出）。
#   这是群论给死的数，与"界面面积分数"**不是一回事** —— 靶值是面积分数，
#   而配对数只说明"这 12 个变体轴是否构成完整 Burgers 集"。
_TRUTH_N = {6: 6, 2: 12, 3: 24, 4: 12, 5: 12}
_bad = [t for t, _ in TYPES if hist[t] != _TRUTH_N[t]]
if _bad:
    print('   ⚠ 配对数与理想 Burgers 集真值（T6=6 T2=12 T3=24 T4=12 T5=12）不符：'
          '实测 %s ⇒ **变体轴集合不完整**'
          % ' '.join('T%d=%d' % (t, hist[t]) for t, _ in TYPES))
    fails.append('I-1b')
else:
    print('   ✅ 配对数与理想 Burgers 集真值**逐项相同**（T6=6 T2=12 T3=24 T4=12 T5=12）'
          ' ⇒ 12 个变体轴构成完整 Burgers 变体集')
if not ok1:
    fails.append('I-1')

# ---------------------------------------------------------------- I-3 退化对照
print('\n【I-3 退化对照】只含单变体的 `region()` ⇒ 所有类型分数必须为 0')
reg1 = np.zeros((N, N, N), dtype=np.int8)
reg1[:, :, : N // 2] = 1                                  # 只有变体 1
cnt = {t: 0 for t, _ in TYPES}
for ax in range(3):
    x, y = reg1, np.roll(reg1, -1, axis=ax)
    sel = (x != y) & (x > 0) & (y > 0)
    for u, v in zip(x[sel].ravel(), y[sel].ravel()):
        t = classify(red_angle(Q[int(u)], Q[int(v)], G)[0], a_ap.tol)
        if t is not None:
            cnt[t] += 1
ok3 = sum(cnt.values()) == 0
print('   变体-变体界面键数 = **%d** ⇒ %s' % (sum(cnt.values()), 'PASS' if ok3 else 'FAIL'))
if not ok3:
    fails.append('I-3')

# ---------------------------------------------------------------- I-2 真实算例
print('\n【I-2 真实 RVE】N=%d Δx=%.0f nm，跑 %d 步后统计界面类型分数' % (N, a_ap.dx_nm, a_ap.steps))
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
rng = np.random.default_rng(7)
ns, guard = 0, 0
while ns < a_ap.n0 and guard < 500:
    guard += 1
    c = rng.random(3) * (L - 1.2e-6) + 0.6e-6
    k = int(rng.integers(1, NV + 1))
    nv_ = np.asarray(NPF[k], float)
    try:
        g.seed_plate(k, c, nv_ / np.linalg.norm(nv_), 300e-9, 200e-9)
        ns += 1
    except ValueError:
        pass
g.init_parent()
for _ in range(a_ap.steps):
    g.advance(DT, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
reg = g.region()
pv = 0
cnt2 = {t: 0 for t, _ in TYPES}
for ax in range(3):
    x, y = reg, np.roll(reg, -1, axis=ax)
    for u, v in zip(x.ravel(), y.ravel()):
        u, v = int(u), int(v)
        if u == v:
            continue
        if u == 0 or v == 0:
            pv += 1
            continue
        t = classify(red_angle(Q[u], Q[v], G)[0], a_ap.tol)
        if t is not None:
            cnt2[t] += 1
tot_vv = sum(cnt2.values())
print('   parent–variant 界面键 %d ；变体–变体 %d' % (pv, tot_vv))
print('   %-8s %-12s %-12s %s' % ('Type', '模型分数', '同工艺靶', '判定'))
for t, ang in TYPES:
    frac = cnt2[t] / max(tot_vv, 1)
    lo, hi = TARGET[t]
    ok = (lo - 0.06) <= frac <= (hi + 0.06)
    print('   %-8s %-12s %-12s %s' % ('Type %d' % t, '%.3f' % frac,
                                      '%.2f–%.2f' % (lo, hi), '✓' if ok else '✗'))
print('\n   ⚠ **口径警告（`R10`）**：靶值来自 **EBSD 2D 截面线段长度**；模型的键计数是 **3D 6 邻域面积代理**，')
print('     且本算例只有 %d 个初始核、%d 步（远未长大）⇒ **本表只作量具演示，不得当"命中文献"报**。'
      % (a_ap.n0, a_ap.steps))
print('\n' + '=' * 104)
print('=== 靶③ 量具验收 %s ===' % ('全部 PASS' if not fails else ('FAIL: ' + ','.join(fails))))
sys.exit(0 if not fails else 1)
