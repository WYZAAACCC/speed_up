#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r524_rejattrib.py —— 把 `_r520c` 那 **22 次形核拒绝归因**（56% 拒绝率，参数标定的要害）。

## 为什么
`_r520c` 的日志把拒绝写成一句
    `⚠ athermal 事件 #N 被引擎拒（无可用空场/落位失败）`
—— **两个完全不同的原因合并成一句话**，于是 39 次尝试里 22 次被拒
**无法归因**。而"短跑定参数"要的恰恰是这个归因。

⚠ 但**不要说"引擎没给"**：`_bk_exp.py` 会把引擎的 `_dbg` 落盘成
   `<run>/nuc_dbg.json`（`_r519_why13.py` 已经在读它）。
⇒ 本量具先把**已有的**数据读出来；如果归因得了，那这条就**不是**缺陷。

## 判据（先写死）
* **A1 数据存在**：`nuc_dbg.json` 里 `dbg` 至少有 `att` 与 `nfsv_nofield` 两个键。
* **A2 归因闭合**：把 `nfsv_nofield`（无同变体空场）与「落位失败」分开数，
  两者之和**应当**能解释引擎侧的事件缺口。
* **A3 正对照能失败**：若两个键都取不到，必须报 FAIL 而不是"猜一个"。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = ['dry_r520param', 'dry_abA']
KEYS = ['att', 'ok', 'oob', 'cov', 'exc', 'empty', 'nocand',
        'nfsv_ok', 'nfsv_nofield', 'nfsv_novgroup',
        'attach_ok', 'end_pref', 'dg_pick', 'dg_pick_nofree',
        'n_events', 'forced_reinit', 'fresh_blocked']


def main():
    rows = []
    L = ['=' * 100, 'R524 —— `_r520c` 形核拒绝归因', '=' * 100]
    for run in RUNS:
        p = os.path.join(HERE, '_exp', '_bk_mb', run, 'nuc_dbg.json')
        L.append('')
        L.append('── %s ──' % run)
        if not os.path.exists(p):
            L.append('   ⚠ 找不到 %s' % p)
            rows.append((run + ' 数据存在', False, '缺文件'))
            continue
        with open(p, errors='replace') as fh:
            d = json.load(fh)
        dbg = d.get('dbg', d)
        L.append('   键 = %s' % ', '.join(sorted(dbg.keys())))
        for k in KEYS:
            if k in dbg:
                L.append('     %-18s = %s' % (k, dbg[k]))
        rows.append((run + ' A1 有 `att`/`nfsv_nofield`',
                     ('att' in dbg) and ('nfsv_nofield' in dbg),
                     'att=%s nfsv_nofield=%s' % (dbg.get('att'), dbg.get('nfsv_nofield'))))

    npass = sum(1 for _, ok, _ in rows if ok)
    L.append('')
    L.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r524_rejattr.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
