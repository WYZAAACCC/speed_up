#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_variant_groups.py --- ★ 相变组织的晶体学分组：**packet / colony / block**

为什么必须先把这件事算清楚
--------------------------
用户实验 4–7 要问的是"多个晶核能不能组成**块**"，以及"块能不能**自协调**"。
而"块"不是一个形态词，是一个**晶体学**词：

  * **packet（群）**：**同一惯习面族**（Burgers 下 3 个 `{110}_β` 面之一）内的所有变体；
  * **colony（丛）**：同一惯习面**且**同一 `⟨111⟩_β` 长轴方向 —— 更细一级；
  * **block（块）**：**同一变体**、彼此平行的一组长条（真正的"块"）。

⇒ 不先把 12 个变体按这三层分好组，实验 4–7 的"组成了块没有"就**没有判据**。

做法（全部由引擎自己的表算出，**不另起一套约定**）
--------------------------------------------------
  * `n*_k  = NPF[k]`   —— 惯习面法向（`argmin_normal` 给的微弹性最省能法向）
  * `a_k   = atab[k]`  —— 板条**长轴**（`_rank1_axes` 的 `a`）
  * `w_k   = wtab[k]`  —— 板条**宽度**方向
分组规则（写死）：
  * **packet**：`|n*_i · n*_j| ≥ cos(5°)`（同族，允许 ± 号）
  * **colony**：在同一 packet 内，且 `|a_i · a_j| ≥ cos(5°)`
  * **block**：同一 colony 内，且 `|w_i · w_j| ≥ cos(5°)`  —— 在 Burgers 下等价于"同一个变体"

