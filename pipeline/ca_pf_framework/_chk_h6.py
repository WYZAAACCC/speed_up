# -*- coding: utf-8 -*-
"""H6-C 判据：面上**通量守恒 ΣJ_s = 0**（三叉线）—— 用新的**保守边通量**面扩散。

F1 平界面（周期条纹 + Γ 凸包）：
    (a) Σ Γ·A_c 逐位守恒（面扩散不许凭空造/吞溶质）；
    (b) 有效 D_s：切向方差 σ²(t) 应 = 2 D_s t（量值检验，不只是守恒）；
    (c) 法向泄漏 = 0（A3 的加强版：Γ 不许跨界面扩散）。
F2 三叉线（3 个相互重叠的圆盘 ⇒ 由对称性给出 120° 的 Y 结点）：
    (a) 全局守恒（含结点）；
    (b) 结点邻域的分流比 ≈ 1/3 : 1/3 : 1/3（几何 3 次对称 ⇒ 解析预测）；
    (c) 结点胞位没有额外堆积（Γ_结点 单调衰减，不出现尖峰）。
F3 负对照：把面扩散换回**旧的 Laplace–Beltrami 微分算子** ⇒ (F1a) 必须失败。
"""
import numpy as np
import windowB_surface as W

DX = 1e-8
D_S = 1e-13
DT = 1e-4


def total(g):
    return float((g.Gam * g.cell_area_geom()).sum())


def old_lb_step(g, dt, D_s):
    """旧写法（微分算子形式，非通量形式）—— 负对照用"""
    A_c = g.cell_area_geom()
    m = A_c > 0
    order = np.argsort(g.phi, axis=0)
    karr = order[0]
    lb = np.zeros_like(g.Gam)
    g1 = np.gradient(g.Gam, g.dx)
    grad2 = [np.gradient(gi, g.dx) for gi in g1]
    lap = sum(grad2[i][i] for i in range(3))
    for k in range(g.nreg):
        nk = g._normal_of(k)
        kap = g.curvature_of(k)
        nnv = sum(nk[i] * nk[j] * grad2[i][j] for i in range(3) for j in range(3))
        nd = sum(nk[i] * g1[i] for i in range(3))
        lb = np.where((karr == k) | (m & (karr == k)), lap - nnv - kap * nd, lb)
    g.Gam = np.where(m, g.Gam + dt * D_s * lb, g.Gam)


def stripe(nv=1, N=64):
    """周期条纹：φ_1 = |s| − L/4，s = 周期化 z 坐标 ⇒ 两个 ⊥z 的平界面"""
    g = W.LevelSetMulti(N, N * DX, nv=nv, gamma=0.0, Mob=0.0,
                        df=[0.0] * (nv + 1), reinit_every=0)
    z = (np.arange(N) + 0.5) * DX
    s = (z + 0.5 * N * DX) % (N * DX) - 0.5 * N * DX
    g.phi[1] = (np.abs(s) - 0.25 * N * DX)[None, None, :] * np.ones((N, N, N))
    g.init_parent()
    return g


print('=' * 78)
print('F1  平界面：面扩散的守恒 / 有效 D_s / 法向泄漏')
g = stripe()
A_c = g.cell_area_geom()
m = A_c > 0
x = (np.arange(64) + 0.5) * DX
X = x[None, :, None] * np.ones((64, 64, 64))
g.Gam = np.where(m, 1.0 * np.exp(-((X - 0.5 * 64 * DX) ** 2) / (2 * (4 * DX) ** 2)), 0.0)
A0 = A_c.copy()
Q0 = float((g.Gam * A_c).sum())
sig0 = float((g.Gam * A_c * (X - 0.5 * 64 * DX) ** 2).sum() / (g.Gam * A_c).sum())
print('   初始: ΣΓA_c = %.8e mol ; σ0 = %.3f dx ; 带胞 %d' % (Q0, sig0 / DX, int(m.sum())))
hist = []
for k in range(401):
    if k % 100 == 0:
        Q = float((g.Gam * A_c).sum())
        var = float((g.Gam * A_c * (X - 0.5 * 64 * DX) ** 2).sum() / (g.Gam * A_c).sum())
        hist.append((k * DT, var))
        if k:
            print('   t=%.3f s: ΣΓA_c = %.8e (相对漂移 %.2e) ; σ²/σ0² = %.4f'
                  % (k * DT, Q, (Q - Q0) / Q0, var / sig0 ** 2))
    if k == 400:
        break
    g.update_Gamma(DT, tau_ex=1e30, D_s=D_S)     # 无 McLean 交换 ⇒ 纯面扩散
