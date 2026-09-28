#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_reinit_norm.py --- ★★★ 判决实验 `N1`：`reinit` 的**目标归一化**与引擎的**带健康阈值**谁错？

背景（`WINDOWB_STATE_CONFIRMED.md §2 N1`）
----------------------------------------
两条实测事实**互相矛盾**，而仓库里**从未对过账**：

* **事实 A**（引擎自带"带健康 probe"，`_reg_run4.log`）：
  `带内|∇φ_win|中位 = 0.457 / 0.459 / 0.468 / 0.463 / 0.509 …` → **判定 `OK`**。
* **事实 B**（`windowB_surface.py:2922-2930` 注释原文）：pair reinit 的目标是
  `|∇d2| = 1`（`d2 = (φ_k−φ_l)/2`），理由是「VDF 里 `∇φ_k = +n`、`∇φ_l = −n`
  ⇒ `|∇d|=2` ⇒ `|∇d2|=1`」。

**两者不可能同时对**。若 A 的 0.46 是这台引擎 VDF 的正确归一化，则 B 的目标 `1` 错了约 2.17×；
若 B 对，则 A 的 `OK` 判错了。

本探针**一次定性**
------------------
关键设计：**在"刚种下的、解析已知的"种子上量** —— 此时场**不可能是"被演化弄坏的"**，
所以读数直接反映**引擎的归一化约定本身**，而不是演化造成的退化。

判据（`MEASUREMENT_SPEC R0`：先拿已知答案跑通工具）
--------------------------------------------------
* **A-0 量具正对照**：网格上解析 SDF 的球 `φ_an = |x−c| − R`
  ⇒ `median|∇φ_an|` **必须 ≈ 1**（否则量具本身坏，后面全部免谈）。
* **A-1 引擎自存场**：`seed_sphere(1,…)` 之后 `median|∇φ_1|` 在带内 = ?
  * ≈1 ⇒ 引擎的场**是按 `|∇φ|=1` 存的** ⇒ **事实 B 的目标正确**、A 的阈值/判据错；
  * ≈0.46 ⇒ 引擎的场**按别的约定存**（`|∇φ|≈0.46`）⇒ **事实 B 的 reinit 目标错了约 2.17×**。
* **A-2 判决量 `|∇d2|`**：`seed_plate` + `init_parent()` 后，
  用**引擎自己的带定义**（`|d2| ≤ band_cells·dx`，`band_cells=6`，与 `reinitialize()` 默认一致）
  量 `median|∇d2|`。
* **A-3 分解**：同一带内分别量 `median|∇φ_k|`、`median|∇φ_l|`、以及两者的夹角余弦
  `cos∠(∇φ_k, ∇φ_l)`。**若两者各 ≈1 而 `|∇d2|≈0.46` ⇒ 夹角不是 180° ⇒ 事实 B 的前提
  「`∇φ_k=+n, ∇φ_l=−n`」在这台 VDF 上不成立**（这是最可能的真相）。
* **A-4 损伤直测**：对该**新鲜**种子调一次 `g.reinitialize()`，报
  ① `region()` 翻转胞数（必须 0，A2 守卫）② 界面带胞数 before/after（膨胀比）
  ③ `_reinit_done`/`_reinit_skipped`。⇒ 直接回答"reinit 会不会伤到干净种子"。

用法：python3 _probe_reinit_norm.py [--N 64] [--dx-nm 25] [--el 8.0] [--band-cells 6]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB, DF = 1e-9, 3.5e8


