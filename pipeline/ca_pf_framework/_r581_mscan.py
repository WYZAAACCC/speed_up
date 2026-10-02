#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_mscan.py --- ★★★★ **`m` 的标定曲线**：`nslab_n` / `Vt` / 拒绝率 随 `m` 怎么变？

## 为什么要这个
R33 给出**短程**判决（`m=4 ⇒ max 4`；`m=12 ⇒ max 5 = target`），R48/R51 证明
**变体分布是构造均匀的** ⇒ **`m` 是"同变体板条数"的唯一约束**。R53 算了时间与内存账。
**⇒ 现在缺的是**跨 `m` 的实测标定曲线**：把 `m = 4 / 12 / 20`（以及以后的 38）三（四）个点连起来。**

## 数据来源（**全部读运行自己的产物，不猜**）
* `nuc_dbg.json` 的 **`nuc_cfg.vgroup`** ⇒ `nv`、每变体场数 `m`
* `series.csv` 的 **`nslab_n` / `nf3_col` / `Vt` / `nf2`** ⇒ 末值与最大值
* `_w2_r581_p2_<tag>.log` 的 **`被引擎拒` / `athermal 形核`** ⇒ 拒绝率（**注意 P42 的 grep 坑**：
  只认 `**athermal 形核** @ step`，**排除横幅 `athermal 形核律`**）

