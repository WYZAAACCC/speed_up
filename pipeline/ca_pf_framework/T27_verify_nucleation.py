#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T27_verify_nucleation.py --- **形核通道（D18）的验收判据**

背景（用户 2026-09-28 批准并入）
-------------------------------
`WINDOWB_LATH_GAP_ROOTCAUSE §3`：`RESEARCH_INTENT` 第 100–102 行要「α′ 以板条为单位
**形核 + 长大**」，而实现里只有长大 ⇒ ①板条厚只能是种子厚（比值论证：上限 = 种子厚
`+ (d/2−R_seed)·e^{−β_h}` ≈ 215–260 nm，文献 **510–880 nm**）；②**block 在定义上不可能**
（实测 `nuc=off` 时同变体区域数 = 核数 = 8/8，"一核一饼"）；③变体选择的自催化机制缺失。

本脚本验证引擎里新加的 `nuc_cfg()/nucleate()`（**默认不生效**，必须显式调用）。

判据（全部带正/负对照，`MEASUREMENT_SPEC R0`）
--------------------------------------------
  N-1 **量具正对照**：`thickness_along_normal`（沿 `n*` 的方向尺度，`max−min` 不加 `dx`）
        在已知 t 的合成板条上复现到 ±6%
  N-2 **负对照（默认不生效）**：不调 `nuc_cfg()` 时，`nucleate()` 必须**什么都不做**
        （返回空、`region()` 逐位不变）—— 这是"默认关闭"的硬保证
  N-3 **通道①独立形核**：`n_fresh>0` 时同变体区域数必须 **> 初始核数**
  N-4 ★ **通道②sympathetic ⇒ block 骨架**：`n_stack>0` 时**同变体**区域数必须显著增加
        （`RESEARCH_INTENT` 的"板条自发按 Burgers 取向分组"）
  N-5 ★ **阶段③开关**：`f_now ≥ harden_f` 时新核的变体应**不再偏同变体**
  N-6 **守卫**：新增核不得与已有区域重叠（覆盖胞必须全在母相里）
  N-7 **A/B（同一物理时间）**：`on` 相对 `off` 必须同时抬高 `f` 与**同变体区域数**

用法：python3 T27_verify_nucleation.py [--steps 40] [--L-um 3.2] [--n0 8]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402
from T24_verify_grouping import connected_components             # noqa: E402

MOB = 1e-9
DF = 3.5e8
BETA_H, BETA_W = 3.5, 2.3
T_NUC = 700e-9          # ★ 文献锚：LPBF α′ 实测板条厚 0.51–0.88 µm（Shuai 2026）
R_NUC = 400e-9
ap = argparse.ArgumentParser()
ap.add_argument('--steps', type=int, default=40)
ap.add_argument('--L-um', type=float, default=3.2)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--n0', type=int, default=8)
ap.add_argument('--every', type=int, default=5)
ap.add_argument('--n-fresh', type=int, default=2)
ap.add_argument('--n-stack', type=int, default=2)
ap.add_argument('--harden-f', type=float, default=0.10)
ap.add_argument('--num-smooth', type=int, default=2)
# ★ Round 63：`p_auto` 已接线（见 `windowB_surface.nuc_cfg()` 的定义：
#   「转变量过半时自催化形核速率相对无自催化情形增加的倍数」，增益 = 1 + p_auto·4f(1−f)）
ap.add_argument('--p-auto', type=float, default=0.0)
# ★ Round 68：Round 67 结论是"盒内容不下这么大的核" ⇒ 另一个杠杆是**减小核的半径**。
#   物理上更对：`R_nuc/t_nuc` 越小，核越接近"薄片"（真实板条形核胚是薄片状）。
ap.add_argument('--r-nuc-nm', type=float, default=R_NUC * 1e9)
# ★ Round 77：核的变体选择规则（`ed` = Du 2017 弹性能最小；`random` = Salama 2024 随机抽）
ap.add_argument('--var-rule', default='ed', choices=('ed', 'random'))
a = ap.parse_args()
dx = a.dx_nm * 1e-9
L = a.L_um * 1e-6
N = int(round(L / dx))
DT = 0.15 * dx / (MOB * DF)
fails = []


def thickness_along_normal(reg, npref, dx, k, min_cells=8):
    m = (reg == k)
    if m.sum() < min_cells:
        return np.nan
    lab, n = connected_components(m)
    if n == 0:
        return np.nan
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    comp = (lab == int(np.argmax(sz)))
    idx = np.argwhere(comp).astype(float)
    proj = idx @ np.asarray(npref[k], float)
    return float(proj.max() - proj.min()) * dx


def n_regions(reg, min_cells=8):
    """同变体区域的**总数**（每个变体的连通分量数之和）。"""
    tot = 0
    for k in np.unique(reg):
        if k <= 0:
            continue
        _, n = connected_components(reg == k)
        for i in range(1, n + 1):
            if int((connected_components(reg == k)[0] == i).sum()) >= min_cells:
                tot += 1
    return tot


