#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r193_append133.py —— 追加 `§133`：**W-1 惰性闭环通过** + `_r171` 接线核对。"""
from __future__ import annotations

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
MARK = '## §133'

SEC = r"""
---

## §133（R184/R192）✅ **W-1 惰性闭环通过**：`§129` 的代码改动对 λ=0 路径逐位惰性

> 脚本：`_r178_repro.py`（从 meta 逐参重建命令行）、`_r179_inert.sh`、
> `_r184_inert_cmp.py`、`_r192_cols.sh`；日志 `_w2_r179.log`
> 上游：`§129.6` 的 W-1（`dry_saSet2F2` 与 `dry_saSet2` 的**代码 SHA 不同**）

### §133.1 问题

`§129` 的 W-1 核对发现：`dry_saSet2F2`(λ=1) 与 `dry_saSet2`(λ=0) 的
`sha_exp` / `sha_windowB_lath` / `sha_measure` **三者全不同**（本轮改过这三个文件）。
**⇒ "代码变了"是**独立于 λ 的第二个变量**，不能靠"我认为 λ=0 是惰性的"排除。**

### §133.2 做法（**关键：不手工敲命令行**）

`_r178_repro.py` 从归档 `meta.json` 的 **`exp_args`（= `vars(a)`，`_bk_exp.py:1013`）**
**逐键重建**命令行（115 个 token），只**显式覆盖**三处：
`tag=saSet2INERT`（写到独立目录，不碰归档）、`steps=120`（省时）、`out=_exp/_bk_mb`。
**不传 `--f2-pair-gamma`** ⇒ 默认 0.0 ⇒ 应与归档同路径。

**⇒ 为什么必须这样做**：手工重建一定会漏参数 —— `§129.6` 就是这样才发现
`nthreads 3→4` 这个**第二个变量**的。重建出的命令里
`--nthreads 3` / `--omega-mode ladder` / `--rank1-swap none` 都与归档一致（已逐项核对）。

### §133.3 结果：**逐位相同**

`_r184_inert_cmp.py` 比**每一列**（不只 `Vt` —— `§116` 的教训是 55/97 列会变）：

| 项 | 结果 |
|---|---|
| 共同步 | `0, 20, 40, 60, 80`（5 个）|
| 可比列 | **93** 个 |
| **逐位相同的列** | **93 / 93** ✅ |
| **最大相对差（全表）** | **0.000e+00** |

**⇒ I-1 通过** ⇒ `windowB_lath.py` 的 `f2_lam` / `_bk_exp.py` 的 `--f2-pair-gamma`
**对 λ=0 路径完全惰性** ⇒ **R165 是合法单变量对照**。

**⇒ 一个预判被证实**：`step 0` 的逐字段比对（`_r186_early.sh`）显示
**唯一不同的字段是 `wall_s`（1.8 vs 1.64）** —— **墙钟时间，不是物理**
⇒ 93 个物理字段在 `t=0` 就已经逐位相同。（`_r184` 已把 `wall_s` 列入 `SKIP`。）

### §133.4 `_r171` 判决脚本的接线核对（`_r192_cols.sh`）

**先查脚本要读的列到底存不存在**（硬规则 ⑩；`_r105`/`_r134` 就是栽在读错东西上）：

| `_r171` 要读的列 | 存在？ |
|---|---|
| `step` / `r_selfac` / `E_el_J` / `Vt` | ✅ |
| `f3_area_m2` / `f2_area_m2` / `nf2` | ✅ |
| `box_touch_core` / `blk_nprof` / `nblk_sig` | ✅ |

（`series.csv` 共 **94** 列，含 `E_el_J`、`blk_span_nm`、`n_var_sig`、`r_selfac` 等。）

⚠ **另记一条接线风险**：`_r184` 也曾发现 `meta.json`
**顶层没有 `f2_pair_gamma` 键**（λ 只在 `exp_args` 里）⇒
**任何 `m.get('f2_pair_gamma', 0)` 的写法都会把 λ=1 静默读成 λ=0**
（`§129.4` 的第 3 个假阳性就是这么来的）。
`_r171` 不读 meta（只读 `series.csv`）⇒ **不受影响** ✅。

### §133.5 本节结论

✅ W-1 **闭环通过**：代码改动惰性 ⇒ R165 的单变量性成立；
✅ `_r171` 的列接线正确，可以读 G-1…G-4；
⏳ R165（λ=1 两臂）跑到 step 340/400。
"""


def main():
    with io.open(LED, 'r', encoding='utf-8') as f:
        txt = f.read()
    n0 = txt.count('\n') + 1
    if MARK in txt:
        print('⚠ 已有 `%s` ⇒ 不重复追加（当前 %d 行）' % (MARK, n0))
        return 0
    assert txt.endswith('\n'), '台账末尾不是换行'
    assert '\t' not in SEC, '待追加正文里有制表符'
    with io.open(LED, 'a', encoding='utf-8', newline='') as f:
        f.write(SEC)
    with io.open(LED, 'r', encoding='utf-8') as f:
        t2 = f.read()
    n1 = t2.count('\n') + 1
    print('✅ 台账：%d 行 → **%d 行**（+%d）；制表符 = %d'
          % (n0, n1, n1 - n0, t2.count('\t')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
