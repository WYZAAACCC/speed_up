#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_steal.py --- ★★★★★★ 核验：`attach` 是否**吃掉**已有场的体积？（先验后修）

## 机制假说（来自代码）
`attach` 的守卫是 `np.isin(_okr, (0, k))` ⇒ **允许新种子覆盖源场 k 的区域**;
`seed_plate` 写 `φ_j = max(φ_j, −sdf)` ⇒ 重叠区 `φ_j < φ_k` ⇒ `argmin` 转向 j ⇒
**源场 k 的 φ 被推向正 ⇒ k 的相体积流失 + 可能被切断。**

## 核验判据（**预先写死**）
对每个 `attach` 事件（step S）：
* **`gain`** = **新场**在 S 之后的 φ<0 体积（首次出现时的体积）;
* **`loss`** = **所有**老场**（在 S 之前已存在）在 S 前后**合计**的 φ<0 体积变化（负值 = 丢）;
* **`ratio` = `loss` / `gain`**
**⇒ 判据：**
| `ratio` | 结论 |
|---|---|
| **≈ 1（如 0.6–1.4）** | **✅ 机制确认**：新场拿到多少，老场就丢多少（**直接吃掉**）|
| **≪ 1（如 <0.3）** | **❌ 机制不成立**：老场没丢多少，新场是从**母相**长的 |
| **> 1.5** | 老场丢得**比新场拿的还多** ⇒ 还有别的流失渠道 |

## 数据源
* `nuc_dbg.json` 的 `T_events`（含 step 与 mode）;
* 快照（每 40 步）的 `band`（φ<0 ⇒ 物理体积）。
"""
import glob
import json
import os
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
steps = [int(P.split('snap_')[1].replace('.npz', '')) for P in snaps]


def vols(P):
    with np.load(P, allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
    v = {}
    neg = bv < 0
    for k in np.unique(bf[neg]):
        k = int(k)
        if k:
            v[k] = int((neg & (bf == k)).sum())
    return v


cache = {st: vols(P) for P, st in zip(snaps, steps)}
def _events():
    """从引擎日志解析形核事件（`nuc_dbg.json` 只在跑完时才写）。"""
    import re
    L = '_w2_t5_short_%s.log' % TAG
    RX = re.compile(r'@ step (\d+)：T=[\d.]+ K.*?场 (\d+)（累计 \d+/\d+；模式 \*\*([a-z]+)\*\*')
    ev = []
    if os.path.exists(L):
        for line in open(L, errors='ignore'):
            m = RX.search(line)
            if m:
                ev.append(dict(step=int(m.group(1)), field=int(m.group(2)),
                               mode=m.group(3)))
    return ev


ev = _events()
att = [e for e in ev if e.get('mode') == 'attach']
print('=' * 100)
print('★ %s：核验「`attach` 是否吃掉已有场的体积」' % TAG)
print('=' * 100)
print('  快照步点：%s … %s（共 %d）' % (steps[:3], steps[-3:], len(steps)))
print('  attach 事件 %d 个' % len(att))
print()
print('  %-7s %-8s %-10s %-12s %-12s %-8s %s'
      % ('事件step', '前快照', '后快照', '新场gain', '老场合计Δ', '**ratio**', '判读'))
rows = []
for e in att:
    S = int(e['step'])
    pre = [s for s in steps if s < S]
    post = [s for s in steps if s > S]
    if not pre or not post:
        continue
    a, b = pre[-1], post[0]
    va, vb = cache[a], cache[b]
    # 新场：在 a 时不存在、在 b 时存在的场（取体积增量最大的那个）
    newk = [k for k in vb if k not in va]
    if not newk:
        continue
    gn = sum(vb[k] for k in newk)
    # 老场：a 与 b 都存在的场，合计体积变化
    old = [k for k in va if k in vb]
    dl = sum(vb[k] - va[k] for k in old)
    ratio = dl / gn if gn else 0.0
    if 0.6 <= ratio <= 1.4:
        vd = '**✅ 吃掉**'
    elif ratio < 0.3:
        vd = '❌ 从母相长'
    else:
        vd = '⚠ 混合'
    rows.append((S, a, b, gn, dl, ratio))
    print('  %-7d %-8d %-10d %-12d %-12d **%-8.2f** %s'
          % (S, a, b, gn, dl, ratio, vd))
print()
if rows:
    r = np.array([x[5] for x in rows])
    print('  ── 汇总（%d 个可判事件）──' % len(rows))
    print('     ratio 中位 = **%.2f** ｜ 范围 [%.2f, %.2f]' % (np.median(r), r.min(), r.max()))
    print('     ratio ∈ [0.6,1.4] 的个数 = **%d / %d**' % (int(((r >= .6) & (r <= 1.4)).sum()), len(r)))
    print('     ratio < 0.3 的个数     = **%d**' % int((r < .3).sum()))
    print()
    print('  ── 判据 ──')
    if np.median(r) >= 0.6:
        print('  ⇒ **✅ 机制确认**：`attach` 事件中，**老场丢掉的体积与新场拿到的体积相当**')
        print('     ⇒ **新种子确实吃掉了已有场** ⇒ 这就是"一场多块 + 体积流失"的机制。')
    else:
        print('  ⇒ **❌ 机制不成立**：老场没丢多少 ⇒ 新场主要从**母相**长大。')
        print('     ⇒ 需另找"体积流失"的渠道（例如曲率驱动的回退）。')
else:
    print('  ⚠ 没有可判事件（快照步点与事件步点不匹配）')
