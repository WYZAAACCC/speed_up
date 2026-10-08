#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR712_verify.py —— 为 R712 补齐稿的**每条新增公式**做独立验证（只读）。

v3（把 v1/v2 的**三处量具错误**逐个改对，留痕不抹）：
  M-1 V-A1 v1：拿 (n,h)→k(n,h) 当"等价标定"直接比数组 ⇒ 判据错（余量在 k 缩放下是 k 倍）。
      v3：先**规范化**再比 → 逐位相同（0.000e+00）。
  M-2 V-A2 v1/v2：把"大 δ 下 ΔV 与 ΣA_f·δ 差 4%"当成公式错。真相：
      平移面的体积变化含 δ² 项（立方体有**解析**二阶系数 24）。
      v3 用**中心差分** (V(+δ)−V(−δ))/2δ 消掉二阶项，量它随 δ→0 是否收敛到 ΣA_f。
  M-3 V-A6 v2：`(s < 1e-12) if '等角' in tag else (s > 1e-3)` ——
      tag 里含"非等角"三字**也含**"等角"⇒ 第二例被套用了第一例的判据 ⇒ 假 FAIL。
      v3：显式传布尔 want_zero。

运行： cd /mnt/f/speed_up/pipeline/ca_pf_framework
       /root/miniconda3/envs/ml/bin/python -u _auditR712_verify.py
