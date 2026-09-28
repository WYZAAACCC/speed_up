#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_probe_d6_variants.py --- **从零构造理想 Burgers 变体集**，算出 66 对的约化错取向角真值

为什么要做（解开 `_probe_iface_types.py` 的 I-1c「已知限制」）
----------------------------------------------------------------
`_probe_iface_types.py` 的 I-1 自校验只有 **4/5** 类型命中：`Type 3 = 60.83°` 一对都没有，
当时记为"量具分辨不出（丢掉了 `F_k` 的面内取向）"。**这个归因必须先证伪再用**——
如果 66 对的真值里 **本来就只有 4 个角度**，那 I-1c 根本不是量具的问题，
而是**引擎的 12 个变体轴本身不构成完整的 Burgers 变体集**（少了一整类）。
本脚本用**完全不依赖本仓库**的构造法给出真值：

    β 为 bcc；Burgers OR： (0001)α ∥ {110}β ， <11−20>α ∥ <111>β
    ⇒ 6 个 {110} 面 × 每个面内 2 个 <111> = **12 个变体**
    ⇒ α′ 三元组 Q_k = [ a1 , m = c×a1 , c ]，其中
         c  = {110} 面法向（单位化），  a1 = 该面内的 <111> 方向（单位化，天然 ⊥ c）
    ⇒ 约化错取向角 θ(k,l) = min_{G∈D6} arccos( ½(tr(Q_l^T Q_k G) − 1) )

判定（**先写死**）
------------------
  V-1 12 个变体互不相同（无重复三元组）⇒ 若重复，构造本身错；
  V-2 66 对的 θ 值集合 = {0, 10.53, 60.00, 60.83, 63.26, 90}（容差 0.05°）；
  V-3 与 `windowB_ti64_variants.variants()` 给出的 `(n, d)` 逐变体比对角度差（应 ≈0）。
  V-4 报告**每一类型配对数**（这是群论给死的，与"界面面积分数"不是一回事）。

