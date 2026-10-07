#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_milectl.py --- ★★★★★ 里程碑监视器的**正/负对照**（证明它真会报，不是哑的）

## 为什么（第 19/24 条：探针必须先做正对照，且正对照必须能失败）
**"监视器没报警"有两种可能**：① 真的没变化；② **监视器坏了**。
**⇒ 必须构造一个**已知会触发**的输入，确认它**真报警**。**

## 做法（**不碰真数据**）
把真 `series.csv` 读进来，**在内存里改列**，写到临时文件，用**同一套判据函数**跑一遍：
| 用例 | 注入的改动 | 期望 |
|---|---|---|
| **C1 正对照 M2** | 把块表行的 `nf2` 由 `0` 改成 `5` | **必须报 M2（块间相遇）** |
| **C2 正对照 M1** | 把 `nblk_sig` 由 1 改成 3 | **必须报 M1（块数增加）** |
| **C3 正对照 M3** | 把 `n_var_sig` 由 1 改成 4 | **必须报 M3（多变体）** |
| **C4 负对照** | **不改任何列** | **必须**不报**任何 M1/M2/M3** |
**⇒ 四个用例全过 ⇒ 监视器可信；任一不过 ⇒ 监视器必须先修。**
"""
import csv
import io
import sys


def num(r, k):
    v = (r.get(k) or '').strip()
    try:
        return float(v)
    except Exception:
        return None


def scan(rows):
    """与 `_t5_milewatch.py` **同一套判据**（复制自那里，逐字）"""
    events = []
    prev = {}
    for r in rows:
        last = r
        st = last.get('step')
        blk = None
        for x in rows:
            if (x.get('nblk_sig') or '').strip():
                blk = x
        nb = num(blk, 'nblk_sig') if blk else None
        nv = num(blk, 'n_var_sig') if blk else None
        nf2 = num(blk, 'nf2') if blk else None
        if prev.get('nblk') is not None and nb is not None and nb > prev['nblk']:
            events.append('M1 nblk_sig %g→%g' % (prev['nblk'], nb))
        if prev.get('nv') is not None and nv is not None and nv > prev['nv']:
            events.append('M3 n_var_sig %g→%g' % (prev['nv'], nv))
        if prev.get('nf2') == 0 and nf2 is not None and nf2 > 0:
            events.append('M2 nf2 0→%g' % nf2)
        prev['nblk'], prev['nv'], prev['nf2'] = nb, nv, nf2
    return events


P = '_exp/_bk_t5/dry_t5N276/series.csv'
rows = list(csv.DictReader(open(P, newline='')))
print('  真数据：%d 行，块表行 = %s'
      % (len(rows), [r['step'] for r in rows if (r.get('nblk_sig') or '').strip()]))

# 为了让对照有分辨力，构造"两阶段"：前半保持原样，后半注入改动
# （监视器的判据是"比上一点大"，所以必须有两个块表点）
base = [dict(r) for r in rows]
blkidx = [i for i, r in enumerate(rows) if (r.get('nblk_sig') or '').strip()]
print('  块表行索引 = %s' % blkidx)
if len(blkidx) < 1:
    print('  ⚠ 块表行不足 ⇒ 无法做对照（需至少 2 个块表点才能看"增加"）')

cases = [
    ('C1 正对照 M2（nf2 0→5）', 'nf2', '5', ['M2']),
    ('C2 正对照 M1（nblk_sig 1→3）', 'nblk_sig', '3', ['M1']),
    ('C3 正对照 M3（n_var_sig 1→4）', 'n_var_sig', '4', ['M3']),
    ('C4 负对照（不改）', None, None, []),
]
print()
ok_all = True
for name, col, val, want in cases:
    rs = [dict(r) for r in base]
    if col:
        # 在**最后一个块表行**上注入改动（模拟"后来变了"）
        i = blkidx[-1]
        rs[i][col] = val
    ev = scan(rs)
    hit = [w for w in want if any(e.startswith(w) for e in ev)]
    bad = [e for e in ev if not any(e.startswith(w) for w in want)] if not want else []
    ok = (len(hit) == len(want)) and (not bad)
    ok_all &= ok
    print('  %-30s 触发的事件 = %-28s ⇒ %s'
          % (name, (ev or ['（无）'])[0] if len(ev) <= 1 else '%d 个' % len(ev),
             '✅ 符合期望' if ok else '❌ **不符**'))
    if ev:
        for e in ev[:3]:
            print('        · %s' % e)
print()
print('  ⇒ **%s**' % ('四个对照全过 ⇒ 监视器可信（"没报警"= 真没变化）'
                     if ok_all else '有未过项 ⇒ **监视器须先修**'))
sys.exit(0 if ok_all else 1)
