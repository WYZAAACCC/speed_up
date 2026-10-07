#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_milectl2.py --- ★★★★★ 里程碑监视器的正/负对照（**修正版**：按"轮"模拟，与监视器同构）

## 我上一版对照的 bug（**留痕**）
第一版 `_t5_milectl.py` 写成 `for r in rows: … 内层再扫全表取最后块表行` ⇒
**块表值恒定不变** ⇒ "变大"的比较**永不触发** ⇒ 三个正对照全失败。
**而真正的 `_t5_milewatch.py` 是**按轮**（每轮重读文件，与**上一轮**的值比）—— **结构不同**（那个是对的）。**
**⇒ 是**对照脚本**错了，不是监视器错了。**
**⇒ 纪律（第 33 条）：对照必须与**被测对象同构**** —— 否则测的是另一段逻辑。

## 本版做法
把真数据切成**若干个"轮"的快照**，逐轮喂给**与监视器逐字相同**的判据函数：
* **C1** 第 2 轮把 `nf2` 改成 `5` ⇒ **必须报 M2**
* **C2** 第 2 轮把 `nblk_sig` 改成 `3` ⇒ **必须报 M1**
* **C3** 第 2 轮把 `n_var_sig` 改成 `4` ⇒ **必须报 M3**
* **C4 负对照** 两轮都不改 ⇒ **必须不报 M1/M2/M3**
"""
import csv
import sys


def num(r, k):
    v = (r.get(k) or '').strip()
    try:
        return float(v)
    except Exception:
        return None


def judge_round(rows, prev):
    """**与 `_t5_milewatch.py` 逐字同一套判据**（每轮：取最新块表行，与 prev 比）"""
    ev = []
    blk = None
    for r in rows:
        if (r.get('nblk_sig') or '').strip():
            blk = r
    if blk is None:
        return ev, prev
    nb, nv, nf2 = num(blk, 'nblk_sig'), num(blk, 'n_var_sig'), num(blk, 'nf2')
    if prev.get('nblk') is not None and nb is not None and nb > prev['nblk']:
        ev.append('M1 nblk_sig %g→%g' % (prev['nblk'], nb))
    if prev.get('nv') is not None and nv is not None and nv > prev['nv']:
        ev.append('M3 n_var_sig %g→%g' % (prev['nv'], nv))
    if prev.get('nf2') == 0 and nf2 is not None and nf2 > 0:
        ev.append('M2 nf2 0→%g' % nf2)
    prev = {'nblk': nb, 'nv': nv, 'nf2': nf2}
    return ev, prev


P = '_exp/_bk_t5/dry_t5N276/series.csv'
rows = list(csv.DictReader(open(P, newline='')))
blkidx = [i for i, r in enumerate(rows) if (r.get('nblk_sig') or '').strip()]
print('  真数据：%d 行；块表行 step = %s（索引 %s）'
      % (len(rows), [rows[i]['step'] for i in blkidx], blkidx))
print()

CASES = [('C1 正对照 M2（nf2 0→5）   ', 'nf2', '5', 'M2'),
         ('C2 正对照 M1（nblk 1→3）  ', 'nblk_sig', '3', 'M1'),
         ('C3 正对照 M3（nvar 1→4）  ', 'n_var_sig', '4', 'M3'),
         ('C4 负对照（两轮都不改）    ', None, None, None)]

ok_all = True
for name, col, val, want in CASES:
    # 第 1 轮：原样（只到第一个块表行）——建立 prev
    r1 = [dict(r) for r in rows[:blkidx[0] + 1]]
    ev1, prev = judge_round(r1, {})
    # 第 2 轮：全部行（可选注入）
    r2 = [dict(r) for r in rows]
    if col:
        i = blkidx[-1]
        r2[i] = dict(r2[i]); r2[i][col] = val
    ev2, prev = judge_round(r2, prev)
    got = [e.split()[0] for e in ev2]
    if want is None:
        ok = (len(got) == 0)
    else:
        ok = (want in got)
    ok_all &= ok
    print('  %-28s 第2轮触发 = %-22s ⇒ %s'
          % (name, (', '.join(got) if got else '（无）'), '✅' if ok else '❌ **不符**'))
    for e in ev2:
        print('        · %s' % e)
print()
print('  ⇒ **%s**' % ('四个对照全过 ⇒ 监视器可信（"没报警" = 真没变化）'
                     if ok_all else '有未过项 ⇒ 监视器须先修'))
sys.exit(0 if ok_all else 1)
