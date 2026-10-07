#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r283_summary7.py —— 摘要加入 `§153`（R165 × `--facet-proj 0` 已启动）。"""
from __future__ import annotations

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, 'AUDIT_SUMMARY_R76.md')
MARK = '## 14. 第七轮新增'

SEC = r"""
---

## 14. 第七轮新增（`§153`，2026-10-01）

### 14.1 ★★ **P0 跟进已启动：R165 在 `--facet-proj 0` 下重跑**

`§145.3` 给 R165 的否定结果（F2 界面能降 9.3 倍、`r_selfac` 只动 0.03%）
列了**三条叠加**原因：
① `--facet-proj 10` 压制界面能对形态的影响（`§144`/`§147`）；
② F2 只占总界面面积 **8.7%**（`§142.1`）；
③ F2 上界面能项本身只占 `|Δed|` 的 **2–9%**（`§141.1`）。

**本实验把 ① 去掉**（`--facet-proj 10 → 0`），其余逐字不动
（命令行由 `_r178_repro.py` 从归档 `exp_args` **逐参重建** + 追加 `--diag-terms`）。

**✅ R-1 前置核对（从打印出的最终命令行逐字核对）**：
两臂**只差 `--f2-pair-gamma`**（λ=0 vs 1.0）；
两臂与归档**只差 `--facet-proj 10→0` 与 `--diag-terms`** ⇒ **单变量成立、实验有效**。
⚠ `--nthreads` 3 vs 4 与归档一致，`§107`/`§151` 已证**并行逐位不变** ⇒ 无害（记账）。

**★ 另一条独立确认**：`_r281_check.sh` 直接读**存活进程的 cmdline**，
看到 `p45L0`/`p45P0` 的 `facet-proj 0`、`p45L`/`p45P` 的 `facet-proj 10`
⇒ **`_r253`/`_r225` 的开关设置被从**进程层**独立证实**（不只是脚本里写了）。

**预登记判据**：
* **R-2** ★ 核心：比较 `saSet2P0` vs `saSet2F2P0` 的 `r_selfac` 末态相对差与归档的
  **−2.72e-04**。**若 ≥10×（≈2.7e-3）⇒ ① 是主因**；**若仍 ≈2.72e-04 ⇒ ②③ 才是约束。**
* **R-3** `--diag-terms`：无投影时 F2 的 `|stk·κ|/|Δed|` 是否比归档时更大。
* ⚠ **两种结果都有信息量，都必须如实报。**

### 14.2 ⚠ 为腾算力先停 `saOddGDT`（**先论证，再动手**）

* **价值**：`_r210` 第二臂，只为给 `saSet2DT` 一个对照；而 `saSet2DT` **已跑满 400 步**并给出主结论。
* **成本**：实测 **~22 s/步** ⇒ 还要 **~2 小时**。
* **安全规程**：不用 `pkill -f`；按 **PID** 杀；PID 由 `--tag` **精确匹配** cmdline；
  **二次核对"`tag` 只出现一次"**；杀后**复验**（5 个正当臂全在、目标消失、**无孤儿**）。
* **实测**：`SIGTERM` 后**干净退出**；**无孤儿** ✅

### 14.3 ⚠ 我自己的两个调度错误（**都属硬规则 ㉘**）

1. `_r272`（上轮）：5 个并发臂叠在 6 个重进程上、**没做时间预算** ⇒ 被工具超时打断。
2. **`_r280` 第一次启动**：我把**长跑启动器**包在 `timeout 100` 里
   ⇒ 脚本在 `_r178_repro.py --emit` 阶段就被杀 ⇒ **一个臂都没起**（日志/产物全无）。

**⇒ 硬规则 ㉘ 补充**：**启动器本身是长跑**（它要 `wait` 子进程）
⇒ **必须用托管后台作业启动，不得用 `timeout` 包裹**。

### 14.4 在跑（7 个进程）

| 作业 | 进度 |
|---|---|
| `_r225`（`p45L`/`p45P`，**投影**，P1-45 基线）| ~360/400 |
| **`_r253`（P0，`--facet-proj 0`，P1-45）** | `p45L0`/`p45P0` ~140/400 |
| **`_r280`（P0，**本实验**，R165 × 0）** | `saSet2P0`/`saSet2F2P0` 刚启动（~51 min）|
| `_r240`（`saSet2EDV`，逐变体 `ed`）| ~100/400 |

**台账 10173 行、摘要 632+ 行、制表符 0**；负载 ~14/20 核、可用内存 ~13 GB ⇒ **未过载**。
"""


def main():
    with io.open(DOC, 'r', encoding='utf-8') as f:
        txt = f.read()
    n0 = txt.count('\n') + 1
    if MARK in txt:
        print('⚠ 摘要里已有 `%s`' % MARK)
        return 0
    assert txt.endswith('\n')
    assert '\t' not in SEC
    with io.open(DOC, 'a', encoding='utf-8', newline='') as f:
        f.write(SEC)
    with io.open(DOC, 'r', encoding='utf-8') as f:
        t2 = f.read()
    print('✅ 摘要：%d 行 → **%d 行**' % (n0, t2.count('\n') + 1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
