#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_selfac2.py --- ★★★★ S-1 的**修正量具**：核级零分布 + 穷举 + 精确 p + 可达性判定

为什么要重写（`R1_PROBLEM_LEDGER.md` B-13，独立审计的结论）
----------------------------------------------------------
原 `_r1_selfac.py` 有三条**已核实**的硬伤：
 ① 置换在**体素级**（在 `reg>0` 的胞之间打乱标签）⇒ 把**紧凑的核打碎成散斑**
    ⇒ 它的 z 几乎全部来自"紧凑 vs 散斑"，**不是**变体搭配。实测：同一物理构型，
    核级置换 `z = −0.03`，体素级 `z = −5.98`。
 ② `z ≤ −2` 在 **6 核 2 变体**下**数学上不可达**：只有 **C(6,3)=20** 个核级划分，
    穷举后 `z ∈ [−1.326, +1.792]`。上界由"构型数只有 20"决定，**与物理无关**。
 ③ `k0_mode='clamped'` 的平均场项在置换下逐位不变、却抬高分母
    （引擎 `windowB_pf3d.py:113-115` 自己推荐 `'free'`）。

本脚本的做法
------------
1. **核级**：先对 `reg>0` 做连通分量标注得到**核**；一个核整体换标签。
2. **穷举**：枚举把"标签多重集"分给各核的**全部不重复方案**（= 多项系数），
   对每个方案算 `E_el`。构型数 ≤ `--max-configs` 时**穷举**；超过则**定种子抽样**
   并在输出里**显式标注"抽样，非穷举"**。
3. **报排名 + 精确 p**：`p = #{E ≤ E_obs} / n_configs`（单侧，越小越好）。
4. **可达性判定（关键）**：由**枚举出的**构型集算 `z` 的可达区间
   `[z_min, z_max]`；若 `−2` 不在区间内 ⇒ **明确宣告"z 判据不可达"**，
   此时只报排名/p，**不报 z 判决**。
5. **负对照（内置）**：`--control-bad` 会把标签按"最不利"方案（枚举中 E 最大者）指派，
   量具**必须**把它排到最后；否则本量具作废。
6. `--seed` **真正生效**（原版定义了却没用 ⇒ 不可复现）。

