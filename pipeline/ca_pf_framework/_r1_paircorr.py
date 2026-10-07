#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_paircorr.py --- ★★ 66 对：**几何 rank-1 相容性** vs **微弹性相容性**，它们一致吗？

科学问题
--------
马氏体文献里判"两块板条能不能形成不变平面界面"用的是**几何**判据：
`Δε = ε_i − ε_j` 是否 rank-1（`det Δε ≈ 0` 或最佳 rank-1 残余 `r` 小）。
而**本模型**用的是**微弹性**判据：`ncmp[k,l] = argmin_n 0.5·Δε:Λ(C,n):Δε`，
其最小值 `E_min` 才是模型眼里的"这一对有多不相容"。

第 24 轮在 6 个同 packet 对上发现两者**排序相反**。
本脚本把它做成**全 66 对**的定量结果。

判据（先写死）
--------------
  C-1 算全 66 对的 `r`（几何）与 `E_min`（微弹性）。
  C-2 报 Spearman 秩相关（对单调关系稳健）。
      * `ρ` 接近 **−1**（r 小 ⇔ E_min 小，即两者一致）⇒ 几何判据可用作代理；
      * `ρ` 接近 **0 或为正** ⇒ **几何判据不能当微弹性的代理**
        ⇒ 文献的"rank-1 相容性"结论**不能**直接搬进本模型。
  C-3 **正对照**：`E_min` 必须与 `ncmp` 处的**实际能量**一致（自洽）。
  C-4 附带：把 6 个同 packet 对单独列出来看。
