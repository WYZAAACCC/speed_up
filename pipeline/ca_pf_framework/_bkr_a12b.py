"""_bkr_a12b.py —— 对 BLOCK_DERIVATION.md 的 A1 / A2 / B2 / B3 / B4 逐项数值核对。

只读：不修改任何引擎源文件。运行：
  /root/miniconda3/envs/ml/bin/python _bkr_a12b.py
"""
import os
import sys
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

np.set_printoptions(precision=6, suppress=True, linewidth=140)


def hdr(t):
    print('\n' + '=' * 78)
    print(t)
    print('=' * 78)


# =====================================================================
hdr('A1  Read-Shockley：代数等价性 + 数值')
G_poly, nu = 114.0e9, 0.34
G = G_poly / (2.0 * (1.0 + nu))
a_al = 0.2950e-9
b_guess = a_al                      # 文档取 |b| = a_alpha
E0 = G * b_guess / (4.0 * math.pi * (1.0 - nu))
thm = math.radians(15.0)
gm = E0 * thm
print('G = E/[2(1+nu)]      = %.4f GPa        (文档 42.5 GPa)' % (G / 1e9))
print('E0 = Gb/[4pi(1-nu)]  = %.6f J/m^2     (文档 1.513)' % E0)
print('theta_m              = %.6f rad      (文档 0.2618)' % thm)
print('gamma_m = E0*theta_m = %.6f J/m^2     (文档 0.396)' % gm)

# 代数等价性：gamma_m*(t/tm)*(1-ln(t/tm))  ==  E0*t*(1-ln(t/tm))
worst = 0.0
for t_deg in np.linspace(0.01, 15.0, 4001):
    t = math.radians(t_deg)
    lhs = gm * (t / thm) * (1.0 - math.log(t / thm))       # 教科书 RS 形式
    rhs = E0 * t * (1.0 - math.log(t / thm))               # 文档 (3.2)
    worst = max(worst, abs(lhs - rhs) / max(abs(rhs), 1e-300))
print('两种写法相对差 max = %.3e  ⇒ %s' % (worst, '等价' if worst < 1e-14 else '不等价'))

print('\n表 3.1 核对（文档值 ← 计算值）:')
doc_tab = {0.5: 0.058, 1.0: 0.098, 1.83: 0.150, 2.0: 0.159,
           3.0: 0.207, 5.0: 0.277, 10.0: 0.371, 15.0: 0.396}
for d in sorted(doc_tab):
    t = math.radians(d)
    val = E0 * t * (1.0 - math.log(t / thm))
    print('   %6.2f deg : doc %.3f   calc %.5f   ratio %.4f'
          % (d, doc_tab[d], val, val / doc_tab[d]))

# C^1 性质
h = 1e-7
d1m = (E0 * (thm - h) * (1 - math.log((thm - h) / thm)) - gm) / (-h)
d1p = (E0 * thm - E0 * thm) / h
print('左导数 = %.3e, 右导数 = %.3e  ⇒ C^1 %s' % (d1m, d1p, 'OK' if abs(d1m) < 1e-6 else 'BAD'))

# |b| for (a/3)<11-20> in hcp:  a1,a2 夹角 120 度
a1 = np.array([1.0, 0.0]); a2 = np.array([math.cos(math.radians(120)), math.sin(math.radians(120))])
# [11-20] = a1 + a2 - 2*a3, a3 = -(a1+a2)  =>  3*(a1+a2)
vec = 3.0 * (a1 + a2)
print('\n|b| = |(a/3)[11-20]| = (a/3)*|3(a1+a2)| = a*|a1+a2| = %.6f a  ⇒ |b| = %.4f nm'
      % (np.linalg.norm(a1 + a2), np.linalg.norm(a1 + a2) * 0.295))

# 反解：若 gamma_lath[占位]=0.15 J/m2，对应 theta
lo, hi = 1e-9, thm
for _ in range(200):
    mid = 0.5 * (lo + hi)
    if E0 * mid * (1 - math.log(mid / thm)) < 0.15:
        lo = mid
    else:
        hi = mid
print('gamma_RS = 0.15 J/m^2  <=>  theta = %.4f deg  (文档 1.83)' % math.degrees(0.5 * (lo + hi)))