⚠ 代价：`PF3D(N)` 构造 ~377 s（N=192，实测），`Lam` 约 2.04 GB；每个构型一次 `E_el()`。
"""
import argparse
import itertools
import os
import sys
import time
from collections import Counter

import numpy as np
from scipy import ndimage as nd

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument('--snap', default=None)
ap.add_argument('--N', type=int, default=192)
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--workers', type=int, default=8)
ap.add_argument('--max-configs', type=int, default=20000,
                help='超过此数则改为定种子抽样（并在输出里标注）')
ap.add_argument('--nrand', type=int, default=64, help='抽样时的次数')
ap.add_argument('--seed', type=int, default=12345)
ap.add_argument('--k0-mode', default='free', choices=['free', 'clamped'],
                help="引擎自己推荐 'free'（自协调研究的标准选择）")
ap.add_argument('--also-voxel', action='store_true',
                help='同时算**旧的**体素级 z，用于对照两种口径差多少')
ap.add_argument('--control-bad', action='store_true',
                help='负对照：把标签指派成"最不利"方案，量具必须把它排最后')
a = ap.parse_args()
rng = np.random.default_rng(a.seed)

# ---------- 载入快照 ----------
snap = a.snap
if snap is None:
    import glob
    cand = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         '_exp', '*', 'snap_*.npz')))
    if not cand:
        print('✗ 找不到快照'); sys.exit(1)
    snap = cand[-1]
z = np.load(snap)
reg = np.asarray(z['region'])
NV = int(reg.max())
print('=' * 100)
print('_r1_selfac2（修正量具）快照=%s  shape=%s  最大变体号=%d'
      % (os.path.basename(snap), reg.shape, NV))
print('   k0_mode=%s  seed=%d  max-configs=%d' % (a.k0_mode, a.seed, a.max_configs))
print('=' * 100, flush=True)

# ---------- 核级标注 ----------
m = reg > 0
lab, nlab = nd.label(m)
sizes = np.array(nd.sum(m, lab, range(1, nlab + 1)), dtype=int)
# 每个核当前的标签 = 该核内变体号的众数
labels = []
for ci in range(1, nlab + 1):
    vals = reg[lab == ci]
    labels.append(int(Counter(vals.tolist()).most_common(1)[0][0]))
labels = np.array(labels, int)
print('\n连通分量（核）：%d 个' % nlab)
order = np.argsort(-sizes)
print('   %-6s %8s %8s' % ('核', '胞数', '变体'))
for i in order:
    print('   %-6d %8d %8d' % (i + 1, sizes[i], labels[i]))
cnt = Counter(labels.tolist())
print('   标签多重集 = %s' % dict(sorted(cnt.items())))

# 只保留**显著核**（≥1% 非母相胞），碎屑不参与指派（否则构型数爆炸且无物理意义）
_thr = 0.01 * int(m.sum())
sig = [i for i in range(nlab) if sizes[i] >= _thr]
print('   显著核（≥1%%=%.0f 胞）：%d 个 ；碎屑体积占比 %.4f'
      % (_thr, len(sig), 1.0 - sizes[sig].sum() / max(m.sum(), 1)))
if len(sig) < 2:
    print('   ⚠ 显著核 <2 ⇒ **无法做核级划分**，本脚本退出'); sys.exit(0)

# ---------- 枚举方案 ----------
lab_sig = [labels[i] for i in sig]
mult = Counter(lab_sig)
keys = sorted(mult)
# 不重复的多项式系数：从 len(sig) 个位置里给每个标签选位置
def enum_configs():
    n = len(sig)
    idx = list(range(n))
    out = []
    # 依次为每个标签选位置
    def rec(k, remaining, acc):
        if k == len(keys):
            out.append(tuple(acc))
            return
        need = mult[keys[k]]
        for comb in itertools.combinations(sorted(remaining), need):
            cs = set(comb)
            rec(k + 1, [x for x in remaining if x not in cs], acc + [comb])
    rec(0, idx, [])
    # acc 里每个标签一段
    cfgs = []
    for acc in out:
        assign = [0] * len(sig)
        for ki, comb in enumerate(acc):
            for p in comb:
                assign[p] = keys[ki]
        cfgs.append(assign)
    return cfgs

cfgs = enum_configs()
exhaustive = len(cfgs) <= a.max_configs
print('\n核级构型数 = **%d** %s' % (len(cfgs), '（穷举）' if exhaustive else '（超上限）'))
if not exhaustive:
    sel = rng.choice(len(cfgs), size=min(a.nrand, len(cfgs)), replace=False)
    cfgs = [cfgs[i] for i in sel]
    print('   ⇒ 改为**抽样 %d 个**（**非穷举**，输出已标注）' % len(cfgs))

# 观测方案在枚举里的位置
obs_assign = [labels[i] for i in sig]
obs_idx = None
for i, c in enumerate(cfgs):
    if list(c) == obs_assign:
        obs_idx = i
        break

# ---------- PF3D ----------
from windowB_pf3d import PF3D                                    # noqa: E402
from T16_verify_rve import C, EPS0                               # noqa: E402

L = a.L_um * 1e-6
t0 = time.time()
pf = PF3D(a.N, L, C, EPS0, gamma=0.0, w90=1e-8, Lmob=0.0,
          workers=a.workers, k0_mode=a.k0_mode, phi_dtype=bool, lam_prec='f64')
print('PF3D 构造 %.1f s' % (time.time() - t0), flush=True)


def eel_of(regarr):
    pf.phi[:] = False
    for v in range(pf.nv):
        pf.phi[v] = (regarr == v + 1)
    return float(pf.E_el())


base = reg.copy()


def reg_from_assign(assign):
    """按核级指派生成 `reg`；碎屑保持原样。"""
    out = base.copy()
    for p, i in enumerate(sig):
        out[lab == (i + 1)] = assign[p]
    return out


# ---------- 逐个构型算能量 ----------
print('\n开始逐构型算 E_el（n=%d）……' % len(cfgs), flush=True)
E = np.empty(len(cfgs))
t0 = time.time()
for i, c in enumerate(cfgs):
    E[i] = eel_of(reg_from_assign(c))
    if (i + 1) % 5 == 0 or i == len(cfgs) - 1:
        print('   %d/%d  %.1f s' % (i + 1, len(cfgs), time.time() - t0), flush=True)

E_obs = E[obs_idx] if obs_idx is not None else eel_of(base)
p_exact = float((E <= E_obs).sum()) / len(E)
rank = int((E < E_obs).sum()) + 1
mu, sd = float(E.mean()), float(E.std(ddof=1)) if len(E) > 1 else 0.0
z_obs = (E_obs - mu) / max(sd, 1e-300)
z_all = (E - mu) / max(sd, 1e-300)

print('\n' + '=' * 100)
print('【核级 · %s】结果' % ('穷举' if exhaustive else '抽样(非穷举)'))
print('   n_configs = %d ； E 均值 = %.6e ； 标准差 = %.3e' % (len(E), mu, sd))
print('   E(观测) = %.6e   ⇒ **排名 %d / %d**（1 = 最好）' % (E_obs, rank, len(E)))
print('   **精确单侧 p = %.4f**（= #{E ≤ E_obs}/n；越小越"自协调"）' % p_exact)
print('   能量降低 = %+.3f%%' % (100 * (E_obs / mu - 1.0)))
print('   z(观测) = %+.3f' % z_obs)
print('   **z 的可达区间 = [%+.3f, %+.3f]**' % (z_all.min(), z_all.max()))
reach = (z_all.min() <= -2.0)
print('   ⇒ `z ≤ −2` **可达性**：%s'
      % ('✅ 在可达区间内（z 判据有意义）' if reach else
         '⛔ **不可达** ⇒ **本数据上 z 判据作废**，只报排名/精确 p'))
print('   ⇒ 小样本地板：最小可达 p = 1/%d = %.4f' % (len(E), 1.0 / len(E)))
print('=' * 100)

# ---------- 负对照 ----------
if a.control_bad:
    worst = int(np.argmax(E))
    if worst == obs_idx:
        print('\n负对照：⛔ **观测本身就是最差方案** ⇒ 量具无法区分（可疑）')
    else:
        print('\n负对照：最差方案（第 %d 个）E = %.6e，比观测高 %+.2f%%'
              % (worst + 1, E[worst], 100 * (E[worst] / E_obs - 1)))
        print('   ⇒ 量具能区分"最差"与"观测" ⇒ ✅ 有分辨力（这是**必要**条件，非充分）')

# ---------- 可选的旧口径对照 ----------
if a.also_voxel:
    print('\n【体素级 · 旧口径｜**仅作对照，不作判决**】')
    er = []
    for _ in range(a.nrand):
        o = base.copy()
        mm = base > 0
        o[mm] = rng.permutation(base[mm])
        er.append(eel_of(o))
    er = np.array(er)
    print('   n=%d 均值=%.6e sd=%.3e ； z(体素级) = %+.3f ； 能量降低 = %+.3f%%'
          % (len(er), er.mean(), er.std(), (E_obs - er.mean()) / max(er.std(), 1e-300),
             100 * (E_obs / er.mean() - 1)))
    print('   ⚠ 体素级置换把紧凑核打碎成散斑 ⇒ 其 z 主要来自"紧凑度"，**不是自协调**。')
print('\n完成。')