## 判据（**预先写死**）
* 若 `nslab_n` 的**最大同变体数**随 `m` 单调上升到 ≈`m` ⇒ **R33 的"上限 = `m`"成立**；
* 若 `m=12`/`m=20` 的 `nslab_n` **仍停在 ~4–5** ⇒ **上限不是 `m`，另有原因**（要查）。
"""
import json
import os
import re
import sys
from collections import Counter

import numpy as np

ROOT = '_exp/_bk_p2'


def read_cfg(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'nuc_dbg.json')
    if not os.path.exists(p):
        return None
    j = json.load(open(p, encoding='utf-8'))
    cfg = j.get('nuc_cfg', {})
    vg = cfg.get('vgroup')
    if not isinstance(vg, dict):
        return None
    vg = {int(a): int(b) for a, b in vg.items()}
    cnt = Counter(vg.values())
    per = sorted(set(cnt.values()))
    return dict(nv=len(vg), m_per_variant=(per[0] if len(per) == 1 else per),
                uniform=(len(per) == 1), vmap=vg)


def read_series(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    dd = np.genfromtxt(p, delimiter=',', names=True)
    out = {}
    for k in ('step', 'nslab_n', 'nf3_col', 'Vt', 'nf2'):
        if k in dd.dtype.names:
            out[k] = np.atleast_1d(dd[k]).astype(float)
    return out


def per_variant_laths(tag):
    """★★★ **`m` 假说的**正确**观测量**：从**最后一个快照**数「每个变体各出现几根」。

    ⚠ **为什么不能用 `nslab_n`**（本工具第一版就是这个错 —— 留痕）：
    `nslab_n` 是 **1-D 柱剖面量**、数的是**该柱里所有板条**（**跨变体**）；
    而 `m` 限的是**同一变体**最多几根 ⇒ **两者不是一个量**。
    **实测对照**：`p2_b5`（`m=4`）的 `nslab_n` **max = 5**，看着"超过 `m`" ——
    但 R33 实测它的场是 **变体 1 占 4 根 + 变体 5 占 1 根 = 5** ⇒ **完全符合 `m=4`** ✓
    ⇒ **必须按变体分组数。**
    """
    d = os.path.join(ROOT, 'dry_' + tag)
    if not os.path.isdir(d):
        return None
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    if not snaps:
        return None
    z = np.load(os.path.join(d, snaps[-1]))
    if 'region' not in z or 'vmap_keys' not in z:
        return None
    reg = z['region']
    vk = [int(x) for x in np.asarray(z['vmap_keys']).ravel()]
    vv = [int(x) for x in np.asarray(z['vmap_vals']).ravel()]
    vm = dict(zip(vk, vv))
    byvar = Counter()
    for f in np.unique(reg):
        f = int(f)
        if f > 0:
            byvar[vm.get(f, -1)] += 1
    return dict(step=int(z['step']), byvar=dict(sorted(byvar.items())),
                max_per_variant=(max(byvar.values()) if byvar else 0),
                n_fields=sum(byvar.values()))


def read_rej(tag):
    """拒绝率（★ 只认**事件行** `**athermal 形核** @ step`，排除横幅 `athermal 形核律` —— R42 的坑）。"""
    f = None
    for cand in ('_w2_r581_p2_%s.log' % tag,):
        if os.path.exists(cand):
            f = cand
    if f is None:
        c = [x for x in os.listdir('.') if x.endswith('.log') and tag in x]
        f = c[0] if c else None
    if f is None:
        return None
    txt = open(f, encoding='utf-8', errors='replace').read()
    ok = len(re.findall(r'\*\*athermal 形核\*\* @ step', txt))   # ★ 只认事件行
    rej = len(re.findall(r'被引擎拒', txt))
    return dict(ok=ok, rej=rej, tot=ok + rej,
                rate=(rej / (ok + rej) if (ok + rej) else float('nan')))


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3', 'p2_b5ov', 'p2_b5ps', 'p2_m12', 'p2_m12b', 'p2_m20']
    print('=' * 104)
    print('`m` 的标定曲线：`nslab_n` / `Vt` / 拒绝率 随 `m` 怎么变？')
    print('=' * 104)
    rows = []
    for t in tags:
        cfg = read_cfg(t); se = read_series(t); rj = read_rej(t)
        if cfg is None and se is None:
            continue
        rows.append((t, cfg, se, rj))
    print(' %-10s %-5s %-7s %-8s %-9s %-9s %-9s %-8s %s'
          % ('tag', 'nv', 'm/变体', '均匀?', '末step', 'nslab max', 'nf3col max', 'Vt末(µm³)', '拒绝率'))
    print(' ' + '-' * 100)
    for t, cfg, se, rj in rows:
        nv = cfg['nv'] if cfg else '?'
        m = cfg['m_per_variant'] if cfg else '?'
        uni = ('✅' if cfg['uniform'] else '❌') if cfg else '?'
        st = int(se['step'].max()) if se and 'step' in se else '?'
        ns = int(se['nslab_n'].max()) if se and 'nslab_n' in se else '?'
        n3 = int(se['nf3_col'].max()) if se and 'nf3_col' in se else '?'
        vt = (se['Vt'][-1] * 1e18) if se and 'Vt' in se else float('nan')   # P30：SI → µm³
        rr = ('%.1f%%' % (100 * rj['rate'])) if rj and rj['tot'] else '—'
        print(' %-10s %-5s %-7s %-8s %-9s %-9s %-9s %-8.4g %s'
              % (t, nv, m, uni, st, ns, n3, vt, rr))
    print()
    print('── ★★★ **按变体分组数板条**（`m` 假说的**正确**观测量）──')
    print(' %-10s %-8s %-7s %-10s %s'
          % ('tag', '快照step', 'm', '同变体 max', '每变体的根数'))
    print(' ' + '-' * 92)
    for t, cfg, se, rj in rows:
        pv = per_variant_laths(t)
        if pv is None:
            print(' %-10s %-8s %-7s %-10s %s'
                  % (t, '（无快照/vmap）', cfg['m_per_variant'] if cfg else '?', '—', '—'))
            continue
        m = cfg['m_per_variant'] if cfg else '?'
        ok = '✅ ≤ m' if (isinstance(m, int) and pv['max_per_variant'] <= m) else \
             ('❌ > m' if isinstance(m, int) else '?')
        print(' %-10s %-8d %-7s %-10s %s   %s'
              % (t, pv['step'], m, '**%d**' % pv['max_per_variant'],
                 pv['byvar'], ok))
    print()
    print('=' * 104)
    print('★ 判读（**预先写死**）')
    print('  · 「m/变体」应当是 `nv/12`；「均匀?」应当是 ✅（R48/R51）')
    print('  · ★ **正确判据**：**「同变体 max」是否 ≤ `m`，且是否随 `m` 上升** ——')
    print('    那就是 R33 的"上限 = m"假说；**不要拿 `nslab_n` 直接比 `m`**（口径不同，见上）')
    print('  · 若 `m=12`/`m=20` 的「同变体 max」**仍停在 4** ⇒ **上限不是 `m`**，要另查')
    print('  ⚠ `nslab_n` 是 **1-D 柱剖面量**，已知**会多读**（P1-29）⇒ 只作旁证')
    print('=' * 104)


if __name__ == '__main__':
    main()