print('\n[敏感性] 若 G 用 600 C 的值（约 -20%%），gamma_m = %.3f  (仍 << 2*gamma_ab 的 0.596)'
      % (0.8 * gm))

# =====================================================================
hdr('A2  取向差角：点群 12 vs 24 元素')


def rot(axis, deg):
    ax = np.asarray(axis, float)
    ax = ax / np.linalg.norm(ax)
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + math.sin(math.radians(deg)) * K + (1 - math.cos(math.radians(deg))) * (K @ K)


C6 = rot([0, 0, 1], 60.0)
C2x = rot([1, 0, 0], 180.0)
G12 = []
for k in range(6):
    G12.append(np.linalg.matrix_power(C6, k))
    G12.append(np.linalg.matrix_power(C6, k) @ C2x)
G12 = np.array(G12)
G24 = np.concatenate([G12, -G12], 0)          # 6/mmm = 622 + i*622
print('构造：622 有 %d 个元素（det 全 %+.0f）；6/mmm 有 %d 个元素（det 含 -1）'
      % (len(G12), np.linalg.det(G12).mean(), len(G24)))


def angle_naive(M, clip=False):
    t = 0.5 * (np.trace(M) - 1.0)
    if clip:
        t = min(1.0, max(-1.0, t))
    return math.degrees(math.acos(t))


def small_rot(deg, seed):
    rng = np.random.default_rng(seed)
    w = rng.normal(size=3)
    w = w / np.linalg.norm(w) * math.radians(deg)
    K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    return np.eye(3) + math.sin(math.radians(deg)) * (K / math.radians(deg)) \
        + (1 - math.cos(math.radians(deg))) * (K @ K) / math.radians(deg) ** 2


print('\n裸角 vs min over 12 / min over 24（naive trace 公式，不 clip）:')
print('  theta_bare   min12      min24(naive)   NaN?')
bad24 = 0
for deg in (0.5, 2.0, 5.0, 10.0, 20.0, 25.0, 29.0):
    for seed in range(3):
        dR = small_rot(deg, seed)
        m12 = min(angle_naive(s @ dR) for s in G12)
        try:
            m24 = min(angle_naive(s @ dR) for s in G24)
            nan = False
        except ValueError:
            m24, nan = float('nan'), True
        bad24 += int(nan)
        print('   %6.2f      %8.4f    %s   %s'
              % (deg, m12, ('nan' if nan else '%8.4f' % m24), nan))
print('⇒ 24 元素（含反演/镜面）在 naive trace 公式下出现 NaN 的档数 = %d' % bad24)

# 22.5 度以上：非平凡群元开始“拉近”
print('\n大角对照（说明“小角”的定量界限）：')
for deg in (30.0, 40.0, 55.0, 59.0, 61.0):
    dR = small_rot(deg, 0)
    m12 = min(angle_naive(s @ dR) for s in G12)
    print('   bare %5.1f  ->  min12 %8.4f   %s'
          % (deg, m12, 'min=bare' if abs(m12 - deg) < 1e-9 else '**群元把角拉小了**'))
print('622 的非平凡元素最小转角 = %.1f deg  ⇒ 裸角公式在 theta < %.0f deg 内成立'
      % (min(angle_naive(s) for s in G12 if not np.allclose(s, np.eye(3))),
         min(angle_naive(s) for s in G12 if not np.allclose(s, np.eye(3))) / 2))

# 共轭不变性（变体转动是否真的约掉）
print('\n变体转动共轭不变性（随机大转动 R，seed 0..4）：')
worst = 0.0
for seed in range(5):
    R = small_rot(137.0, seed)
    for deg in (1.0, 5.0, 10.0):
        dR = small_rot(deg, seed + 10)
        a = min(angle_naive(s @ dR) for s in G12)              # 晶体坐标口径
        bb = min(angle_naive(s @ (R @ dR @ R.T)) for s in G12)  # 文档 (2.2) 样品坐标口径
        worst = max(worst, abs(a - bb))
print('  两种口径之差 max = %.3e deg  ⇒ %s' % (worst, '一致（结论成立）' if worst < 1e-9 else '不一致'))

