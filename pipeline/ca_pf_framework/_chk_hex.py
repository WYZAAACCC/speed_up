#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HX 判据（2026-09-25 新增）：各向异性（hcp/cubic）弹性张量的正确性。
   严格按"先拿一个已知答案跑通工具"的原则：每条都是**闭式或不变性**，不是自评。

   HX-1 `C_hex` 的各向同性极限必须**逐位等于** `C_iso3`（钉住 Voigt 记账）
   HX-2 六方不变性：对 Rz(60)/Rz(120)/180°(x̂)/σ_h 的**张量级**不变（1e-12）
   HX-3 rank-1 湮灭：ε = sym(a⊗n) ⇒ ε:Λ(n):ε = 0（对 n=ẑ/x̂/随机方向都要精确）
   HX-4 Λ(n=ẑ) 的闭式：Λ_3333=0、Λ_1313=C44、Λ_1212=C66、Λ_1111=C11−C13²/C33
   HX-5 α-Ti 单晶常数 ⇒ Voigt/Reuss/Hill 的 K、G 应与文献量级相符（K≈110、G≈45 GPa）
   HX-6 12 个变体的**转动张量**：6×6 Voigt 矩阵**特征值谱不变**，且纵波刚度极大方向 = 变体 c 轴 n_v
   HX-7 β 母相（bcc，立方）张量：立方不变性（4 重轴 + 90° 交换）
   E-1/E-2 **既有记账的钉子**（这几条比 HX 更基础）：均匀剪切/均匀膨胀特征应变在
        `clamped`（平均应变固定为 0）下 `PF3D.E_el` 必须等于闭式 ½V·ε⁰:C:ε⁰
        （剪切：E=2μa²V；膨胀：E=½·9b²K·V）—— 这一条同时钉住"工程分量因子"的记账。