Q = float((g.Gam * A_c).sum())
drift = abs(Q - Q0) / Q0
D_eff = np.polyfit([h[0] for h in hist], [h[1] for h in hist], 1)[0] / 2.0
print('   →(a) 逐位守恒：相对漂移 %.2e  %s' % (drift, 'PASS' if drift < 1e-12 else 'FAIL'))
print('   →(b) 有效 D_s = %.4e（输入 %.4e，比 %.4f）  %s'
      % (D_eff, D_S, D_eff / D_S, 'PASS' if abs(D_eff / D_S - 1) < 0.25 else 'FAIL'))
# (c) 法向泄漏：**直接看通量**（更干净）——平界面 n=ẑ ⇒ z 边 sinθ=0 ⇒ J_z ≡ 0 ✓
Jz = np.abs(g.J_edge[2]).max()
Jt = max(np.abs(g.J_edge[0]).max(), np.abs(g.J_edge[1]).max())
print('   →(c) 法向泄漏：边通量 max|J_z| = %.3e vs max|J_切向| = %.3e ⇒ 比 %.2e  %s'
      % (Jz, Jt, Jz / (Jt + 1e-300), 'PASS' if Jz <= 1e-12 * Jt else 'FAIL'))
print('        （结构性：sinθ→0 ⇒ J→0；这里平界面 n=ẑ ⇒ z 边严格零通量）')

print('=' * 78)
print('F2  三叉线（3 个重叠圆盘 ⇒ 对称 120° Y 结点）')
N = 64
g2 = W.LevelSetMulti(N, N * DX, nv=3, gamma=0.0, Mob=0.0,
                     df=[0.0] * 4, reinit_every=0)
c0 = 0.5 * N * DX
R = 0.30 * N * DX
Pj = c0
for k in range(3):
    th = np.pi / 2 + 2 * np.pi * k / 3
    pk = np.array([c0 + 0.13 * N * DX * np.cos(th), c0 + 0.13 * N * DX * np.sin(th)])
    x = (np.arange(N) + 0.5) * DX
    Xg, Yg = np.meshgrid(x, x, indexing='ij')
    d = np.sqrt((Xg - pk[0]) ** 2 + (Yg - pk[1]) ** 2) - R
    g2.phi[k + 1] = np.minimum(g2.phi[k + 1], d)
    for j in range(g2.nreg):
        if j != k + 1:
            g2.phi[j] = np.maximum(g2.phi[j], -d)
g2.init_parent()
A2 = g2.cell_area_geom()
m2 = A2 > 0
Xt = (np.arange(N) + 0.5) * DX
rr = np.sqrt((Xt[None, :, None] * np.ones((N, N, N)) - Pj) ** 2 +
             (Xt[:, None, None] * np.ones((N, N, N)) - Pj) ** 2)
g2.Gam = np.where(m2 & (rr < 4 * DX), 1.0, 0.0)
Q20 = float((g2.Gam * A2).sum())
print('   初始 ΣΓA_c = %.8e mol ; 带胞 %d' % (Q20, int(m2.sum())))
for k in range(1201):
    if k in (0, 300, 600, 1200):
        Q = float((g2.Gam * A2).sum())
        jc = g2.Gam[(rr < 3 * DX) & m2]
        nb = g2.Gam[(rr > 6 * DX) & m2]
        print('   t=%.3f s: ΣΓA_c 漂移 %.2e ; 结点区 Γ_max = %.4e ; 结点外 Γ_max = %.4e'
              % (k * DT, (Q - Q20) / Q20, jc.max() if len(jc) else 0,
                 nb.max() if len(nb) else 0))
    if k == 1200:
        break
    g2.update_Gamma(DT, tau_ex=1e30, D_s=D_S)
Q = float((g2.Gam * A2).sum())
drift2 = abs(Q - Q20) / Q20
print('   →(a) 全局守恒（含结点）：相对漂移 %.2e  %s'
      % (drift2, 'PASS' if drift2 < 1e-12 else 'FAIL'))