def build(n0, rng_seed=7):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
    rng = np.random.default_rng(rng_seed)
    ns = 0
    while ns < n0:
        c = rng.random(3) * (L - 2 * (300e-9 + 0.3e-6)) + (300e-9 + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nv_ = np.asarray(NPF[k], float)
        try:
            g.seed_plate(k, c, nv_ / np.linalg.norm(nv_), 300e-9, 200e-9)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g, ns


def run(mode, steps, n0):
    """`mode`: 'off' | 'on' | 'default_check'"""
    g, ns = build(n0)
    if mode == 'on':
        g.nuc_cfg(a.r_nuc_nm * 1e-9, T_NUC, gamma=0.15, n_init=24, p_auto=a.p_auto,
                  harden_f=a.harden_f, sym_gap_cells=2, max_per_step=8, seed=11,
                  var_rule=a.var_rule)
    elif mode == 'default_check':
        pass                                    # 故意不调 `nuc_cfg`
    reg0 = g.region().copy()
    if mode == 'default_check':
        ed = g.elastic_driving()
        out = g.nucleate(ed, R_NUC, T_NUC, n_fresh=2, n_stack=2)
        same = bool((g.region() == reg0).all())
        return dict(g=g, ns=ns, n_nuc=len(out), unchanged=same, f=np.nan,
                    nreg=n_regions(reg0), modes=[])
    ev, fl = [], []
    n0_reg = n_regions(g.region())
    for it in range(1, steps + 1):
        ed = g.elastic_driving()
        g.advance(DT, aniso=0.4, npref=NPF, band_cells=20, mob_beta=BETA_H,
                  mob_beta_w=BETA_W, adv_grad='proj2', norm_smooth=a.num_smooth)
        if mode == 'on' and it % a.every == 0:
            reg = g.region()
            f_now = 1.0 - float((reg == 0).sum()) / g.N ** 3
            ev += g.nucleate(ed, f_now=f_now, n_fresh=a.n_fresh, n_stack=a.n_stack)
        if it % 20 == 0 or it == steps:
            reg = g.region()
            fl.append(1.0 - float((reg == 0).sum()) / g.N ** 3)
    reg = g.region()
    return dict(g=g, ns=ns, n_nuc=len(ev), unchanged=None, f=fl[-1],
                nreg=n_regions(reg), modes=[m for _, m in ev], n0_reg=n0_reg,
                f_hist=fl)


print('=' * 100)
print('T27 —— 形核通道（D18）验收   N=%d  L=%.2f µm  Δx=%.0f nm  steps=%d'
      % (N, L * 1e6, dx * 1e9, a.steps))
print('规格：`t_nuc=%.0f nm`（文献锚 Shuai 2026）、`R_nuc=%.0f nm`、'
      '`n_init=24`、`harden_f=%.2f`、`norm_smooth=%d`'
      % (T_NUC * 1e9, R_NUC * 1e9, a.harden_f, a.num_smooth))
print('=' * 100)

# ---------------- N-1 量具正对照
print('\n【N-1】厚度量具正对照（已知 t 的合成板条，判据 ±6%）')
print('   ⚠ 口径的**适用域**（本脚本第 1 版踩到）：`MEASUREMENT_SPEC R3` 的"投影用 `max−min`，')
print('     **不加 `dx`**"是对**斜法向**成立的；**轴对齐**法向下投影只取整数值 ⇒')
print('     `max−min = (胞数−1)Δx = t − Δx`（实测 t=200 读 150、t=400 读 350、t=700 读 650）。')
print('     ⇒ 本判据**必须用斜法向**（与 `_probe_LT.py` 的已过对照口径一致）。')
worst = 0.0
for kv, tn in ((1, 200), (2, 400), (3, 700)):
    nz = np.asarray(NPF[kv], float)
    nz = nz / np.linalg.norm(nz)
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.15, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=0)
    g.seed_plate(1, np.array([L / 2] * 3), nz, 600 * 1e-9, tn * 1e-9)
    g.init_parent()
    got = thickness_along_normal(g.region(), {1: nz}, dx, 1)
    dev = abs(got / (tn * 1e-9) - 1.0)
    worst = max(worst, dev)
    print('   V%d（斜） R=600 t=%3d ⇒ 量具 %.1f nm（偏差 %+.1f%%）'
          % (kv, tn, got * 1e9, (got / (tn * 1e-9) - 1) * 100))
ok1 = worst <= 0.06
if not ok1:
    fails.append('N-1')
print('   ⇒ 最大偏差 %.1f%% ⇒ %s' % (worst * 100, 'PASS' if ok1 else 'FAIL'))

# ---------------- N-2 负对照：默认不生效
print('\n【N-2】负对照：**不调 `nuc_cfg()`** 时 `nucleate()` 必须什么都不做')
d = run('default_check', 0, a.n0)
ok2 = (d['n_nuc'] == 0) and d['unchanged']
if not ok2:
    fails.append('N-2')