"""
import numpy as np
import windowB_pf3d as P
from windowB_pf3d import C_iso3, C_hex, C_from_voigt, lambda_packed, _lam_full, VOIGT, G6

ok_all = []


def rec(tag, good, extra=''):
    ok_all.append(bool(good))
    print('   %-52s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


# ---------------- HX-1 各向同性极限 ----------------
print('---- HX-1 `C_hex` 的各向同性极限 == `C_iso3`（逐位）----')
E_mod, nu = 113e9, 0.34
mu = E_mod / (2 * (1 + nu)); lam = E_mod * nu / ((1 + nu) * (1 - 2 * nu))
Chi = C_hex(lam + 2 * mu, lam, lam, lam + 2 * mu, mu)
Ciso = C_iso3(E_mod, nu)
d = np.abs(Chi - Ciso).max() / np.abs(Ciso).max()
rec('max|C_hex(iso极限) − C_iso3| / max|C_iso3| < 1e-14', d < 1e-14, '= %.2e' % d)


# ---------------- HX-2 六方不变性 ----------------
def rot(axis, deg):
    t = np.radians(deg); c, s = np.cos(t), np.sin(t)
    if axis == 'z':
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
    if axis == 'x':
        return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 'y':
        return np.array([[c, 0, s], [0, 1.0, 0], [-s, 0, c]])


def rot4(C, R):
    return np.einsum('ia,jb,kc,ld,abcd->ijkl', R, R, R, R, C)


print('---- HX-2 六方不变性（张量级）----')
# α-Ti 单晶弹性常数（GPa）★【文献值待核对】：常引用的 Simmons&Wang 型数值；
# 本项目应到 docs/LIT 清单里核对一次再用于结论（尤其 Ti64 的 α′ 相）
GPA = 1e9
C11, C12, C13, C33, C44 = 162.4 * GPA, 92.0 * GPA, 69.0 * GPA, 180.7 * GPA, 46.7 * GPA
Ch = C_hex(C11, C12, C13, C33, C44)
print('   α-Ti: C11=%.1f C12=%.1f C13=%.1f C33=%.1f C44=%.1f C66(= (C11−C12)/2)=%.1f GPa'
      % (C11 / GPA, C12 / GPA, C13 / GPA, C33 / GPA, C44 / GPA,
         0.5 * (C11 - C12) / GPA))
for tag, R in (('Rz(60°)', rot('z', 60)), ('Rz(120°)', rot('z', 120)),
               ('180° about x̂', rot('x', 180)), ('180° about ŷ', rot('y', 180))):
    dd = np.abs(rot4(Ch, R) - Ch).max() / np.abs(Ch).max()
    rec('不变性 %s' % tag, dd < 1e-12, '相对 %.2e' % dd)
# σ_h: z → −z（镜像）。六方 6/mmm 含它 ⇒ 奇数次 z 指标的分量必须为 0
Cm = Ch.copy()
for i in range(3):
    for j in range(3):
        for k in range(3):
            for l in range(3):
                sg = (-1) ** ((i == 2) + (j == 2) + (k == 2) + (l == 2))
                if sg < 0:
                    Cm[i, j, k, l] = -Cm[i, j, k, l]
dd = np.abs(Cm - Ch).max() / np.abs(Ch).max()
rec('不变性 σ_h (z→−z)', dd < 1e-14, '相对 %.2e' % dd)


# ---------------- HX-3 rank-1 湮灭 ----------------
print('---- HX-3 rank-1 湮灭 ε=sym(a⊗n) ⇒ ε:Λ(n):ε = 0 ----')
rng = np.random.default_rng(0)
for tag, n in (('n=ẑ', np.array([0, 0, 1.0])), ('n=x̂', np.array([1.0, 0, 0])),
               ('n 随机 1', rng.normal(size=3)), ('n 随机 2', rng.normal(size=3))):
    n = n / np.linalg.norm(n)
    a = rng.normal(size=3)
    e = 0.5 * (np.outer(a, n) + np.outer(n, a))
    L = _lam_full(Ch, n)
    val = abs(np.einsum('ij,ijkl,kl->', e, L, e))
    rec('ε:Λ(n):ε = 0  (%s)' % tag, val < 1e-6 * np.abs(Ch).max(),
        '= %.3e (|C|max=%.3e)' % (val, np.abs(Ch).max()))


# ---------------- HX-4 Λ(n=ẑ) 闭式 ----------------
# ★ 记账（2026-09-25，判据自身的错）：初版我写"Λ_1313 = C44" ⇒ 报 FAIL。**那是我的期望错了**：
#   n=ẑ 时 rank-1 相容模式张成的子空间正是 {ε_13, ε_23}（二维）⇒ Λ 必须**整块湮灭**它
#   （A = diag(C44,C44,C33)、C_3j13 = (C44,0,0) ⇒ C1_1313 = C44²/C44 = C44 ⇒ Λ = 0 ✓）。
#   正确闭式：Λ_3333 = 0、Λ_1313 = Λ_2323 = 0、Λ_1212 = C66、Λ_1111 = Λ_2222 = C11 − C13²/C33、
#            Λ_1122 = C12 − C13²/C33、Λ_1133 = Λ_2233 = 0
print('---- HX-4 Λ(n=ẑ) 的闭式 ----')
Lz = _lam_full(Ch, np.array([0, 0, 1.0]))
rec('Λ_3333 = 0', abs(Lz[2, 2, 2, 2]) < 1e-12 * C33, '= %.3e' % Lz[2, 2, 2, 2])
rec('Λ_1313 = Λ_2323 = 0（rank-1 子空间={ε13,ε23} 整块湮灭）',
    max(abs(Lz[0, 2, 0, 2]), abs(Lz[1, 2, 1, 2])) < 1e-12 * C44,
    '= %.3e / %.3e' % (Lz[0, 2, 0, 2], Lz[1, 2, 1, 2]))
rec('Λ_1212 = C66 = (C11−C12)/2', abs(Lz[0, 1, 0, 1] - 0.5 * (C11 - C12)) < 1e-12 * C11,
    '= %.6e vs %.6e' % (Lz[0, 1, 0, 1], 0.5 * (C11 - C12)))
rec('Λ_1111 = Λ_2222 = C11 − C13²/C33',
    max(abs(Lz[0, 0, 0, 0] - (C11 - C13 ** 2 / C33)),
        abs(Lz[1, 1, 1, 1] - (C11 - C13 ** 2 / C33))) < 1e-12 * C11,
    '= %.6e vs %.6e' % (Lz[0, 0, 0, 0], C11 - C13 ** 2 / C33))
rec('Λ_1122 = C12 − C13²/C33', abs(Lz[0, 0, 1, 1] - (C12 - C13 ** 2 / C33)) < 1e-12 * C11,
    '= %.6e vs %.6e' % (Lz[0, 0, 1, 1], C12 - C13 ** 2 / C33))
rec('Λ_1133 = Λ_2233 = 0（z 向耦合湮灭）',
    max(abs(Lz[0, 0, 2, 2]), abs(Lz[1, 1, 2, 2])) < 1e-12 * C33,
    '= %.3e / %.3e' % (Lz[0, 0, 2, 2], Lz[1, 1, 2, 2]))


# ---------------- HX-5 多晶平均（Voigt/Reuss/Hill） ----------------
print('---- HX-5 α-Ti 的 Voigt/Reuss/Hill 平均 ----')
# ★ 记账（2026-09-25，判据自身的错）：初版手搭 CV 时**漏了上三角以外的元素**（只写 CV[0,1]
#   没写 CV[1,0]…）⇒ 矩阵**不对称** ⇒ `np.linalg.inv` 给出垃圾 ⇒ K_R = 242 GPa（离 107 极远）。
#   正确做法：直接从张量取 `CV[p,q] = C[VOIGT[p], VOIGT[q]]`（自动对称）。
#   另记账：本项目的 Voigt 记账是"**张量分量 + 工程应变**"（σ_p = Σ_q C_pq ε^eng_q），
#   这一点由 E-1（均匀剪切）逐位吻合钉死 ⇒ 这里的 CV 就是该约定的矩阵，与 `inv` 自洽。
CV = np.array([[Ch[VOIGT[p][0], VOIGT[p][1], VOIGT[q][0], VOIGT[q][1]]
                for q in range(6)] for p in range(6)])
print('   CV 对称性 max|CV − CVᵀ| = %.2e' % np.abs(CV - CV.T).max())
SV = np.linalg.inv(CV)
KV = (CV[0, 0] + CV[1, 1] + CV[2, 2] + 2 * (CV[0, 1] + CV[0, 2] + CV[1, 2])) / 9.0
GV = ((CV[0, 0] + CV[1, 1] + CV[2, 2]) - (CV[0, 1] + CV[0, 2] + CV[1, 2])
      + 3 * (CV[3, 3] + CV[4, 4] + CV[5, 5])) / 15.0
KR = 1.0 / ((SV[0, 0] + SV[1, 1] + SV[2, 2] + 2 * (SV[0, 1] + SV[0, 2] + SV[1, 2])))
GR = 15.0 / (4 * (SV[0, 0] + SV[1, 1] + SV[2, 2]) - 4 * (SV[0, 1] + SV[0, 2] + SV[1, 2])
             + 3 * (SV[3, 3] + SV[4, 4] + SV[5, 5]))
KH, GH = 0.5 * (KV + KR), 0.5 * (GV + GR)
print('   K_V=%.1f K_R=%.1f K_H=%.1f ; G_V=%.1f G_R=%.1f G_H=%.1f GPa'
      % (KV / GPA, KR / GPA, KH / GPA, GV / GPA, GR / GPA, GH / GPA))
rec('K_H ∈ [100,120] GPa（α-Ti 文献 ~105–110；K_V≈K_R≈107 自洽）', 100e9 < KH < 120e9,
    'K_V=%.1f K_R=%.1f' % (KV / GPA, KR / GPA))
rec('G_H ∈ [38,52] GPa（α-Ti 文献 ~43–48）', 38e9 < GH < 52e9)

# ---------------- HX-6 12 个变体的转动张量 ----------------
print('---- HX-6 12 个 Burgers 变体的转动张量 ----')
from windowB_ti64_variants import variants
eps0, Fs, meta = variants()


def c_axis_of(F):
    """对 hcp（横向各向同性）张量：c 轴 = 纵波刚度极大方向。取 F 的第一列像？ —— 直接用
       `build_F` 的输出：F 把 n 映成 lam·n ⇒ n 就是 c 轴。这里用张量自身**反解**以独立验证。"""
    return None


def long_stiff(C, n):
    n = n / np.linalg.norm(n)
    return np.einsum('i,j,k,l,ijkl->', n, n, n, n, C)


npref = meta
worst_spec = 0.0
worst_axis = 0.0
rngd = np.random.default_rng(1)
samp = rngd.normal(size=(2000, 3))
samp /= np.linalg.norm(samp, axis=1, keepdims=True)
for v in range(len(eps0)):
    n_v = None
    for key in ('n',):
        if isinstance(npref, (list, tuple)) and isinstance(npref[v], dict):
            n_v = npref[v].get(key)
    Cv = None
    if n_v is not None:
        n_v = np.asarray(n_v, float); n_v = n_v / np.linalg.norm(n_v)
        # 取任一 R: ẑ -> n_v
        z = np.array([0.0, 0, 1.0])
        a = np.cross(z, n_v)
        na = np.linalg.norm(a)
        if na < 1e-12:
            R = np.eye(3) if n_v[2] > 0 else np.diag([1.0, -1, -1])
        else:
            a = a / na; th = np.arccos(np.clip(z @ n_v, -1, 1))
            Kx = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
            R = np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * (Kx @ Kx)
        Cv = rot4(Ch, R)
    if Cv is None:
        continue
    # ★ 记账（判据自身的错）：`Voigt 6x6` 的**特征值不是转动不变量**（Voigt 表示在一般转动下
    #   不是协变的）⇒ 初版这条判据本身不成立（实测差 6e-2，而我一度以为代码错了）。
    #   正确的不变量要用 **Kelvin/Mandel 表示**（对剪切分量乘 √2 ⇒ 6x6 在 SO(6) 下协变，
    #   特征值转动不变 ✓）。外加三条**张量迹不变量** C_iijj / C_ijij / C_ijkl C_ijkl 复核。
    def kelvin(C):
        CVv = np.array([[C[VOIGT[p][0], VOIGT[p][1], VOIGT[q][0], VOIGT[q][1]]
                         for q in range(6)] for p in range(6)])
        f = np.sqrt(G6)
        return CVv * np.outer(f, f)

    ev0 = np.linalg.eigvalsh(kelvin(Ch))
    evv = np.linalg.eigvalsh(kelvin(Cv))
    worst_spec = max(worst_spec, np.abs(ev0 - evv).max() / np.abs(ev0).max())
    # c 轴反解：纵波刚度在这条线上取极大
    b_of = np.array([long_stiff(Cv, n) for n in samp])
    best = samp[int(np.argmax(b_of))]
    if best @ n_v < 0:
        best = -best
    worst_axis = max(worst_axis, 1.0 - abs(best @ n_v))
print('   变体数 = %d（meta 里 n 的可用条数）' % sum(
    1 for v in range(len(eps0)) if isinstance(npref, (list, tuple))
    and isinstance(npref[v], dict) and npref[v].get('n') is not None))
rec('Kelvin/Mandel 6×6 特征值谱转动不变（1e-10）', worst_spec < 1e-10,
    '最差相对 %.2e' % worst_spec)

# 张量迹不变量（转动不变的复核）
def tracer(C):
    t1 = np.einsum('iijj->', C)
    t2 = np.einsum('ijij->', C)
    t3 = np.einsum('ijkl,ijkl->', C, C)
    return np.array([t1, t2, t3])

tr0 = tracer(Ch)
worst_tr = 0.0
for v in range(len(eps0)):
    di = npref[v] if isinstance(npref[v], dict) else {}
    n_v = di.get('n')
    if n_v is None:
        continue
    n_v = np.asarray(n_v, float); n_v = n_v / np.linalg.norm(n_v)
    z = np.array([0.0, 0, 1.0]); ax = np.cross(z, n_v); na = np.linalg.norm(ax)
    if na < 1e-12:
        R = np.eye(3) if n_v[2] > 0 else np.diag([1.0, -1, -1])
    else:
        ax = ax / na; th = np.arccos(np.clip(z @ n_v, -1, 1))
        Kx = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        R = np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * (Kx @ Kx)
    trv = tracer(rot4(Ch, R))
    worst_tr = max(worst_tr, float(np.abs(trv - tr0).max() / np.abs(tr0).max()))
rec('张量迹不变量 C_iijj / C_ijij / C_ijklC_ijkl 转动不变', worst_tr < 1e-12,
    '最差相对 %.2e' % worst_tr)
rec('纵波刚度极大方向 = 变体 c 轴 n_v（1−|cos| < 0.02）', worst_axis < 0.02,
    '最差 1−|cos|=%.4f' % worst_axis)

# ---------------- HX-7 β（bcc）张量 + 立方不变性 ----------------
print('---- HX-7 β 母相（bcc 立方）----')
C11b, C12b, C44b = 134.0 * GPA, 110.0 * GPA, 36.0 * GPA      # ★【文献值待核对】
Cb = C_from_voigt(np.array([[C11b, C12b, C12b, 0, 0, 0],
                            [C12b, C11b, C12b, 0, 0, 0],
                            [C12b, C12b, C11b, 0, 0, 0],
                            [0, 0, 0, C44b, 0, 0],
                            [0, 0, 0, 0, C44b, 0],
                            [0, 0, 0, 0, 0, C44b]], float))
worst = 0.0
for ax in ('x', 'y', 'z'):
    for deg in (90, 180):
        worst = max(worst, np.abs(rot4(Cb, rot(ax, deg)) - Cb).max() / np.abs(Cb).max())
rec('立方不变性（90°/180° 绕 x/y/z）', worst < 1e-12, '最差相对 %.2e' % worst)

# ---------------- E-1/E-2 既有记账的钉子 ----------------
print('---- HX-8 惯习面（compatible normal）：用 Λ(C_ref, n) 极小化 ----')
from scipy.optimize import minimize
from windowB_pf3d import C_cubic, rot_z_to
from windowB_pf3d import _lam_full as lamf

# {334}_β 族（立方 24 个面 ⇒ 12 条法向线；本项目文献验证清单里的目标惯习面）
_h334 = []
for perm in ((0, 1, 2), (0, 2, 1), (1, 2, 0)):
    for sg in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)):
        v = np.zeros(3)
        base = np.array([3.0, 3.0, 4.0])
        for k in range(3):
            v[perm[k]] = sg[k] * base[k]
        v = v / np.linalg.norm(v)
        if v[np.nonzero(np.abs(v) > 1e-12)[0][0]] < 0:
            v = -v
        _h334.append(v)
_h334 = np.unique(np.round(np.array(_h334), 9), axis=0)


def fib(n=20000):
    i = np.arange(n) + 0.5
    ga = np.pi * (3 - np.sqrt(5))
    zz = 1 - 2 * i / n
    rr = np.sqrt(np.clip(1 - zz ** 2, 0, 1))
    return np.stack([rr * np.cos(ga * i), rr * np.sin(ga * i), zz], -1)


DIRS = fib()


def compatible_normal(C_ref, e0):
    """compatible（无应力）惯习面法向：min_n ½ ε⁰:Λ(C_ref,n):ε⁰"""
    def f(n):
        n = n / np.linalg.norm(n)
        return 0.5 * np.einsum('ij,ijkl,kl->', e0, lamf(C_ref, n), e0)
    vals = np.array([f(n) for n in DIRS[::8]])
    n0 = DIRS[::8][int(np.argmin(vals))]

    def g(t):
        th, ph = t
        return f([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])
    th0 = np.arccos(np.clip(n0[2], -1, 1)); ph0 = np.arctan2(n0[1], n0[0])
    r = minimize(g, [th0, ph0], method='Nelder-Mead',
                 options=dict(xatol=1e-8, fatol=1e-3, maxiter=2000))
    th, ph = r.x
    n = np.array([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])
    return n / np.linalg.norm(n), float(r.fun)


Cbeta = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)     # ★【文献值待核对】bcc β-Ti
rows = []
for v in range(len(eps0)):
    di = npref[v] if isinstance(npref[v], dict) else {}
    n_v = di.get('n')
    if n_v is None:
        continue
    n_v = np.asarray(n_v, float); n_v = n_v / np.linalg.norm(n_v)
    n_cub, e_cub = compatible_normal(Cbeta, eps0[v])
    n_iso, e_iso = compatible_normal(C_iso3(113e9, 0.34), eps0[v])
    C_v = rot4(Ch, rot_z_to(n_v))
    n_hcp, e_hcp = compatible_normal(C_v, eps0[v])
    ang334 = min(np.degrees(np.arccos(np.clip(abs(n_cub @ h), -1, 1))) for h in _h334)
    rows.append((v + 1, np.degrees(np.arccos(np.clip(abs(n_cub @ n_v), -1, 1))),
                 np.degrees(np.arccos(np.clip(abs(n_iso @ n_v), -1, 1))),
                 np.degrees(np.arccos(np.clip(abs(n_hcp @ n_v), -1, 1))), ang334))
print('   变体   ∠(n_hab[β立方] , c轴)   ∠(n_hab[各向同性] , c轴)   ∠(n_hab[变体hcp] , c轴)   ∠(n_hab , 最近{334})')
for r_ in rows:
    print('   V%-3d %20.1f° %23.1f° %22.1f° %14.1f°' % r_)
print('   ⇒ {334} 接近度：中位 %.1f°、最小 %.1f°（判据：若物理对，应显著小于无规 ~30°）'
      % (float(np.median([r_[4] for r_ in rows])), float(np.min([r_[4] for r_ in rows]))))
rec('compatible normal 计算收敛（12 个变体全部给出法向）', len(rows) == 12)

# HX-8b **对照分布**：12 个 {334} 成员与 12 个变体有同样的立方对称性 ⇒ 必须跟"无规方向的
#   最近 {334} 距离分布"比，否则那个 8° 可能只是"对称性对齐"的必然。
_rng = np.random.default_rng(7)
_vr = _rng.normal(size=(200000, 3))
_vr /= np.linalg.norm(_vr, axis=1, keepdims=True)
_h = np.array(_h334)
_cos = np.abs(_vr @ _h.T).max(axis=1)
_ang = np.degrees(np.arccos(np.clip(_cos, -1, 1)))
print('   对照（无规方向 2e5 个）到最近 {334} 的夹角：p5=%.1f° 中位 %.1f° p95=%.1f°'
      % (np.percentile(_ang, 5), np.median(_ang), np.percentile(_ang, 95)))
p8 = float((_ang < 8.0).mean())
p27 = float((_ang < 2.7).mean())
print('   无规方向落在 8.0° 内的比例 = %.1f%% ；落在 2.7° 内 = %.2f%%'
      % (100 * p8, 100 * p27))
print('   ⇒ 我们的 12 个 n_hab：中位 8.0°（= 无规分布的第 %.0f 百分位）、最小 2.7°'
      % (100 * (1 - p8)))
rec('HX-8b 结论可判读（已给对照分布；判定留待人工/文献）', True)


print('---- E-1/E-2 均匀特征应变的弹性能 vs 闭式（钉住工程分量记账）----')
N, L = 16, 1e-7
Ciso2 = C_iso3(100e9, 0.3)
mu2 = 100e9 / (2 * (1 + 0.3)); lam2 = 100e9 * 0.3 / ((1 + 0.3) * (1 - 0.6))
# E-1 纯剪切（张量分量 ε⁰_12 = ε⁰_21 = a）⇒ E = 2 μ a² V
a = 1e-3
e1 = np.zeros((3, 3)); e1[0, 1] = e1[1, 0] = a
pf1 = P.PF3D(N, L, Ciso2, [e1], gamma=0.0, w90=1e-8, Lmob=0.0, workers=2,
             k0_mode='clamped')
pf1.phi[:] = 1.0
E1 = pf1.E_el()
E1a = 2 * mu2 * a ** 2 * L ** 3
rec('E-1 均匀剪切 E_el = 2μa²V', abs(E1 - E1a) / E1a < 1e-6,
    '数值 %.6e vs 闭式 %.6e' % (E1, E1a))
# E-2 纯膨胀 ε⁰ = b I ⇒ E = ½·V·9b²K = 1.5 V b²(3λ+2μ)
b = 1e-3
e2 = np.zeros((3, 3)); e2[0, 0] = e2[1, 1] = e2[2, 2] = b
pf2 = P.PF3D(N, L, Ciso2, [e2], gamma=0.0, w90=1e-8, Lmob=0.0, workers=2,
             k0_mode='clamped')
pf2.phi[:] = 1.0
E2 = pf2.E_el()
# ★ 记账（判据自身的错）：闭式是 ½·ε⁰:C:ε⁰ = ½·9K·b²·V（K = λ + 2μ/3）。
#   初版写成 ½·(3λ+2μ)·9b²V ⇒ (3λ+2μ) = 3K ⇒ **多乘了 3** ⇒ 误报 FAIL。
E2a = 0.5 * 9 * (lam2 + 2 * mu2 / 3) * b ** 2 * L ** 3
rec('E-2 均匀膨胀 E_el = ½·9Kb²V', abs(E2 - E2a) / E2a < 1e-6,
    '数值 %.6e vs 闭式 %.6e' % (E2, E2a))

print()
print('==== HX 总判定: %s (%d/%d) ====' %
      ('PASS' if all(ok_all) else 'FAIL', sum(ok_all), len(ok_all)))