⚠ 记账：本脚本**不读引擎**（除 V-3 读变体模块），只做晶体学算术 ⇒ 可作为 I-1 的**独立真值源**。
用法：python3 _probe_d6_variants.py
"""
import os
import sys
import itertools

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402

TYPES = [(6, 10.53), (2, 60.00), (3, 60.83), (4, 63.26), (5, 90.00)]
TOL = 0.05


def d6_group():
    """α′ 的 D6（12 个真旋转），在正交三元组 (a1, m, c) 里。"""
    def Rz(t):
        c_, s_ = np.cos(t), np.sin(t)
        return np.array([[c_, -s_, 0], [s_, c_, 0], [0, 0, 1.0]])

    def Rax(t):
        u = np.array([np.cos(t), np.sin(t), 0.0])
        return 2 * np.outer(u, u) - np.eye(3)
    return ([Rz(np.radians(60 * n)) for n in range(6)]
            + [Rax(np.radians(t)) for t in (0, 60, 120)]
            + [Rax(np.radians(t)) for t in (30, 90, 150)])


def burgers_variants():
    """从零构造 12 个 Burgers 变体的三元组（β 立方坐标系）。"""
    # 6 个 {110} 面法向（**必须保留符号**：取绝对值的无序三元组会把 6 个面塌成 1 个 ——
    #   本脚本第一版就是这么错的，构造出 4 个变体）
    planes = []
    for i, j, k in itertools.product((0, 1, -1), repeat=3):
        if sum(1 for v in (i, j, k) if v == 0) != 1:
            continue
        v = [i, j, k]
        first = next(t for t in range(3) if v[t] != 0)
        if v[first] < 0:
            v = [-t for t in v]
        if tuple(v) not in planes:
            planes.append(tuple(v))
    out = []
    for pl in planes:                      # pl 是 {110} 的无序三元组，如 (0,1,1)
        n = np.array(pl, float)
        n = n / np.linalg.norm(n)
        for sg in itertools.product((1, -1), repeat=3):
            d = np.array(sg, float)
            if abs(d @ n) > 1e-9:          # <111> 必须落在这个面内
                continue
            if abs(np.linalg.norm(d) - np.sqrt(3)) > 1e-9:
                continue
            # ★ 每个面内只有 **2** 个 <111>（方向等价，±d 是同一支）——
            #   本脚本第二版没去重，得到 24 个变体（= 12 个变体 × 2，因为 D6 含
            #   翻转 c 的 2 次轴）=> 66 对的直方图被放大 4 倍。
            fd = next(t for t in range(3) if d[t] != 0)
            if d[fd] < 0:
                d = -d
            a1 = d / np.linalg.norm(d)
            m = np.cross(n, a1)
            Q_ = np.column_stack([a1, m, n])
            if any(np.allclose(Q_, q, atol=1e-9) for q in out):
                continue
            out.append(Q_)
    return out


def red_angle(Qk, Ql, G):
    dR = Ql.T @ Qk
    best = 1e9
    for g in G:
        tr = float(np.trace(dR @ g))
        th = np.degrees(np.arccos(np.clip(0.5 * (tr - 1.0), -1.0, 1.0)))
        best = min(best, th)
    return best


def classify(th, tol=TOL):
    for t, ang in TYPES:
        if abs(th - ang) <= tol:
            return t
    if th <= tol:
        return 0                               # 自身
    return None


G = d6_group()
Q = burgers_variants()
print('=' * 96)
print('_probe_d6_variants —— 理想 Burgers 12 变体集的 66 对约化错取向角（独立真值源）')
print('=' * 96)
print('\n【V-1】构造出的变体数 = %d（应为 12）' % len(Q))
uniq = {tuple(np.round(q.ravel(), 6)) for q in Q}
print('   互不相同的三元组数 = %d ⇒ %s' % (len(uniq), 'PASS' if len(uniq) == len(Q) == 12 else 'FAIL'))
if len(uniq) != len(Q):
    for a, b in itertools.combinations(range(len(Q)), 2):
        if np.allclose(Q[a], Q[b]):
            print('   !! 重复：%d 与 %d' % (a + 1, b + 1))

hist = {t: 0 for t, _ in TYPES}
hist[0] = 0
allth = []
uncl = []
for k, l in itertools.combinations(range(len(Q)), 2):
    th = red_angle(Q[k], Q[l], G)
    allth.append(th)
    t = classify(th)
    if t is None:
        uncl.append((k + 1, l + 1, th))
    else:
        hist[t] += 1
print('\n【V-2】66 对的约化错取向角分布（容差 ±%.2f°）' % TOL)
for t, ang in TYPES:
    print('   Type %d (%6.2f°) : **%2d** 对' % (t, ang, hist[t]))
print('   未归类 = **%d** 对 %s' % (len(uncl), ('（%s）' % uncl[:6]) if uncl else ''))
got = sorted({round(v, 2) for v in allth})
print('   实测角度值集合 = %s' % got)
want = sorted(a for _, a in TYPES)
hit = [a for a in want if any(abs(a - v) <= 0.5 for v in got)]
print('   ⇒ 命中的 Table 3 类型角 = %d/5 %s ；%s'
      % (len(hit), hit, 'PASS' if len(uncl) == 0 and len(hit) == 5 else 'FAIL'))

print('\n【V-3】与 `windowB_ti64_variants.variants()` 的 (n, d) 比对')
try:
    from windowB_ti64_variants import variants as _V
    _s, _F, _meta = _V()
    print('   模块给出 %d 个变体' % len(_meta))
    # 对每个模块变体，找理想集里 c 与 a1 都最接近的那个
    dev = []
    for i, mt in enumerate(_meta):
        c_ = np.asarray(mt['n'], float)
        c_ = c_ / np.linalg.norm(c_)
        d_ = np.asarray(mt['d'], float)
        d_ = d_ / np.linalg.norm(d_)
        best, bj = 1e9, -1
        for j, q in enumerate(Q):
            ang = (np.degrees(np.arccos(np.clip(abs(q[:, 2] @ c_), -1, 1)))
                   + np.degrees(np.arccos(np.clip(abs(q[:, 0] @ d_), -1, 1))))
            if ang < best:
                best, bj = ang, j
        dev.append((i + 1, bj + 1, best))
    worst = max(d[2] for d in dev)
    print('   逐变体 (c 与 a1 的角度偏差之和) 最大 = %.3f° ⇒ %s'
          % (worst, 'PASS（模块与理想集一致）' if worst < 1.0 else 'FAIL（模块的轴与理想 Burgers 不符）'))
    for i, j, b in dev:
        if b > 1.0:
            print('      ⚠ 模块变体 %2d ↔ 理想 %2d ：偏差 %.3f°' % (i, j, b))
    # 用模块的 (n,d) 重算 66 对 ⇒ 与理想集的直方图对比
    Qm = []
    for mt in _meta:
        c_ = np.asarray(mt['n'], float)
        c_ = c_ / np.linalg.norm(c_)
        a_ = np.asarray(mt['d'], float)
        a_ = a_ - (a_ @ c_) * c_
        a_ = a_ / np.linalg.norm(a_)
        Qm.append(np.column_stack([a_, np.cross(c_, a_), c_]))
    hm = {t: 0 for t, _ in TYPES}
    hm[0] = 0
    for k, l in itertools.combinations(range(len(Qm)), 2):
        t = classify(red_angle(Qm[k], Qm[l], G))
        hm[t if t is not None else -1] = hm.get(t if t is not None else -1, 0) + 1
    print('   用**模块**的 (n,d) 重算直方图：%s'
          % '  '.join('T%d=%d' % (t, hm[t]) for t, _ in TYPES))
    print('   与理想集一致？%s' % ('**一致** ⇒ I-1c 不是模块的问题'
                                  if all(hm[t] == hist[t] for t, _ in TYPES) else
                                  '**不一致** ⇒ 模块的变体轴有问题（见上 ⚠）'))
except Exception as e:
    print('   （跳过：%s）' % e)
print('\n' + '=' * 96)