"""
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from windowB_surface import _argmin_normal                      # noqa: E402
from windowB_pf3d import _lam_full, E_normal                     # noqa: E402
from T16_verify_rve import C, EPS0, NV                           # noqa: E402

E = [np.asarray(e, float) for e in EPS0]
NVV = NV


def rank1_resid(dE):
    """几何①：**对称部分**的最佳 rank-1 逼近的相对残余（相对 ‖Δε‖）。"""
    S = 0.5 * (dE + dE.T)
    w, V = np.linalg.eigh(S)
    k = int(np.argmax(np.abs(w)))
    a = np.sign(w[k]) * np.sqrt(abs(w[k])) * V[:, k]
    return float(np.linalg.norm(dE - np.outer(a, a)) / max(np.linalg.norm(dE), 1e-300))


def rank1_resid_full(dU):
    """几何②：**完整** ΔU 的 Hadamard rank-1 残余 `σ₂/σ₁`。

    两变体间存在不变平面界面的**标准**判据（Hadamard 跳跃条件）是
    `ΔF = F_j − F_i` 能写成 `a ⊗ n`，即 `rank ΔF = 1`（`det ΔF = 0`）。
    这里直接用 SVD：`σ₂/σ₁` 就是到最近 rank-1 矩阵的相对距离。
    与几何①的区别：**不做对称化**，且不假定最佳逼近对称。
    """
    sv = np.linalg.svd(np.asarray(dU, float), compute_uv=False)
    return float(sv[1] / max(sv[0], 1e-300))


def e_at(C, dE, n):
    """在给定法向 n 上算 0.5·Δε:Λ(C,n):Δε。

    `_lam_full(C,n)` 返回的是 **(3,3,3,3) 四阶张量**（不是 6×6），
    所以这里直接做全张量缩并 —— **不经过任何 Voigt/工程剪应变约定**，
    因此这条检查与 `E_normal` 内部实现互为独立写法。
    """
    L = _lam_full(C, np.asarray(n, float))
    return 0.5 * float(np.einsum('ij,ijkl,kl->', np.asarray(dE, float), L,
                                 np.asarray(dE, float)))


print('=' * 96)
print('66 对：几何 rank-1 相容性 vs 微弹性相容性')
print('=' * 96, flush=True)
rows = []
for k, l in itertools.combinations(range(1, NVV + 1), 2):
    de = E[k - 1] - E[l - 1]
    r = rank1_resid(de)
    r2 = rank1_resid_full(de)
    n_p, E_min, cert = _argmin_normal(C, de)
    # C-3 正对照：在 ncmp 上重算能量，应与 E_min 一致
    e_chk = e_at(C, de, n_p)
    # C-3b 正对照：用**模型自己的**能量函数在同一法向上重算（不经过我自己的张量缩并写法）
    e_mod = float(E_normal(C, np.asarray(de, float),
                           np.asarray(n_p, float)[None, :])[0])
    # 量纲尺度：二次型 `0.5·Δε:Λ:Δε` 的一个**稳健**上界
    #   `0.5 · max|Λ_ijkl| · (Σ|Δε_ij|)²  ≥  0.5·|Δε:Λ:Δε|`
    # 不用 `E([1,0,0])` 做尺度 —— 它对某些对恰好≈0（相消），会把比值炸到 1e293。
    _L = _lam_full(C, np.asarray(n_p, float))
    e_scale = 0.5 * float(np.abs(_L).max()) * float(np.abs(de).sum()) ** 2
    rows.append((k, l, r, float(E_min), float(cert), float(e_chk),
                 np.asarray(n_p), float(e_mod), r2, e_scale))
    if len(rows) % 12 == 0:
        print('   …已算 %d/66' % len(rows), flush=True)

rs = np.array([x[2] for x in rows])
rs2 = np.array([x[8] for x in rows])
em = np.array([x[3] for x in rows])
chk = np.array([x[5] for x in rows])
emod = np.array([x[7] for x in rows])
esc = np.array([x[9] for x in rows])

# C-3 正对照（三条，必须都过）
rel = np.abs(chk - em) / np.maximum(np.abs(em), 1e-300)
scaled = np.abs(chk - emod) / np.maximum(esc, 1e-300)
rel_mod = np.abs(emod - em) / np.maximum(np.abs(em), 1e-300)
print('\nC-3a 正对照（我的张量缩并 vs `argmin_normal` 返回的 `E_min`）：')
print('   相对差：中位 %.3e  最大 %.3e  ⇒ %s'
      % (float(np.median(rel)), float(np.max(rel)),
         '✅ 自洽' if np.max(rel) < 1e-6 else '⚠ 相对差超 1e-6（见下一行）'))
print('C-3a′ 同一差用**稳健能量尺度**（`0.5·max|Λ|·(Σ|Δε|)²`）无量纲化：')
print('   中位 %.3e  最大 %.3e  ⇒ %s'
      % (float(np.median(scaled)), float(np.max(scaled)),
         '✅ 是浮点累加/相消噪声，非约定错误'
         if np.max(scaled) < 1e-13 else '⚠ 存在真实差异'))
print('   （`E_min` 跨 9 个量级、最小的 4.19e-04 是两个大量相消得到的，')
print('    因此用**相对 E_min** 的差评判会把 1e-16 的浮点噪声放大成 1e-4。）')
print('C-3b 正对照（**模型自己的** `E_normal` 在同一 `ncmp` 上重算）：')
print('   相对差：中位 %.3e  最大 %.3e  ⇒ %s'
      % (float(np.median(rel_mod)), float(np.max(rel_mod)),
         '✅ 逐位相同' if np.max(rel_mod) == 0.0 else '⚠ 不自洽 —— 结论作废'))

# C-3c 扰动检查：`ncmp` 必须是**真正的局部极小**（在其邻域内能量不下降）
_rng = np.random.default_rng(11)
_defect = 0
_worst = 0.0
for x in rows:
    n_p = x[6]
    d = _rng.normal(size=(200, 3))
    d -= (d @ n_p)[:, None] * n_p[None, :]          # 切向扰动
    d /= np.linalg.norm(d, axis=1)[:, None]
    for amp in (1e-4, 1e-2):
        cand = n_p[None, :] + amp * d
        cand /= np.linalg.norm(cand, axis=1)[:, None]
        v = np.asarray(E_normal(C, np.asarray(E[x[0] - 1] - E[x[1] - 1], float),
                                cand), float)
        drop = float(np.min(v) / max(x[3], 1e-300) - 1.0)
        _worst = min(_worst, drop)
        if drop < -1e-6:
            _defect += 1
print('C-3c 扰动检查（每对 400 个切向邻域点，振幅 1e-4 与 1e-2）：')
print('   能量下降的对数：%d/66   最深下降 %+.3e  ⇒ %s'
      % (_defect, _worst,
         '✅ `ncmp` 都是真局部极小' if _defect == 0 else '⚠ 有对不是极小 ⇒ 结论作废'))

# C-2 秩相关
def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return float(ra @ rb / np.sqrt((ra @ ra) * (rb @ rb)))


rho = spearman(rs, em)
rho2 = spearman(rs2, em)
def prho(tag, v):
    print('\nC-2 %s Spearman 秩相关 ρ = **%+.3f**' % (tag, v))
    print('   （若几何判据是微弹性的好代理，ρ 应接近 −1）')
    if v < -0.7:
        print('   ⇒ ✅ 几何判据可作代理')
    elif v < -0.3:
        print('   ⇒ ⚠ 只有弱相关 ⇒ 几何判据**不足以**替代微弹性判据')
    else:
        print('   ⇒ ⛔ **几何判据不能当微弹性的代理**（ρ 接近 0 或为正）')

prho('几何①（对称部分最佳 rank-1 残余 r）vs E_min：', rho)
prho('几何②（完整 ΔU 的 Hadamard σ₂/σ₁）vs E_min：', rho2)

# 分域：同 packet（6 对）vs 跨 packet（60 对）
SAME = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
_S = set(SAME)
msk = np.array([(x[0], x[1]) in _S for x in rows])
print('\nC-2′ 按域拆开看（**同 packet 的 6 对才是 block/colony 有关的对**）：')
for tag, m in (('同 packet  %2d 对' % int(msk.sum()), msk),
               ('跨 packet %2d 对' % int((~msk).sum()), ~msk)):
    if int(m.sum()) < 3:
        continue
    print('   %s ：ρ(几何①)=%+.3f   ρ(几何②)=%+.3f'
          % (tag, spearman(rs[m], em[m]), spearman(rs2[m], em[m])))
    print('      E_min 跨度 %.3e … %.3e' % (em[m].min(), em[m].max()))
    print('      几何① 取值集合 %s'
          % np.unique(np.round(rs[m], 6)).tolist())
    print('      几何② 取值集合 %s'
          % np.unique(np.round(rs2[m], 6)).tolist())

# C-2″ 分辨力：几何量到底有几个不同取值？（对 2 值变量算 ρ 没有意义）
u1, u2 = np.unique(np.round(rs, 6)), np.unique(np.round(rs2, 6))
print('\nC-2″ **分辨力检查**（这一步决定上面那些 ρ 能不能解释成"相关"）：')
print('   66 对里 几何① 只取 %d 个不同值：%s' % (len(u1), u1.tolist()))
print('   66 对里 几何② 只取 %d 个不同值：%s' % (len(u2), u2.tolist()))
print('   而 `E_min` 取 %d 个不同值（i.e. 几乎每对都不同），跨度 %.3e … %.3e（%.1f 个量级）'
      % (len(np.unique(em)), em.min(), em.max(), np.log10(em.max() / em.min())))
if len(u1) <= 3 or len(u2) <= 3:
    print('   ⇒ ⛔ **几何量是"近乎二值"的，不是连续预测子。**')
    print('     对只有 2 个取值的变量算 Spearman ρ，得到的是"两组均值之差"，')
    print('     **不能**读成"几何相容性预测微弹性相容性"（组内排序完全靠并列打破）。')
    print('     真正的结论是：**几何判据在本模型的 66 对上几乎没有分辨力**，')
    print('     本模型的配对判据是**各向异性微弹性**判据，不是几何 rank-1 判据。')

print('\nC-4 6 个同 packet 对：')
PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
print('   %-10s %10s %10s %14s  %s' % ('对', 'r(几何①)', 'σ₂/σ₁(②)', 'E_min(微弹性)', 'ncmp'))
for p in PAIRS:
    d = [x for x in rows if (x[0], x[1]) == p or (x[1], x[0]) == p]
    if not d:
        continue
    x = d[0]
    print('   V%-2d–V%-2d %10.4f %13.10f %14.4e  [%+.3f %+.3f %+.3f]'
          % (p[0], p[1], x[2], x[8], x[3], *x[6]))

print('\n（附）`E_min` 与 `r` 的极值对照：')
i_r = int(np.argmin(rs)); i_e = int(np.argmin(em))
print('   r 最小的对      ：V%-2d–V%-2d  r=%.4f  E_min=%.3e'
      % (rows[i_r][0], rows[i_r][1], rows[i_r][2], rows[i_r][3]))
print('   E_min 最小的对  ：V%-2d–V%-2d  r=%.4f  E_min=%.3e'
      % (rows[i_e][0], rows[i_e][1], rows[i_e][2], rows[i_e][3]))

# 落盘：66 对全表，供后续溯源
_out = os.path.join(HERE, '_exp', 'paircorr.csv')
with open(_out, 'w') as f:
    f.write('k,l,r_sym,sigma2_over_sigma1,E_min,argmin_cert,e_chk,e_mod,'
            'nx,ny,nz,e_scale\n')
    for x in rows:
        f.write('%d,%d,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,'
                '%.10g,%.10g,%.10g,%.10g\n'
                % (x[0], x[1], x[2], x[8], x[3], x[4], x[5], x[7],
                   x[6][0], x[6][1], x[6][2], x[9]))
print('\n已写出 `_exp/paircorr.csv`（66 行：两种几何量 + `E_min` + `ncmp`）。')
print('   ⇒ %s' % ('两者**不是同一对**' if i_r != i_e else '两者是同一对'))
print('=' * 96)