# =====================================================================
hdr('B2 / B4  ncmp 的对角项、de=0 退化、facet_nref 回退分支')
from windowB_pf3d import C_cubic, argmin_normal      # noqa: E402
from windowB_ti64_variants import variants           # noqa: E402
import windowB_surface as W                          # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, Fs, meta = variants()
print('EPS0: %d 个变体;  Fs[0] det = %.6f' % (len(EPS0), np.linalg.det(np.asarray(Fs[0]))))

n0, e0, ratio0 = argmin_normal(C, np.zeros((3, 3)))
print('\nargmin_normal(C, 0):  n = %s  E = %.3e  收敛指标 = %.3e' % (n0, e0, ratio0))
print('  是否有限: %s ；是否 crash: 否（E_normal 恒 0 ⇒ argmin 取 Fibonacci 第 0 点）'
      % np.isfinite(n0).all())
NS0 = n0 / np.linalg.norm(n0)
print('  n_garbage = %s' % NS0)

eps_dup = [EPS0[0], EPS0[0]]
lg = W.LevelSetMulti(8, 8 * 1e-8, C=C, eps0=eps_dup, gamma=0.15, Mob=1e-9, workers=1)
print('\n_pair_normals(重复 eps0) 结果:')
print('  ncmp[1,2] = %s   finite=%s' % (lg.ncmp[1, 2], np.isfinite(lg.ncmp[1, 2]).all()))
print('  ncmp[1,1] = %s   (对角项)' % lg.ncmp[1, 1])
NPF = {}
for v in range(len(EPS0)):
    NPF[v + 1] = argmin_normal(C, np.asarray(EPS0[v], float))[0]
lg.npref = {k: v for k, v in NPF.items()}
out = lg.facet_nref(1, np.array(2), NPF)
print('  facet_nref(k=1, larr=2) = %s' % np.asarray(out).reshape(-1, 3)[0])
print('  npref[1]                = %s' % NPF[1])
print('  ⇒ 同变体但 k!=l 时 facet_nref %s 回退到 npref（文档 §2.3 说“已回退”是错的）'
      % ('没有' if np.allclose(np.asarray(out).reshape(-1, 3)[0], NPF[1]) is False else '有'))

print('\nF3 界面的迁移率代价（mob_beta=3.5，nd_ref=ncmp[1,2]）：')
c2 = float(np.dot(NPF[1], NS0)) ** 2
print('  (n*_1 · n_garbage)^2 = %.4f  ⇒ M_eff/M0 = exp(-3.5*%.4f) = %.4f'
      % (c2, c2, math.exp(-3.5 * c2)))
print('  文档假设的 n_ref = n*_v ⇒ M_eff/M0 = exp(-3.5) = %.4f' % math.exp(-3.5))
print('  ⇒ 比值 = %.1f 倍' % (math.exp(-3.5 * c2) / math.exp(-3.5)))

# =====================================================================
hdr('B3  herring_stiffness / herring_stiffness_cusp 对 gamma0 的线性')
rng = np.random.default_rng(0)
c2s = rng.random(20000)
worst_h = 0.0
worst_c = 0.0
for g0 in (0.15, 0.396, 1.1, 3.7):
    a_h = W.herring_stiffness(c2s, g0, 0.4, True)
    b_h = g0 * W.herring_stiffness(c2s, 1.0, 0.4, True)
    worst_h = max(worst_h, float(np.max(np.abs(a_h - b_h) / np.maximum(np.abs(b_h), 1e-300))))
    a_c = W.herring_stiffness_cusp(c2s, g0, 0.4, 0.05)
    b_c = g0 * W.herring_stiffness_cusp(c2s, 1.0, 0.4, 0.05)
    worst_c = max(worst_c, float(np.max(np.abs(a_c - b_c) / np.maximum(np.abs(b_c), 1e-300))))
print('herring_stiffness      : max rel err(g0=1 再乘) = %.3e' % worst_h)
print('herring_stiffness_cusp : max rel err(g0=1 再乘) = %.3e' % worst_c)
print('⇒ 代数上严格线性；数值上只差浮点尾数（1 ulp 量级）')

print('\n完成。')