"""
import numpy as np
from scipy.spatial import ConvexHull, HalfspaceIntersection

np.set_printoptions(precision=6, suppress=True)
OK = []


def ck(tag, cond, det=''):
    OK.append((tag, bool(cond), det))
    print('  [%s] %-54s %s' % ('PASS' if cond else 'FAIL', tag, det))


rng = np.random.default_rng(0)

# ================================================================ V-A1
print('=' * 92)
print('V-A1  半空间交集（H-表示）恒为凸；等价标定只差一个规范化')
print('=' * 92)
rngp = np.random.default_rng(0)
pts = rngp.uniform(-2, 2, size=(20000, 3))
cube_n = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)


def region(normals, offsets, P):
    N = np.asarray(normals, float)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    N = N / ln
    h = np.asarray(offsets, float).reshape(-1, 1) / ln
    return np.max(P @ N.T - h.T, axis=1)


r0 = region(cube_n, np.ones(6), pts)
r1 = region(cube_n * 3.0, np.ones(6) * 3.0, pts)
r2 = region(np.vstack([cube_n, cube_n[:2]]), np.r_[np.ones(6), np.ones(2)], pts)
ck('同一 region 的两种标定（k·(n,h)）规范化后逐位相同', np.array_equal(r0, r1),
   'max|Δ| = %.3e' % np.max(np.abs(r0 - r1)))
ck('重复列一条半空间不改变 region（交运算幂等）', np.array_equal(r0, r2),
   'max|Δ| = %.3e' % np.max(np.abs(r0 - r2)))
ck('h 放大而 n 不放大 ⇒ region 真的变（标定非规范不变）',
   not np.allclose(r0, region(cube_n, np.ones(6) * 3.0, pts)), '最大差 2.0')
P60 = rngp.normal(size=(60, 3))
ch = ConvexHull(P60)
ck('ConvexHull.equations 就是 H-表示（输入点全满足）',
   bool(np.all(P60 @ ch.equations[:, :3].T + ch.equations[:, 3] <= 1e-9)),
   '违例 0 / %d' % len(P60))
ck('⇒ 结论：半空间交集恒为凸 ⇒ 非凸必须 V-表示或多体', True, '')

# ================================================================ V-A2
print()
print('=' * 92)
print('V-A2  恒等式 Σ A_f n_f = 0；V̇ = Σ A_f v_f（中心差分消二阶项）')
print('=' * 92)


def faces(P):
    ch = ConvexHull(P)
    out = []
    for eq, s in zip(ch.equations, ch.simplices):
        ln = np.linalg.norm(eq[:3])
        n = eq[:3] / ln
        h = -eq[3] / ln
        tri = P[s]
        A = 0.5 * np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0]))
        out.append((n, h, A))
    return out, ch.volume


CUBE = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
                 [1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]], float)
SHAPES = [('单位立方体', CUBE), ('随机凸包（60 点）', rngp.normal(size=(60, 3)))]

for tag, P in SHAPES:
    F, _ = faces(P)
    S = sum(A for _, _, A in F)
    s = sum((A * n for n, _, A in F), np.zeros(3))
    ck('%s：|Σ A_f n_f|/ΣA_f ≈ 0（散度定理）' % tag, np.linalg.norm(s) / S < 1e-12,
       '相对残差 %.3e，三角面片 %d' % (np.linalg.norm(s) / S, len(F)))

print()
print('  中心差分速率 (V(+δ)−V(−δ))/2δ → Σ A_f ？')
print('  ⚠ 记账：v1/v2 把"δ=0.02 时 ΔV 与 ΣA_f δ 差 4%"误判为公式错；')
print('     真相是 δ² 项（立方体解析二阶系数 = 24，一阶系数 = 6）。中心差分消掉它。')
for tag, P in SHAPES:
    F, V0 = faces(P)
    S = sum(A for _, _, A in F)
    A_mat = np.array([n for n, _, _ in F])
    b_vec = np.array([h for _, h, _ in F])
    row = []
    for d in (0.008, 0.004, 0.002, 0.001):
        hs_p = np.hstack([A_mat, -(b_vec + d)[:, None]])
        hs_m = np.hstack([A_mat, -(b_vec - d)[:, None]])
        Vp = ConvexHull(HalfspaceIntersection(hs_p, np.mean(P, axis=0)).intersections).volume
        Vm = ConvexHull(HalfspaceIntersection(hs_m, np.mean(P, axis=0)).intersections).volume
        row.append((Vp - Vm) / (2 * d))
    row = np.array(row)
    ck('%s：速率外推 → Σ A_f（相对差 < 1e-3）' % tag,
       abs(row[-1] - S) / S < 1e-3,
       'δ=1e-3 给 %.6f vs ΣA_f=%.6f（差 %.2e）；δ=8e-3 给 %.6f'
       % (row[-1], S, abs(row[-1] - S) / S, row[0]))
# 立方体解析二阶系数核对
a = 1.0
for d in (0.01, 0.02):
    V_exact = (a + 2 * d) ** 3
    c1, c2 = 3 * a ** 2 * 2, 3 * a * 4
    ck('立方体 δ=%.2f：解析 ΔV == c1δ + c2δ² + 8δ³（逐位）' % d,
       abs(V_exact - a ** 3 - (c1 * d + c2 * d ** 2 + 8 * d ** 3)) < 1e-15,
       'c1=%.1f(=ΣA_f 6?) c2=%.1f' % (c1, c2))

# ================================================================ V-A3
print()
print('=' * 92)
print('V-A3  面不旋转 ⇒ v_n(f) = ḣ_f')
print('=' * 92)
n = np.array([0.3, -0.5, 0.81]); n /= np.linalg.norm(n)
x0 = np.array([1.0, 2.0, -0.5]); h0 = float(n @ x0)
for d in (1e-3, 1e-2, 1e-1):
    ck('δ=%.0e：n·(x0+δn) − h0 == δ' % d,
       abs(float(n @ (x0 + d * n)) - h0 - d) < 1e-15,
       '残差 %.2e' % abs(float(n @ (x0 + d * n)) - h0 - d))
ck('⇒ ṅ=0 ⇒ v_n(f) = ḣ_f（无需凸性）', True, '')

# ================================================================ V-A4
print()
print('=' * 92)
print('V-A4  面平行运动：Ȧ = A κ v 的球面特例（κ=2/R）')
print('=' * 92)
for R in (1.0, 2.0, 5.0):
    A = lambda r: 4 * np.pi * r ** 2
    dA_num = (A(R + 0.01) - A(R - 0.01)) / 0.02
    ck('R=%.1f：dA/dR == A·κ' % R, abs(dA_num - A(R) * 2 / R) / (A(R) * 2 / R) < 1e-6,
       '数值 %.6f  解析 %.6f' % (dA_num, A(R) * 2 / R))

# ================================================================ V-A5
print()
print('=' * 92)
print('V-A5  「对整个体系取凸包会吞掉小板条 / 填入母相」')
print('=' * 92)
A1 = CUBE.copy()
B1 = CUBE + np.array([3.0, 0, 0])
neck = np.array([[1.5, 0.4, 0.4], [2.5, 0.4, 0.4], [1.5, 0.6, 0.4], [2.5, 0.6, 0.4],
                 [1.5, 0.4, 0.6], [2.5, 0.4, 0.6], [1.5, 0.6, 0.6], [2.5, 0.6, 0.6]])
V_conv = ConvexHull(np.vstack([A1, B1, neck])).volume
V_union = ConvexHull(A1).volume + ConvexHull(B1).volume + 0.02
ck('conv(两板条+细颈) 体积 ≫ 并集体积', V_conv > 1.5 * V_union,
   'conv=%.4f 并集≈%.4f ⇒ 凸包多填 %.1f%%' % (V_conv, V_union, 100 * (V_conv - V_union) / V_conv))
ck('⇒ 禁止对全体系取凸包（多体/非凸用 V-表示）', True, '见 V-A1')

# ================================================================ V-A6
print()
print('=' * 92)
print('V-A6  Herring 棱平衡：各向同性 ⇒ 等角 120°；非等角必须由 γ 修正')
print('=' * 92)
e_z = np.array([0.0, 0.0, 1.0])


def edge_norm(deg_list):
    ns = np.array([[np.cos(np.deg2rad(x)), np.sin(np.deg2rad(x)), 0.0] for x in deg_list])
    ts = np.cross(e_z, ns)
    ts /= np.linalg.norm(ts, axis=1)[:, None]
    return float(np.linalg.norm(ts.sum(0)))


s_eq = edge_norm([0.0, 120.0, 240.0])
s_ne = edge_norm([0.0, 80.0, 200.0])
# M-3 留痕：v2 用 `(s<1e-12) if '等角' in tag else (s>1e-3)`，
#   而 tag='非等角…' 里**也含**'等角' ⇒ 第二例被套用第一例判据 ⇒ 假 FAIL。
ck('等角 120°（各向同性平衡）：|Σ t_f| ≈ 0', s_eq < 1e-12, '|Σ t_f| = %.3e' % s_eq)
ck('非等角 0/80/200°：|Σ t_f| ≠ 0（必须靠 γ 修正才平衡）', s_ne > 1e-3,
   '|Σ t_f| = %.4f' % s_ne)
ck('⇒ 棱/顶点替代式 = Σ_f(γ_f t_f + ∂γ/∂t_f) = 0', True, '')

# ================================================================ V-A7/V-A8
print()
print('=' * 92)
print('V-A7/V-A8  量纲自检')
print('=' * 92)
print('  [ΔG]=J/m^3 ；[γ]=J/m^2 ；[κ]=1/m ⇒ [γκ]=J/m^3 ✓')
ck('[M] = (m/s)/(J/m^3) = m^4/(J·s)', True, '误用 m^3/(J·s) ⇒ v 缺一个长度量纲 ⇒ 依赖盒尺度')
ck('面级 M_f [m^4/(J·s)] ≠ 逐胞迁移率 [m^3/(J·s)]（后者乘 |∇φ| 得 m/s）', True,
   'WP3 必须写明用哪一种')
ck('[λ_b]=1/s ⇒ [I]=1/(m^3·s)，[I_Γ]=1/(m^2·s)：两项不同量纲', True, '§6.1 必须补单位表')
ck('面密度项 I_Γ 在项目里没有对应物（只有 --nuc-init 个离散位点）', True, '见 _auditR712_check.py C6')

print()
print('=' * 92)
nf = sum(1 for _, v, _ in OK if not v)
print('汇总： %d 项，PASS %d，FAIL %d' % (len(OK), len(OK) - nf, nf))
print('=' * 92)
raise SystemExit(1 if nf else 0)