用法：python3 _r1_variant_groups.py [--N 32]
"""
import os
import sys
import argparse
import itertools

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB            # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=32)
ap.add_argument('--tol-deg', type=float, default=5.0)
a = ap.parse_args()

L = a.N * 2.5e-8
g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=1, reinit_every=0)

CT = np.cos(np.radians(a.tol_deg))


def uni(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) + 1e-300)


n = {k: uni(NPF[k]) for k in range(1, NV + 1)}
aa = {k: uni(np.asarray(g.atab[k], float)) for k in range(1, NV + 1)}
ww = {k: uni(np.asarray(g.wtab[k], float)) for k in range(1, NV + 1)}

print('=' * 100)
print('_r1_variant_groups  NV=%d  容差 %.1f°  （|cos| ≥ %.4f 视为同向）'
      % (NV, a.tol_deg, CT))
print('=' * 100)
print('\n各变体的三轴：')
print('  %-4s %-26s %-26s %-26s' % ('k', 'n*（惯习面法向）', 'a（长轴）', 'w（宽向）'))
for k in range(1, NV + 1):
    print('  %-4d [%+.4f %+.4f %+.4f]  [%+.4f %+.4f %+.4f]  [%+.4f %+.4f %+.4f]'
          % ((k,) + tuple(n[k]) + tuple(aa[k]) + tuple(ww[k])))

# ---------------- packet ----------------
print('\n' + '-' * 100)
seen = set()
packets = []
for k in range(1, NV + 1):
    if k in seen:
        continue
    grp = [j for j in range(1, NV + 1) if abs(n[j] @ n[k]) >= CT]
    seen |= set(grp)
    packets.append(sorted(grp))
print('★ **packet（同一惯习面族）**  共 %d 组：' % len(packets))
for i, grp in enumerate(packets, 1):
    print('   packet-%d：变体 %s   （n* = [%+.4f %+.4f %+.4f]）'
          % (i, grp, *n[grp[0]]))
# 族间夹角（应当 ≈ 60°，Burgers 的 {110}_β 三面）
if len(packets) > 1:
    print('   族间夹角：', end='')
    for i, j in itertools.combinations(range(len(packets)), 2):
        ang = np.degrees(np.arccos(min(1.0, abs(n[packets[i][0]] @ n[packets[j][0]]))))
        print('p%d–p%d = %.2f°  ' % (i + 1, j + 1, ang), end='')
    print()

# ---------------- colony ----------------
print('\n' + '-' * 100)
colonies = []
for gi, grp in enumerate(packets, 1):
    seen2 = set()
    for k in grp:
        if k in seen2:
            continue
        sub = [j for j in grp if abs(aa[j] @ aa[k]) >= CT]
        seen2 |= set(sub)
        colonies.append((gi, sorted(sub)))
print('★ **colony（同族 + 同长轴）**  共 %d 组：' % len(colonies))
for i, (gi, sub) in enumerate(colonies, 1):
    print('   colony-%d（属 packet-%d）：变体 %s' % (i, gi, sub))

# ---------------- block ----------------
print('\n' + '-' * 100)
blocks = []
for gi, sub in colonies:
    seen3 = set()
    for k in sub:
        if k in seen3:
            continue
        sb = [j for j in sub if abs(ww[j] @ ww[k]) >= CT]
        seen3 |= set(sb)
        blocks.append((gi, sorted(sb)))
print('★ **block（同变体 / 完全平行）**  共 %d 组：' % len(blocks))
for i, (gi, sb) in enumerate(blocks, 1):
    print('   block-%d：变体 %s' % (i, sb))

print('\n' + '=' * 100)
print('★★ **用 Burgers 对应关系重新分组**（不用 `NPF`）')
print('=' * 100)
print("""为什么必须换：`NPF` 来自 `argmin_normal` 的**微弹性**最优法向（PTMT 惯习面），
  它是**无理数面**、12 个变体**各不相同**（上面实测：没有两个在 5° 内同族，
  但有 3 对只差 **5.28°** —— 那不是晶体学角，是微弹性的近简并）。
  ⇒ **`NPF` 给不出 packet/colony/block**。
  Burgers OR 里 `(0001)_α ∥ {110}_β` ⇒ **hcp 的 c 轴方向本身就给出 {110}_β 法向族** ⇒
  **packet = 按 c 轴（±）分组**。""")
try:
    from windowB_ti64_variants import variants as _vars     # noqa: E402
    _e0, _Fs, _meta = _vars()
    cax = {k: uni(np.asarray(_meta[k - 1]['n'], float)) for k in range(1, NV + 1)}
    print('\n各变体的 hcp c 轴：')
    for k in range(1, NV + 1):
        print('   V%-2d  c = [%+.4f %+.4f %+.4f]' % ((k,) + tuple(cax[k])))
    seen4 = set()
    pk = []
    for k in range(1, NV + 1):
        if k in seen4:
            continue
        grp = [j for j in range(1, NV + 1) if abs(cax[j] @ cax[k]) >= CT]
        seen4 |= set(grp)
        pk.append(sorted(grp))
    print('\n★ **packet（同 {110}_β 族 = 同 c 轴）**  共 %d 组：' % len(pk))
    for i, grp in enumerate(pk, 1):
        print('   packet-%d：变体 %s    c = [%+.4f %+.4f %+.4f]'
              % (i, grp, *cax[grp[0]]))
    if len(pk) > 1:
        print('   族间夹角（应接近 60° 或 90°，即 {110}_β 之间的夹角）：')
        for i, j in itertools.combinations(range(len(pk)), 2):
            ang = np.degrees(np.arccos(min(1.0, abs(cax[pk[i][0]] @ cax[pk[j][0]]))))
            print('      packet-%d – packet-%d = %.2f°' % (i + 1, j + 1, ang), end='')
        print()
    print('\n★ 与 `NPF` 分组的**对照**（证伪"`NPF` 能当 packet 用"）：')
    print('   `NPF` 分组 = %d 组（每组 1 个变体）' % len(packets))
    print('   c 轴分组  = %d 组：%s' % (len(pk), [len(g) for g in pk]))
except Exception as _e:
    print('   （`windowB_ti64_variants` 读取失败：%s）' % _e)

print('  实验 4「多个板条状晶核 → 组成块」：所有核用**同一个变体 k**（= 同一个 block）')
print('    · 判据 B-1：各核长轴与 a_k 的夹角 ≤ 20°（平行）')
print('    · 判据 B-2：最终 `region()` 里变体 k **连通成一个分量**（`ncomp==1`）')
print('    · 判据 B-3：板条**间距**与**宽度**同量级（文献 lath width 0.9 µm）')
print('  实验 7「自协调」：用**同一 packet 内不同 colony**（如 %s）'
      % (colonies[1][1] if len(colonies) > 1 else '—'))
print('    · 判据 S-1：分族测**弹性能** `E_el`，与"随机指派同体积分数"的对照比，'
      '观测构型必须**更低**')
print('    · 判据 S-2：各组体积分数向**自协调配比**（Burgers 的惯习面族间 ≈ 等分）靠拢')
print('=' * 100)