def gnorm(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


def band_bonds(reg):
    n = 0
    for ax in range(3):
        n += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return n


ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx-nm', type=float, default=25.0)
ap.add_argument('--el', type=float, default=8.0, help='种子长/宽比（锐化界面，放大问题）')
ap.add_argument('--band-cells', type=float, default=6.0,
                help='带定义，必须与 reinitialize() 默认一致（默认 6）')
a_ap = ap.parse_args()
N, dx = a_ap.N, a_ap.dx_nm * 1e-9
L = N * dx
KV = 1
R_nm, T_nm = 300.0, 200.0

print('=' * 104)
print('_probe_reinit_norm —— `N1` 判决实验：reinit 的目标归一化 vs 带健康阈值')
print('  N=%d  Δx=%.1f nm  L=%.2f µm  带定义 `|d2| <= %.1f·dx`（= reinitialize() 默认）'
      % (N, a_ap.dx_nm, L * 1e6, a_ap.band_cells))
print('=' * 104)

# ---------------------------------------------------------------- A-0 量具正对照
c = np.array([L / 2] * 3)
ax_ = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(ax_ - c[0], ax_ - c[1], ax_ - c[2], indexing='ij')
R0 = 12 * dx
phi_an = np.sqrt(X ** 2 + Y ** 2 + Z ** 2) - R0
ban_an = np.abs(phi_an) <= 4 * dx
gm_an = float(np.median(gnorm(phi_an, dx)[ban_an]))
print('\n【A-0 量具正对照】解析 SDF 球（R=%.0f nm）' % (R0 * 1e9))
print('   `median|∇φ_an|` = **%.4f**（真值 1.0，判据 ±2%%）⇒ %s'
      % (gm_an, 'PASS（量具可用）' if abs(gm_an - 1) < 0.02 else 'FAIL（量具坏，后面免谈）'))
if abs(gm_an - 1) >= 0.02:
    print('  ⇒ 量具本身不可信，终止。')
    sys.exit(2)

# ---------------------------------------------------------------- 建引擎
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)

# ---------------------------------------------------------------- A-1 引擎自存场
g.seed_sphere(KV, c, R0)
ph1 = g.phi[KV]
ban1 = np.abs(ph1) <= 4 * dx
gm1 = float(np.median(gnorm(ph1, dx)[ban1]))
print('\n【A-1 引擎自存场】`seed_sphere(%d, R=%.0f nm)` 之后' % (KV, R0 * 1e9))
print('   `median|∇φ_%d|` = **%.4f**  (带胞 %d)' % (KV, gm1, int(ban1.sum())))
print('   ⇒ 引擎的场按 %s 归一化' % ('`|∇φ| = 1`（与事实 B 的目标一致）' if abs(gm1 - 1) < 0.1
                                  else '`|∇φ| ≈ %.3f`（**不是 1**）' % gm1))

# ---------------------------------------------------------------- A-2/A-3 判决量
g2 = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                     df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
n_hab = np.asarray(NPF[KV], float)
n_hab = n_hab / np.linalg.norm(n_hab)
a_ax = np.asarray(g2.atab[KV], float)
a_ax = a_ax - (a_ax @ n_hab) * n_hab
a_ax = a_ax / np.linalg.norm(a_ax)
g2.seed_plate(KV, c, n_hab, R_nm * 1e-9, T_nm * 1e-9, elong=a_ap.el, along=a_ax)
g2.init_parent()

ph = g2.phi
karr, larr = np.argmin(ph, axis=0), None
order = np.argsort(ph, axis=0)
karr, larr = order[0], order[1]
pha = np.take_along_axis(ph, karr[None], 0)[0]
phb = np.take_along_axis(ph, larr[None], 0)[0]
d2 = 0.5 * (pha - phb)
near = np.abs(d2) <= a_ap.band_cells * dx

gda = np.gradient(pha, dx, edge_order=2)
gdb = np.gradient(phb, dx, edge_order=2)
na = np.sqrt(sum(t ** 2 for t in gda))
nb = np.sqrt(sum(t ** 2 for t in gdb))
na_ = na + 1e-30
nb_ = nb + 1e-30
cosang = sum(gda[i] * gdb[i] for i in range(3)) / (na_ * nb_)
gd2 = np.sqrt(sum(t ** 2 for t in np.gradient(d2, dx, edge_order=2)))

m_d2 = float(np.median(gd2[near]))
m_a = float(np.median(na[near]))
m_b = float(np.median(nb[near]))
m_cos = float(np.median(cosang[near]))
ang = float(np.degrees(np.arccos(np.clip(m_cos, -1, 1))))

print('\n【A-2/A-3 判决量】`seed_plate(V%d, R=%.0f nm, t=%.0f nm, elong=%.1f)` + `init_parent()`'
      % (KV, R_nm, T_nm, a_ap.el))
print('   带胞数 = %d（`|d2| <= %.1f·dx`）' % (int(near.sum()), a_ap.band_cells))
print('   `median|∇φ_k|` = %.4f   `median|∇φ_l|` = %.4f' % (m_a, m_b))
print('   `median|∇d2|`  = **%.4f**   ← reinit 的目标是 1；偏离 = %+.3f（告警门槛 0.5）'
      % (m_d2, m_d2 - 1.0))
