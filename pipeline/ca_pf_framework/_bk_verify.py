#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_verify.py —— 阶段 1（BLOCK_DERIVATION.md）的**数值自检**。

对应 BLOCK_DERIVATION.md 附录 A 的三项核验 + §3.2/§6.6 的每一个数。
**每一条都必须打印 PASS/FAIL**；任何 FAIL 都表示推导文档里的某个数是错的。

跑法：  python3 _bk_verify.py
"""
import numpy as np

FAIL = []


def chk(tag, ok, detail=''):
    print('%-46s %s  %s' % (tag, 'PASS' if ok else '**FAIL**', detail))
    if not ok:
        FAIL.append(tag)


def rodrigues(w):
    """旋转矢量 -> 旋转矩阵（exp([w]_x)）"""
    w = np.asarray(w, float)
    th = np.linalg.norm(w)
    if th < 1e-300:
        return np.eye(3)
    k = w / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def rot_angle(R):
    c = np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)
    return float(np.arccos(c))


# =====================================================================
print('=' * 78)
print('A-1  hcp 点群（D6, 12 个真转动）下的小角 disorientation == 裸角？')
print('=' * 78)


def d6_ops():
    """hcp 的**真转动**子群 = D6（阶 12）：C6z^k 与 C6z^k·C2x。
       生成元：绕 z 转 60°，绕 x 转 180°。"""
    C6 = rodrigues([0, 0, np.pi / 3])
    C2 = rodrigues([np.pi, 0, 0])
    ops = []
    M = np.eye(3)
    for _ in range(6):
        ops.append(M.copy())
        ops.append(M @ C2)
        M = M @ C6
    return ops


OPS = d6_ops()
chk('A-1.0 |D6| == 12', len(OPS) == 12, 'n=%d' % len(OPS))
chk('A-1.1 每个 op 都是真转动 (det=+1)',
    all(abs(np.linalg.det(o) - 1) < 1e-12 for o in OPS))
chk('A-1.2 每个 op 都正交',
    all(np.allclose(o @ o.T, np.eye(3), atol=1e-12) for o in OPS))
_ang = sorted(round(np.degrees(rot_angle(o)), 6) for o in OPS)
chk('A-1.3 非恒等元的最小转角 == 60 deg',
    abs(_ang[1] - 60.0) < 1e-6, 'min non-identity=%g deg' % _ang[1])

rng = np.random.default_rng(20260929)
worst = 0.0
for _ in range(4000):
    wa = rng.normal(size=3)
    wa *= np.deg2rad(rng.uniform(0, 5.0)) / (np.linalg.norm(wa) + 1e-300)
    wb = rng.normal(size=3)
    wb *= np.deg2rad(rng.uniform(0, 5.0)) / (np.linalg.norm(wb) + 1e-300)
    Ra, Rb = rodrigues(wa), rodrigues(wb)
    dR = Ra @ Rb.T                                    # 同变体 => 变体转动约掉
    bare = rot_angle(dR)
    dis = min(rot_angle(g @ dR) for g in OPS)
    worst = max(worst, abs(dis - bare))
chk('A-1.4 min_g angle(g dR) == bare (theta<=5deg, 4000 组)',
    worst < 1e-12, 'max|diff|=%.3e rad' % worst)

# 变体转动共轭后仍然成立（式 2.3 的关键一步）
Rv = rodrigues([0.7, -1.1, 0.4] / np.linalg.norm([0.7, -1.1, 0.4]) * 1.05)
worst2 = 0.0
for _ in range(2000):
    wa = rng.normal(size=3); wa *= np.deg2rad(rng.uniform(0, 5)) / np.linalg.norm(wa)
    wb = rng.normal(size=3); wb *= np.deg2rad(rng.uniform(0, 5)) / np.linalg.norm(wb)
    dR = Rv @ (rodrigues(wa) @ rodrigues(wb).T) @ Rv.T
    worst2 = max(worst2, abs(min(rot_angle(g @ dR) for g in OPS) - rot_angle(dR)))
chk('A-1.5 变体转动共轭后结论不变（式 2.3）',
    worst2 < 1e-12, 'max|diff|=%.3e rad' % worst2)

# =====================================================================
print()
print('=' * 78)
print('A-2  Read-Shockley 面能：E0 / gamma_m / 表 3.1 / C1 连续')
print('=' * 78)

a_al = 0.2950e-9          # m   [文献]
E_mod, nu = 114.0e9, 0.34  # Pa   [文献]
G = E_mod / (2 * (1 + nu))
b = a_al                   # |b| = a_alpha for a/3<11-20>
E0 = G * b / (4 * np.pi * (1 - nu))
th_m = np.deg2rad(15.0)
gm = E0 * th_m

chk('A-2.1 G == 42.54 GPa', abs(G / 1e9 - 42.537) < 5e-3, 'G=%.4f GPa' % (G / 1e9))
chk('A-2.2 E0 == 1.5130 J/m2', abs(E0 - 1.51300) < 5e-5, 'E0=%.6f' % E0)
chk('A-2.3 gamma_m == 0.396 J/m2', abs(gm - 0.39575) < 5e-4, 'gm=%.6f' % gm)


def gRS(th_deg):
    th = np.deg2rad(np.asarray(th_deg, float))
    x = np.clip(th / th_m, 1e-300, None)
    return np.where(x >= 1.0, gm, gm * x * (1.0 - np.log(x)))


TBL = [(0.5, 0.058), (1.0, 0.098), (1.83, 0.150), (2.0, 0.159),
       (3.0, 0.207), (5.0, 0.277), (10.0, 0.371), (15.0, 0.396)]
ok = True
for th, ref in TBL:
    got = float(gRS(th))
    if abs(got - ref) > 1e-3:
        ok = False
        print('   theta=%5.2f  doc=%.3f  calc=%.6f  **MISMATCH**' % (th, ref, got))
chk('A-2.4 表 3.1 八档与文档逐档一致', ok)

# [占位] gamma_lath = 0.15 反查 theta
from scipy.optimize import brentq
th_eq = brentq(lambda t: float(gRS(t)) - 0.15, 0.1, 14.0)
chk('A-2.5 gamma_lath=0.15 [占位] <=> theta=1.83 deg',
    abs(th_eq - 1.83) < 0.005, 'theta_eq=%.3f deg' % th_eq)

# C1 连续（P2）：左右导数 + 值
eps = 1e-6
dL = (float(gRS(15.0 - eps)) - float(gRS(15.0))) / (-eps)
dR = (float(gRS(15.0 + eps)) - float(gRS(15.0))) / (eps)
chk('A-2.6 gamma_RS 在 theta_m 处 C1 连续 (P2)',
    abs(dL) < 1e-6 and abs(dR) < 1e-9, "d-=%+.2e d+=%+.2e" % (dL, dR))
chk('A-2.7 gamma_RS(0) == 0 (P1)', abs(float(gRS(1e-9))) < 1e-9)

# =====================================================================
print()
print('=' * 78)
print('§4.4  润湿判据与 gamma_ab 的文献值')
print('=' * 78)

GAB = {  # Murzinova 2017 (Lett. Mater. 7(1) 55-59)
    '600C_lo': 0.298, '600C_hi': 0.429,
    '975C_lo': 0.201, '975C_hi': 0.337,
}
print('   %-10s %-10s %-10s %-10s' % ('case', 'g_ab', '2g_ab', '2g_ab/gm'))
for k, v in GAB.items():
    print('   %-10s %-10.3f %-10.3f %-10.3f   wets=%s'
          % (k, v, 2 * v, 2 * v / gm, 2 * v < gm))
chk('C-1 600C 两档均不润湿 (2g_ab > gm)',
    all(2 * v > gm for k, v in GAB.items() if k.startswith('600')))
chk('C-1 975C 也均不润湿（余量最小 %.3f x）'
    % min(2 * v / gm for k, v in GAB.items() if k.startswith('975')),
    all(2 * v > gm for k, v in GAB.items() if k.startswith('975')))
chk('文档"600C 余量 1.51-2.17x"',
    abs(min(2 * GAB['600C_lo'] / gm, 0) - 0) == 0
    and abs(2 * GAB['600C_lo'] / gm - 1.506) < 0.01
    and abs(2 * GAB['600C_hi'] / gm - 2.168) < 0.01,
    '%.3f - %.3f' % (2 * GAB['600C_lo'] / gm, 2 * GAB['600C_hi'] / gm))

# 体积项 (4.5)
DF = 3.5e8
DG_EL = 2.5e8
vol5 = 5e-9 * (DF - DG_EL)
chk('C-2 h=5nm 的体积项 == 0.5 J/m2', abs(vol5 - 0.5) < 1e-9, '%.3f' % vol5)

# =====================================================================
print()
print('=' * 78)
print('§6.6  不合并的定量论证（d_curv 与正对照）')
print('=' * 78)

N, dx, nstep = 192, 62.5e-9, 700
M0, bh, bw = 1.0e-9, 3.5, 2.3
dt = 0.15 * dx / (M0 * DF)
tsim = nstep * dt
Meff_n = M0 * np.exp(-bh)
Meff_w = M0 * np.exp(-bw)
kmax = 2.0 / dx
dcurv = Meff_n * gm * kmax * tsim
dtip = M0 * DF * tsim

chk('§6.6 dt(62.5nm) == 2.679e-8 s', abs(dt - 2.67857e-8) < 1e-12, 'dt=%.6e' % dt)
chk('§6.6 t_sim(700) == 1.875e-5 s', abs(tsim - 1.875e-5) < 1e-12, 'tsim=%.6e' % tsim)
chk('§6.6 M(n*)/M0 == 0.0302', abs(np.exp(-bh) - 0.030197) < 1e-5,
    '%.6f' % np.exp(-bh))
chk('§6.6 M(w)/M0  == 0.1003', abs(np.exp(-bw) - 0.100259) < 1e-5,
    '%.6f' % np.exp(-bw))
chk('§6.6 d_curv(最坏) == 7.17 nm', abs(dcurv * 1e9 - 7.175) < 0.01,
    '%.4f nm = %.4f dx' % (dcurv * 1e9, dcurv / dx))
d2 = dcurv * float(gRS(2.0)) / gm
chk('§6.6 d_curv(theta=2deg) == 2.88 nm', abs(d2 * 1e9 - 2.878) < 0.01,
    '%.4f nm = %.4f dx' % (d2 * 1e9, d2 / dx))
chk('§6.6 尖端正向位移 == 6.56 um', abs(dtip * 1e6 - 6.5625) < 1e-3,
    '%.4f um' % (dtip * 1e6))
chk('§6.6 对比度 == 915x', abs(dtip / dcurv - 914.6) < 0.5,
    '%.1f x' % (dtip / dcurv))
r5 = gm * (1.0 / (5 * dx)) / DF
rN = gm * kmax / DF
chk('§6.6 gamma*kappa/df 区间 0.36%-3.6%',
    abs(r5 * 100 - 0.362) < 0.01 and abs(rN * 100 - 3.62) < 0.01,
    '%.3f%% .. %.3f%%' % (r5 * 100, rN * 100))

# =====================================================================
print()
print('=' * 78)
print('A-3  psi 方程：不动点、稳定性、auto 退湿 (4.8)(4.9)')
print('=' * 78)


def fp(psi):
    return 6 * psi * (1 - psi)


def gp(psi):
    return 2 * psi * (1 - psi) * (1 - 2 * psi)


def rhs(psi, gdry, gf, W, L=1.0):
    return -L * (fp(psi) * (gf - gdry) + W * gp(psi))


GD, GF = 0.151, 0.60          # dry(gamma@1.84deg) vs wet film (2*g_ab, 600C 低档)
chk('A-3.1 psi=0 是不动点', abs(rhs(0.0, GD, GF, 0.05)) < 1e-15)
chk('A-3.2 psi=1 是不动点', abs(rhs(1.0, GD, GF, 0.05)) < 1e-15)

# 线性稳定性：psi=0 稳定 <=> 6*(gf-gdry) + 2W > 0
W = 0.05
lam0 = 6 * (GF - GD) + 2 * W
lam1 = -6 * (GF - GD) + 2 * W
chk('A-3.3 gamma_f>gamma_dry => psi=0 稳定 / psi=1 不稳定',
    lam0 > 0 and lam1 < 0, 'lam0=%+.3f lam1=%+.3f' % (lam0, lam1))
chk('A-3.4 psi=1 亚稳的条件 gamma_f-gamma_dry < W/3',
    abs((GF - GD) - 0.449) < 2e-3 and (GF - GD) > W / 3.0,
    'df=%.3f  W/3=%.4f' % (GF - GD, W / 3.0))

# auto 退湿：从 psi=1 出发积分
psi, dtp, hist = 1.0 - 1e-12, 1e-4, []
for _ in range(200000):
    k1 = rhs(psi, GD, GF, W)
    k2 = rhs(psi + 0.5 * dtp * k1, GD, GF, W)
    psi = psi + dtp * k2
    hist.append(psi)
    if psi < 1e-9:
        break
hist = np.array(hist)
chk('A-3.5 auto 从 psi=1 单调退湿到 0（P-2）',
    bool(np.all(np.diff(hist) <= 1e-12) and hist[-1] < 1e-6),
    'n=%d  psi_end=%.3e' % (len(hist), hist[-1]))

# 反向：gamma_f < gamma_dry => 应湿润
psi2, hist2 = 1e-12, []
for _ in range(200000):
    k1 = rhs(psi2, 0.60, 0.20, W)
    k2 = rhs(psi2 + 0.5 * dtp * k1, 0.60, 0.20, W)
    psi2 = psi2 + dtp * k2
    hist2.append(psi2)
    if psi2 > 1 - 1e-9:
        break
hist2 = np.array(hist2)
chk('A-3.6 反向对照：gamma_f<gamma_dry 时 psi->1（正对照）',
    bool(np.all(np.diff(hist2) >= -1e-12) and hist2[-1] > 1 - 1e-6),
    'n=%d  psi_end=%.6f' % (len(hist2), hist2[-1]))

# =====================================================================
print()
print('=' * 78)
print('§9  盒子与分辨率')
print('=' * 78)
chk('§9 N=192, dx=62.5nm => L=12 um', abs(N * dx * 1e6 - 12.0) < 1e-9)
chk('§9 板条厚 250nm @62.5nm == 4 胞', abs(250.0 / 62.5 - 4.0) < 1e-12)
chk('§9 R1 板条厚 250nm @125nm == 2 胞（原写 2.4 是 T=300nm）',
    abs(250.0 / 125.0 - 2.0) < 1e-12)
chk('§9 6 根堆叠跨距 6*250+5*62.5 == 1812.5 nm',
    abs(6 * 250 + 5 * 62.5 - 1812.5) < 1e-9)
chk('§9 nreg=1+6=7 <= 12 (int8 安全)', 7 <= 12)

print()
print('=' * 78)
print('FAIL 数 = %d' % len(FAIL))
if FAIL:
    for t in FAIL:
        print('   !! ' + t)
print('=' * 78)
raise SystemExit(1 if FAIL else 0)
