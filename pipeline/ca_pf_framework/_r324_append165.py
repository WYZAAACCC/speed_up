#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r324_append165.py —— 追加 `§165`：**执行 `§164.5` 的待办**（框架级实验的时间窗延长）。"""
from __future__ import annotations

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
MARK = '## §165'

SEC = r"""
---

## §165（R322–R324）**执行 `§164.5` 的待办：框架级实验的时间窗延长到 200 步**

> 脚本：`_r322_edvar200.sh`、`_r323_status.sh`；日志 `_w2_r322.log`
> 上游：`§164`（框架级判决"σ 不由变体配置主导"）与其 `§164.5` **自己写下的边界**

### §165.1 为什么必须延（`§164.5` 原文）

`§164` 的结论**只在 step 20–60 上测过**，而那时**板条尚未充分接触**
（`§145.2`：F2 胞数 step 40 才 ~9 个、step 80 才上百）
⇒ **σ 可能还没"看见"彼此**。
**⇒ 必须延到板条充分接触之后再判一次。**

### §165.2 设计（与 `_r318` **逐字相同**，只把 `--steps 60` 改成 **200**）

| 臂 | `--laths` | 变体对 | `‖ε⁰₁−ε⁰_w‖_F` |
|---|---|---|---|
| `near200` | `1,1,1,2,2,2` | V1–V2 | **0.025990**（0.21×）|
| `mid200` | `1,1,1,3,3,3` | V1–V3 | **0.123728**（1.00×）|
| `far200` | `1,1,1,5,5,5` | V1–V5 | **0.242277**（1.96×）|

**⇒ 三臂只差 `--laths`，其余（N=96 / `plate-L 1600` / `--multi-block` / `facet-proj 10` /
`--diag-edv`）逐字相同。**

### §165.3 判据（**先写死**）

* **Q-1** 三臂几何验收：`nf2(t=0)=0` 且 `cov_norm ≥ 0.95`（不过则报"**不适用**"）。
* **Q-2 ★ 核心**：在 **step 100 / 120 / … / 200**（板条**已充分接触**）上，
  "`ed` 离散度是否随 `‖Δε‖` 单调增"。
  * **若仍不单调** ⇒ `§164` **加强**（"σ 不由变体配置主导"是**长期**性质）；
  * **若变为单调** ⇒ `§164` **只在早期成立**，必须记账为**时间受限**的结论。

### §165.4 状态

| 臂 | 进度 |
|---|---|
| `near200` / `mid200` / `far200` | 各 **20 / 200**（实测 ~6 s/步 ⇒ 约 18 min）|
| `_r280` `saSet2P0` / `saSet2F2P0`（**最后一个 P0**）| **260 / 300** of 400 |
| `_r240` `saSet2EDV` | **380 / 400**（即将完成）|

* 主机：**6 个 `_bk_exp` 进程**、负载 **13.3 / 20 核**、可用内存 **14.5 GB** ⇒ **未过载**。
* 文档：台账 **10962 行**、摘要 **981 行**、**制表符 0**。
"""


def main():
    with io.open(LED, 'r', encoding='utf-8') as f:
        txt = f.read()
    n0 = txt.count('\n') + 1
    if MARK in txt:
        print('⚠ 已有 `%s` ⇒ 不重复追加（当前 %d 行）' % (MARK, n0))
        return 0
    assert txt.endswith('\n'), '台账末尾不是换行'
    assert '\t' not in SEC, '正文里有制表符'
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