print('   `median cos∠(∇φ_k, ∇φ_l)` = %+.4f ⇒ 夹角 **%.1f°**（事实 B 的前提要求 **180°**）'
      % (m_cos, ang))

print('\n【判决】')
if m_d2 >= 0.9:
    print('   `median|∇d2| ≈ 1` ⇒ **事实 B（reinit 目标）正确**；')
    print('   ⇒ `_reg_run4.log` 的 0.46 是**演化之后**才出现的退化，不是引擎约定')
    print('   ⇒ 下一步：查"场为什么退化到 0.46 后 reinit 也拉不回来"。')
elif abs(m_a - 1) < 0.15 and abs(m_b - 1) < 0.15 and m_d2 < 0.9:
    print('   两个场**各自** `|∇φ| ≈ 1`，但 `|∇d2| = %.3f ≪ 1`，夹角 **%.0f° ≠ 180°**' % (m_d2, ang))
    print('   ⇒ **事实 B 的前提「∇φ_k = +n、∇φ_l = −n」在这台 VDF 上不成立**')
    print('   ⇒ **reinit 的目标 `|∇d2| = 1` 用错了量** ⇒ 它每次都在把界面往错的方向推。')
    print('   ⇒ 修法候选（**会改数，须按 R8 重跑，需用户决策**）：')
    print('      (i) 目标改为 `median|∇d2|` 的**实测不动点**；(ii) 或改对 `d`（不是 `d/2`）做 Sussman；')
    print('      (iii) 或干脆**关掉 pair reinit**，只保留 `reinit_guard_region` 的守恒性。')
else:
    print('   两个场各自的 `|∇φ|` 就**不是 1**（%.3f / %.3f）' % (m_a, m_b))
    print('   ⇒ **事实 A 的 `OK` 阈值判错了**（0.46 不是正确的 SDF 归一化）')
    print('   ⇒ 修法：先查引擎把场按什么约定存（`seed_plate`/`advance`/`init_parent` 哪一步引入）。')

# ---------------------------------------------------------------- A-4 损伤直测
reg0 = g2.region()
nb0 = band_bonds(reg0)
trap = np.seterr(all='ignore')
import warnings as _w                                               # noqa: E402
with _w.catch_warnings(record=True) as rec:
    _w.simplefilter('always')
    g2.reinitialize()
nwarn = sum(1 for r in rec if 'pair reinit' in str(r.message))
reg1 = g2.region()
flip = int((reg1 != reg0).sum())
nb1 = band_bonds(reg1)
print('\n【A-4 损伤直测】对**新鲜**种子调一次 `g.reinitialize()`（band_cells=6）')
print('   `region()` 翻转胞数 = **%d**（判据 0）⇒ %s' % (flip, 'PASS' if flip == 0 else 'FAIL'))
print('   界面键数（6 邻域跨界计数，`_band_bonds`）%d → %d（膨胀比 **%.4f×**，P0-3 硬门槛 1.2×）⇒ %s'
      % (nb0, nb1, nb1 / max(nb0, 1), 'PASS' if nb1 / max(nb0, 1) <= 1.2 else 'FAIL'))
print('   `reinit_done`=%d  `reinit_skipped`=%d  ⇒ 跳过率 %.2f'
      % (getattr(g2, '_reinit_done', 0), getattr(g2, '_reinit_skipped', 0),
         getattr(g2, '_reinit_skipped', 0)
         / max(getattr(g2, '_reinit_done', 0) + getattr(g2, '_reinit_skipped', 0), 1)))
print('   引擎内部实测 `_reinit_last_med` = %s' % getattr(g2, '_reinit_last_med', None))
print('   本次触发的 `pair reinit` 告警数 = **%d**' % nwarn)
print('   ⚠ 记账：`reinit_strict` 在 `T21/T24/T27` **全关**，本探针**不改**它（只读）。')

# ------------------------------------------------- A-5 多变体：带掩模是否被"非本配对胞"污染？
#   假设 H1：引擎里 `_med` 的掩模是 `near = |d2| <= band_cells*dx`，**没有**再与 `is_kl` 求交
#   ⇒ 在多区域下，`near` 里混进了"局部赢家是第三个区域"的胞，那里 ∇φ_k 与 ∇φ_l
#     **不对向**（都朝各自区域外）⇒ 中位被拉低到 ~0.46。
#   若 H1 成立：`_med_kl`（交集掩模）应 ≈1 而 `_med_all`（引擎现用掩模）应 ≈0.46。
print('\n' + '=' * 104)
print('【A-5 多变体判决】带掩模是否被"非本配对胞"污染？（H1）')
K2, R2, T2 = 5, 200.0, 200.0
cc = [np.array([0.30, 0.30, 0.30]) * L, np.array([0.70, 0.70, 0.70]) * L]
g3 = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                     df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
for kk, cen in ((KV, cc[0]), (K2, cc[1])):
    nn = np.asarray(NPF[kk], float)
    nn = nn / np.linalg.norm(nn)
    g3.seed_plate(kk, cen, nn, R2 * 1e-9, T2 * 1e-9)
