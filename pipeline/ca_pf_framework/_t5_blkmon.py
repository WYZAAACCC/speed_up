#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_blkmon.py --- ★★★★★ `t5N276` 的**块/块间影响**监控（补几何监控之外的 ③④）

## 为什么需要它
`_t5_armon.py` 只测**几何量**（长宽比/长厚比）⇒ 覆盖目标②，
但**不读块表列** ⇒ **目标③（成块）与④（块间影响）没有量具**。

## 本脚本读 `_exp/_bk_t5/dry_t5N276/series.csv` 的这些列
| 列 | 含义 | 对应目标 |
|---|---|---|
| `nslab_n` | 板条数（`nslab_n1` 等分量另有列）| **① 生长** |
| `Vt` | 已转变体积 | ① |
| **`nf3_col`** | **块内低角晶界（F3）的列数** | **③ 成块（块内被低角晶界分开）** |
| `runs` | 逐场的连通段数 | ③ |
| **`nblk_sig`** | **显著块数**（≥32 体素的分量）| **③ 成块** |
| **`n_var_sig`** | **显著变体数** | **⑤ 自协调** |
| **`nf2`** | **异变体界面数** = **块与块相遇的签名** | **④ 块间影响** |
| **`f2_area_m2`** | 异变体界面面积 | ④ |
| `blk_laths` | 每块的板条数分布（如 `24/1`）| ③ |

**⚠ 口径纪律（沿用本项目既有结论）**：
* **判据③ 用 `nblk_sig`（显著块数），不用易抖动的 `nblk总`**；
* **`nf2=0` ⟺ 两块**真正分离**（`_bk_exp.py:1513` 逐字）**；
* **块表列只在 `--every 100` 的倍数行才有值** ⇒ **本脚本只报"有值的最后一行"**，
  并**明确标出该行的 step**（避免把空行当 0，这是本项目记过的坑）。
"""
import csv
import sys
import time

CSV = '_exp/_bk_t5/dry_t5N276/series.csv'
LOG = '_w2_t5_n276_monitor.log'
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 300

COLS = ['step', 'Vt', 'nslab_n', 'nf3_col', 'runs', 'nf3', 'nf2', 'f2_area_m2',
        'nblk_sig', 'n_var_sig', 'n_hab', 'r_selfac', 'blk_laths']


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def read_last():
    """返回 (最后一行, 最后一个**块表列有值**的行)；两者都带 step

    ★ s240 修正：块表行 = **`nblk_sig` 非空**（**不是** `nf2` 非空）。
      实测（`_t5_blkcol.sh`）：块表值只出现在 **step 的 100 倍数**行（step 0/100 …），
      而 `nf2` 是**常规列**（每行都有值）⇒ 用 `nf2` 判断会把普通行当块表行 ⇒ **永远读不到 nblk_sig**。
    """
    last = None
    last_blk = None
    try:
        with open(CSV, newline='') as f:
            for r in csv.DictReader(f):
                last = r
                if (r.get('nblk_sig') or '').strip() not in ('',):
                    last_blk = r
    except Exception as e:
        return None, None, str(e)
    return last, last_blk, None


say('════ t5N276 块/块间影响监控启动：%d 轮 × %d s ════' % (ROUNDS, GAP))
say('  覆盖：③ 成块（nblk_sig/nf3_col/runs）· ④ 块间影响（nf2/f2_area）· ⑤ 自协调（n_var_sig）')
for i in range(1, ROUNDS + 1):
    last, blk, err = read_last()
    if err:
        say('第 %d 轮 ⚠ 读失败：%s' % (i, err))
    elif last is None:
        say('第 %d 轮 （series.csv 尚无数据 —— 构造期）' % i)
    else:
        say('第 %d 轮 ── 最新行 step=%s ──' % (i, last.get('step')))
        say('   ① 生长：Vt=%.4g µm³ · nslab_n=%s · nf3_col=%s · runs=%s'
            % (float(last.get('Vt') or 0) * 1e18, last.get('nslab_n'),
               last.get('nf3_col'), last.get('runs')))
        if blk is None:
            say('   ③④⑤ **块表列尚无值**（只在 --every 100 的倍数行才有）⇒ 本轮无法判定')
        else:
            say('   ③ 成块：**nblk_sig=%s** · runs=%s · nf3_col=%s · blk_laths=%s'
                % (blk.get('nblk_sig'), blk.get('runs'), blk.get('nf3_col'),
                   blk.get('blk_laths') or '（无）'))
            say('   ④ 块间影响：**nf2=%s** · f2_area=%s m²  ⇒ %s'
                % (blk.get('nf2'), blk.get('f2_area_m2'),
                   '**已相遇**' if (blk.get('nf2') or '0').strip() not in ('', '0', '0.0')
                   else '两块仍**分离**'))
            say('   ⑤ 自协调：**n_var_sig=%s** · n_hab=%s · r_selfac=%s'
                % (blk.get('n_var_sig'), blk.get('n_hab'), blk.get('r_selfac')))
            say('      （块表行 step=%s）' % blk.get('step'))
    time.sleep(GAP)
say('════ 监控结束（%d 轮）════' % ROUNDS)