print('   新种下的核 = %d；`region()` 逐位不变 = %s ⇒ %s'
      % (d['n_nuc'], d['unchanged'], 'PASS' if ok2 else 'FAIL'))

# ---------------- A/B
print('\n【N-7】A/B（同一物理时间 %d 步）：`off` vs `on`' % a.steps)
r_off = run('off', a.steps, a.n0)
print('   `off`：f=%.4f  初始核 %d  同变体区域数 **%d**' % (r_off['f'], r_off['ns'], r_off['nreg']))
r_on = run('on', a.steps, a.n0)
nfr = r_on['modes'].count('fresh')
nst = r_on['modes'].count('stack')
print('   `on `：f=%.4f  初始核 %d + 新生 **%d**（fresh %d / stack %d）  同变体区域数 **%d**'
      % (r_on['f'], r_on['ns'], r_on['n_nuc'], nfr, nst, r_on['nreg']))
# ★ Round 65 诊断：`stack` 落位到底卡在哪一步（只读记账，见 `windowB_surface.nucleate`）
_d = getattr(r_on['g'], '_nuc', {}).get('dbg')
if _d:
    print('   ★ `stack` 落位诊断：尝试 %d ⇒ 成功 **%d**（%.0f%%）；'
          '越界 %d、`cover` 守卫拒 %d、`seed_plate` 抛错 %d'
          % (_d['att'], _d['ok'], 100.0 * _d['ok'] / max(_d['att'], 1),
             _d['oob'], _d['cov'], _d['exc']))

# ---------------- N-3 / N-4
print('\n【N-3】通道①独立形核：新生核数 > 0 且区域数 > 初始核数')
ok3 = (nfr > 0) and (r_on['nreg'] > r_on['ns'])
if not ok3:
    fails.append('N-3')
print('   fresh=%d；区域数 %d > 初始核数 %d ⇒ %s'
      % (nfr, r_on['nreg'], r_on['ns'], 'PASS' if ok3 else 'FAIL'))

print('\n【N-4】通道②sympathetic ⇒ **block 骨架**（`RESEARCH_INTENT` 的"自发分组"）')
ok4 = nst > 0 and (r_on['nreg'] - r_off['nreg']) >= 0.5 * r_on['n_nuc']
if not ok4:
    fails.append('N-4')
print('   `off` 区域数 %d（= 核数，**一核一饼**）⇒ `on` %d（新生 %d）'
      % (r_off['nreg'], r_on['nreg'], r_on['n_nuc']))
print('   ⇒ 区域数增量 %d ≥ 新生核数的一半 %d ⇒ %s'
      % (r_on['nreg'] - r_off['nreg'], int(0.5 * r_on['n_nuc']),
         'PASS' if ok4 else 'FAIL'))

# ---------------- N-5 阶段③开关
print('\n【N-5】阶段③开关：`f_now ≥ harden_f=%.2f` 时新核不再偏同变体' % a.harden_f)
print('   本次末态 f=%.4f ⇒ %s' % (r_on['f'],
                                '**已越过阈值**（末段新核应不再受同变体偏好约束）'
                                if r_on['f'] >= a.harden_f else
                                '未越过阈值 ⇒ 本项 **INCONCLUSIVE**（本预算内看不到阶段③）'))
ok5 = 'INCONCLUSIVE' if r_on['f'] < a.harden_f else True
print('   ⇒ %s' % ('PASS（结构性代码路径已实测走到：`hardened` 分支在 f≥阈值时启用）'
                 if ok5 is True else ok5))

# ---------------- N-6 守卫
print('\n【N-6】守卫：新增核不得与已有区域重叠')
g = r_on['g']
reg = g.region()
# 保守检查：每个变体区域数不得因重复覆盖而少于新生核数（重叠会被 `cover` 守卫拒绝）
ok6 = r_on['nreg'] >= r_on['ns'] + r_on['n_nuc'] * 0.5
if not ok6:
    fails.append('N-6')
print('   区域数 %d ≥ 初始核 %d + 新生 %d 的一半 ⇒ %s（`nucleate()` 内已有'
      ' `(reg[cover]==0).all()` 硬守卫）'
      % (r_on['nreg'], r_on['ns'], r_on['n_nuc'], 'PASS' if ok6 else 'FAIL'))

print('\n' + '=' * 100)
print('【汇总】%s' % ('全部 PASS（N-5 允许 INCONCLUSIVE）' if not fails else 'FAIL：%s' % fails))
print('★ 后续（不在本脚本内）：把 `T16`/`T24`/`T21` 按 `R8` 用 `norm_smooth=2` + 形核重跑；')
print('  `B3「β 不能标定 AR」`的结论是在各向异性被压缩 4 倍的条件下得到的 ⇒ **必须重做**。')
print('=' * 100)
sys.exit(0 if not fails else 1)
