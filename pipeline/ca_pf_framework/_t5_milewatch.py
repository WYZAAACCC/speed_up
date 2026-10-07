#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_milewatch.py --- ★★★★★ `t5N276` 的**里程碑监视器**：③④⑤ 一有变化就落盘报警

## 为什么（用户目标 = ③是否成块 ④块间是否相互影响）
**每 5 分钟的常规轮询会产出大量"没变"的行** ⇒ 需要在**真正变化**时才有信号。
**⇒ 本脚本只在下列任一**跃迁**发生时写一条带 ★ 的记录**：

| 里程碑 | 判据（**预先写死**）| 对应目标 |
|---|---|---|
| **M1 块数增加** | `nblk_sig` 比上一有值点**变大** | **③ 成块** |
| **M2 块间相遇** | **`nf2` 从 0 变成 > 0**（`_bk_exp.py:1513` 逐字：`F2 面数==0` ⟺ 两块真正分离）| **④ 块间影响** |
| **M3 多变体** | `n_var_sig` 比上一点**变大** | **⑤ 自协调** |
| **M4 板条数跳变** | `nslab_n` 增加 ≥ 5 | ① 生长 |
| **M5 异常** | 某行的 `Vt` 比上一行**减小**（不应发生）| 健康 |

**⚠ 同时**每小时**打一条心跳（含当前全部关键量），以便"没消息"不等于"死了"。**
"""
import csv
import sys
import time

CSV = '_exp/_bk_t5/dry_t5N276/series.csv'
LOG = '_w2_t5_n276_milestones.log'
GAP = int(sys.argv[1]) if len(sys.argv) > 1 else 120
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 400


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def load():
    rows = []
    try:
        with open(CSV, newline='') as f:
            for r in csv.DictReader(f):
                rows.append(r)
    except Exception:
        pass
    return rows


def num(r, k):
    v = (r.get(k) or '').strip()
    try:
        return float(v)
    except Exception:
        return None


say('════ t5N276 里程碑监视器启动（每 %d s，共 %d 轮）════' % (GAP, ROUNDS))
say('  报警条件（**预先写死**）：nblk_sig↑ · **nf2 由 0 变 >0** · n_var_sig↑ · nslab_n +5 · Vt 减小')

prev = {}
last_beat = 0.0
for i in range(ROUNDS):
    rows = load()
    if rows:
        last = rows[-1]
        # 块表点（nblk_sig 非空）里最新的一条
        blk = None
        for r in rows:
            if (r.get('nblk_sig') or '').strip():
                blk = r
        st = last.get('step')
        Vt = num(last, 'Vt')
        nslab = num(last, 'nslab_n')
        # M5 异常
        if prev.get('Vt') is not None and Vt is not None and Vt < prev['Vt'] - 1e-12:
            say('★M5⚠ 异常：Vt 减小（step %s：%.4g → %.4g µm³）' %
                (st, prev['Vt'] * 1e18, Vt * 1e18))
        prev['Vt'] = Vt
        # M4 板条跳变
        if prev.get('nslab') is not None and nslab is not None and nslab - prev['nslab'] >= 5:
            say('★M4 板条数跳变：nslab_n %.0f → **%.0f**（step %s）'
                % (prev['nslab'], nslab, st))
        prev['nslab'] = nslab
        if blk is not None:
            nb = num(blk, 'nblk_sig')
            nv = num(blk, 'n_var_sig')
            nf2 = num(blk, 'nf2')
            if prev.get('nblk') is not None and nb is not None and nb > prev['nblk']:
                say('★M1 **块数增加**：nblk_sig %.0f → **%.0f**（块表 step %s）· blk_laths=%s'
                    % (prev['nblk'], nb, blk.get('step'), blk.get('blk_laths')))
            if prev.get('nv') is not None and nv is not None and nv > prev['nv']:
                say('★M3 **多变体**：n_var_sig %.0f → **%.0f**（块表 step %s）· n_hab=%s'
                    % (prev['nv'], nv, blk.get('step'), blk.get('n_hab')))
            if prev.get('nf2') == 0 and nf2 is not None and nf2 > 0:
                say('★M2 ★★★★★ **块间相遇**：nf2 由 0 → **%.0f**（块表 step %s）· '
                    'f2_area=%.4g m² ⇒ **两块不再分离**' % (nf2, blk.get('step'),
                                                          num(blk, 'f2_area_m2') or 0.0))
            prev['nblk'], prev['nv'], prev['nf2'] = nb, nv, nf2
        # 心跳（每 30 分钟）
        if time.time() - last_beat > 1800:
            say('  ♥ 心跳 step=%s Vt=%.3f µm³ nslab_n=%s｜块表(step %s): nblk_sig=%s '
                'n_var_sig=%s nf2=%s'
                % (st, (Vt or 0) * 1e18, last.get('nslab_n'),
                   (blk or {}).get('step'), (blk or {}).get('nblk_sig'),
                   (blk or {}).get('n_var_sig'), (blk or {}).get('nf2')))
            last_beat = time.time()
    time.sleep(GAP)
say('════ 监视器结束 ════')