g3.init_parent()
ph3 = g3.phi
o3 = np.argsort(ph3, axis=0)
ka, la = o3[0], o3[1]
inter = ka != la
sm = np.where(inter, ph3.shape[0], 0)
raw = np.minimum(ka, la) * ph3.shape[0] + np.maximum(ka, la)
sm = np.where(inter, raw, ph3.shape[0] ** 2)
uniq = [int(v) for v in np.unique(sm) if v < ph3.shape[0] ** 2]
print('   区域数 = %d；活跃配对（由 region 邻接/取两个最小场得到）= %s'
      % (g3.nreg, [(v // ph3.shape[0], v % ph3.shape[0]) for v in uniq]))
for v in uniq:
    k_, l_ = v // ph3.shape[0], v % ph3.shape[0]
    is_kl = ((ka == k_) & (la == l_)) | ((ka == l_) & (la == k_))
    sel = (sm == v)
    pha_, phb_ = ph3[k_], ph3[l_]
    d2_ = 0.5 * (pha_ - phb_)
    near_ = np.abs(d2_) <= a_ap.band_cells * dx
    g2_ = np.sqrt(sum(t ** 2 for t in np.gradient(d2_, dx, edge_order=2)))
    mask_all = near_
    mask_kl = near_ & is_kl
    ma = float(np.median(g2_[mask_all])) if mask_all.any() else float('nan')
    mk = float(np.median(g2_[mask_kl])) if mask_kl.any() else float('nan')
    print('   配对 (%d,%d): 引擎掩模 `|d2|<=6dx` 胞数 **%7d** `median|∇d2|` = **%.4f**  |  '
          '交集掩模 胞数 %7d `median|∇d2|` = **%.4f**'
          % (k_, l_, int(mask_all.sum()), ma, int(mask_kl.sum()), mk))

# ------------------------------------------------- A-6 关键收尾：演化后 reinit 还能不能把场拉回来？
#   A-2/A-5 已证"新鲜种子是健康的"（引擎内部 `_reinit_last_med`=0.987、交集掩模=引擎掩模、夹角 180°）。
#   而 T24 各档日志实测 `median ≈ 0.46` 且**每次都进告警分支** ⇒ 退化发生在**演化过程中**。
#   本段判定它是"正常漂移（reinit 能拉回）"还是"reinit 失效（拉不回）"—— 后者才是 P0。
print('\n' + '=' * 104)
print('【A-6 演化 → reinit 能否恢复】`reinit_every=0` 关掉自动重初始化，只看前向演化 + 手动一次 reinit')
g4 = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                     df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=None)
nh4 = np.asarray(NPF[KV], float)
nh4 = nh4 / np.linalg.norm(nh4)
aa4 = np.asarray(g4.atab[KV], float)
aa4 = aa4 - (aa4 @ nh4) * nh4
aa4 = aa4 / np.linalg.norm(aa4)
g4.seed_plate(KV, c, nh4, R_nm * 1e-9, T_nm * 1e-9, elong=a_ap.el, along=aa4)
g4.init_parent()
dt4 = 0.15 * dx / (MOB * DF)


def med_engine(gx, bc=6.0):
    """完全复刻 `reinitialize()` 里的 `_med` 口径（含它用的默认 edge_order）。"""
    o = np.argsort(gx.phi, axis=0)
    kk, ll = o[0], o[1]
    d = 0.5 * (np.take_along_axis(gx.phi, kk[None], 0)[0]
               - np.take_along_axis(gx.phi, ll[None], 0)[0])
    nr = np.abs(d) <= bc * gx.dx
    gd = np.gradient(d, gx.dx)
    return float(np.median(np.sqrt(sum(t ** 2 for t in gd))[nr])), int(nr.sum())


m0, n0_ = med_engine(g4)
print('   step   0（新鲜）: `median|∇d2|` = **%.4f**   带胞 %d' % (m0, n0_))
hist = [m0]
for st in (20, 40, 60):
    for _ in range(20):
        g4.advance(dt4, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    g4._cnt = 0                      # 防止 advance 内部按 reinit_every 触发（本段已置 0）
    mm, nn_ = med_engine(g4)
    hist.append(mm)
    print('   step %3d（演化）: `median|∇d2|` = **%.4f**   带胞 %d' % (st, mm, nn_))
regb, nbb = g4.region(), band_bonds(g4.region())
_w2 = _w.catch_warnings(record=True)
with _w2 as rec2:
    _w.simplefilter('always')
    g4.reinitialize()
nw2 = sum(1 for r in rec2 if 'pair reinit' in str(r.message))
m5, n5_ = med_engine(g4)
rega, nba = g4.region(), band_bonds(g4.region())
print('   reinit 之后     : `median|∇d2|` = **%.4f**   带胞 %d' % (m5, n5_))
print('   ⇒ 恢复率 = %.3f（(reinit 后 − 演化后) / (1 − 演化后)，1.0 = 完全恢复）'
      % ((m5 - hist[-1]) / max(1e-9, 1.0 - hist[-1])))
print('   `region()` 翻转胞数 = %d ；界面键数 %d → %d（%.4f×）'
      % (int((rega != regb).sum()), nbb, nba, nba / max(nbb, 1)))
print('   本次 reinit 告警数 = %d ；`_reinit_done`=%d `_reinit_skipped`=%d'
      % (nw2, getattr(g4, '_reinit_done', 0), getattr(g4, '_reinit_skipped', 0)))
print('\n【A-6 判决】')
_rec = (m5 - hist[-1]) / max(1e-9, 1.0 - hist[-1])
_impr = m5 - hist[-1]
print('   演化 60 步：%.4f → **%.4f**（Δ=%.4f，带胞 %d → %d，%+.1f%%）'
      % (hist[0], hist[-1], hist[-1] - hist[0], n0_, nn_, (nn_ / max(n0_, 1) - 1) * 100))
print('   一次 reinit：%.4f → **%.4f**（Δ=**%+.4f**，恢复率 %+.3f）'
      % (hist[-1], m5, _impr, _rec))
# ★ 判据不能用绝对阈值（本探针第一版用 `m5 > 0.85` ⇒ 在 m5=0.8511 时**误判为"能拉回"**，
#   而同一份输出里的恢复率是 −0.033。⇒ 判据必须比较**前后**，不能拿水平值当改善证据。
#   MEASUREMENT_SPEC 同类教训：R4 的恒等式陷阱 / 教训 #26「守恒量逐位不变是初值钉住的」。
if _rec > 0.5:
    print('   ⇒ reinit **能显著拉回**（恢复率 %+.3f > 0.5）⇒ 0.46 属"正常漂移、reinit 有效"' % _rec)
    print('   ⇒ `N1` 降级：只需把 `reinit_strict=True` 与实际膨胀比如实报出，不必改数值路径。')
elif _impr > 0.02:
    print('   ⇒ reinit **部分有效但远不足以补偿**（Δ=%+.4f，恢复率 %+.3f）⇒ 需查 `reinit_iters`/`dtau`。' % (_impr, _rec))
else:
    print('   ⇒ ★★ reinit **完全没有恢复距离函数性质**（Δ=**%+.4f**，恢复率 %+.3f）'
          % (_impr, _rec))
    print('   ⇒ 而它**确实执行了**（`_reinit_done`=%d，未被跳过），且零等值面理论上会被移动。'
          % getattr(g4, '_reinit_done', 0))
    print('   ⇒ **真 P0**：这条路径花掉机时、可能移动界面，却修不回 `|∇d2|`。')
    print('   ⇒ 下一步（按顺序）：① 查 `sussman_reinit` 的自适应 `dtau` 与收敛判据为何推不动；')
    print('     ② 查 `advance()` 是否在破坏 `|∇φ|=1`（本段实测 60 步 −0.088、带胞 +18%）；')
    print('     ③ 判定"R11-b 的定时 reinit"是否应当**直接关掉**（改为只依赖 `guard_region` 的守恒性）。')
print('   ⚠ 本段**不改** `reinit_strict`，只读；判据已按"前后比较"写，不用绝对阈值。')
print('=' * 104)


print('=' * 104)