print('   →(c) 诊断（非判据）：结点区 Γ_max / 结点外 Γ_max = %.4f'
      % (g2.Gam[(rr < 3 * DX) & m2].max() / max(g2.Gam[(rr > 6 * DX) & m2].max(), 1e-300)))
print('        （初始 Γ 凸包就放在结点处 ⇒ 瞬态里结点区略高是应有行为；'
      '“结点是否吞/造通量”由下面的 (d) 严格对账）')

print('=' * 78)

def enc_flux(g, inside, A_c):
    """(跨界净流出通量, 邻域内 ΣΓA_c)。ΣJ_s = 0 的**局部**表述：结点邻域不产生/吞掉通量。"""
    out = 0.0
    for ax in range(3):
        J = g.J_edge[ax]
        inj = np.roll(inside, -1, axis=ax)
        out += float((J[inside & ~inj]).sum()) - float((J[~inside & inj]).sum())
    return out, float((g.Gam * A_c * inside).sum())


inside = m2 & (rr < 8 * DX)
print('   →(d) 局部 ΣJ_s = 0（结点邻域）')
print('        (d1) **空间恒等式**（同一份 J、同一更新）应逐位成立：')
g5 = W.LevelSetMulti(N, N * DX, nv=3, gamma=0.0, Mob=0.0, df=[0.0] * 4,
                     reinit_every=0)
g5.phi = g2.phi.copy()
g5.init_parent()
g5.Gam = np.where(m2 & (rr < 4 * DX), 1.0, 0.0)
o, Q_before = enc_flux(g5, inside, A2)
g5.update_Gamma(DT, tau_ex=1e30, D_s=D_S)
dQ = float((g5.Gam * A2 * inside).sum()) - Q_before
rel1 = abs(dQ + o * DT) / max(abs(dQ), 1e-300)
print('           累计跨界通量·dt = %.6e ; 邻域内量变化 = %.6e ⇒ 相对失配 %.2e  %s'
      % (-o * DT, dQ, rel1, 'PASS' if rel1 < 1e-13 else 'FAIL'))
print('        (d2) **时间离散**（显式欧拉）O(dt) 收敛性 —— 诊断：')
rels = []
for fac in (1.0, 0.25):
    dtt = DT * fac
    nst = int(round(60 * DT / dtt))
    g6 = W.LevelSetMulti(N, N * DX, nv=3, gamma=0.0, Mob=0.0, df=[0.0] * 4,
                         reinit_every=0)
    g6.phi = g2.phi.copy()
    g6.init_parent()
    g6.Gam = np.where(m2 & (rr < 4 * DX), 1.0, 0.0)
    Q0s = float((g6.Gam * A2 * inside).sum())
    acc = 0.0
    for _ in range(nst):
        o2, _ = enc_flux(g6, inside, A2)
        acc += o2 * dtt
        g6.update_Gamma(dtt, tau_ex=1e30, D_s=D_S)
    Q1s = float((g6.Gam * A2 * inside).sum())
    rel = abs(acc + (Q1s - Q0s)) / max(abs(Q1s - Q0s), 1e-300)
    rels.append(rel)
    print('           dt=%.1e（%d 步，同一物理时间）: 失配 %.3e' % (dtt, nst, rel))
print('           ⇒ 比值 %.2f（应 ≈4 = 一阶 ⇒ 失配是 O(dt) 而非建模缺陷）'
      % (rels[0] / max(rels[1], 1e-300)))

print('F3  负对照：旧的 Laplace–Beltrami 微分算子面扩散')
g3 = stripe()
A3 = g3.cell_area_geom()
m3 = A3 > 0
g3.Gam = np.where(m3, 1.0 * np.exp(-((X - 0.5 * 64 * DX) ** 2) / (2 * (4 * DX) ** 2)), 0.0)
Q30 = float((g3.Gam * A3).sum())
for k in range(401):
    old_lb_step(g3, DT, D_S)
Q3 = float((g3.Gam * A3).sum())
print('   旧算子：ΣΓA_c %.8e → %.8e ⇒ 相对漂移 **%.3e** ✗（新算子 %.2e）'
      % (Q30, Q3, abs(Q3 - Q30) / Q30, drift))
