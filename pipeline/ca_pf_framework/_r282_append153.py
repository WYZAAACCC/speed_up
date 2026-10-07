#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r282_append153.py —— 追加 `§153`：**R165 × `--facet-proj 0`** 已启动（R-1 前置全过）。"""
from __future__ import annotations

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
MARK = '## §153'

SEC = r"""
---

## §153（R279–R282）★★ **P0 跟进已启动：R165 在 `--facet-proj 0` 下重跑**（R-1 前置全过）

> 脚本：`_r279_killsaOddGDT.sh`（腾算力）、`_r280_r165proj0.sh`（本实验）、
> `_r281_check.sh`；日志 `_w2_r280.log`
> 上游：`§144`/`§147`（投影压制界面能）、`§145.3`（R165 否定结果的三条叠加归因）

### §153.1 为什么先停 `saOddGDT`（**先论证，再动手**）

| 项 | `saOddGDT` |
|---|---|
| 价值 | `_r210` 的**第二臂**，只为给 `saSet2DT` 一个"非自协调几何"的对照；而 `saSet2DT` **已跑满 400 步**并给出主结论（`§145.2`）|
| 成本 | 实测 **~22 s/步** ⇒ 400 步还要 **~2 小时** |

**⇒ 停它，把算力让给本节的 P0（价值高得多）。**
**安全规程**（`AGENTS.md §3.10`/`§3.11`）：**不用 `pkill -f`**；按 **PID** 杀；
PID 由 `--tag saOddGDT` **精确匹配** cmdline 得到；**二次核对"`tag` 在 cmdline 里只出现一次"**；
杀后**复验**——期望 `p45L`/`p45P`/`p45L0`/`p45P0`/`saSet2EDV` **仍在**、`saOddGDT` **消失**、
**且无 cwd 带 `(deleted)` 的孤儿**。

**实测**：`SIGTERM` 后 `saOddGDT` **立即干净退出**；5 个正当臂全在；**无孤儿** ✅

### §153.2 本实验的设计（**单变量：只改 `--facet-proj`**）

命令行由 `_r178_repro.py --emit` 从归档 `dry_saSet2` / `dry_saSet2F2` **逐参重建**，
只做两处替换 + 一处追加：
1. `--facet-proj 10 → 0`；
2. `--tag`（写独立目录）；
3. **追加 `--diag-terms`**（拿三项量级，看界面能项在无投影时是否变"活"）。

### §153.3 ✅ **R-1 前置核对（从打印出的最终命令行逐字核对）**

| 项 | `saSet2P0`（λ=0）| `saSet2F2P0`（λ=1）| 判定 |
|---|---|---|---|
| `--facet-proj` | **0** | **0** | ✅ |
| `--tag` | `saSet2P0` | `saSet2F2P0` | ✅ 目录独立 |
| `--f2-pair-gamma` | **无** | **1.0** | ✅ **这就是自变量** |
| `--diag-terms` | 有 | 有 | ✅ |
| `--nthreads` | 3 | 4 | ⚠ 与归档一致；`§107`/`§151` 已证**并行逐位不变** ⇒ 无害，**记账** |
| 其余 ~110 个 token | 与归档**逐字相同** | 同 | ✅ |

**⇒ 两臂**只差 `--f2-pair-gamma`**；两臂与归档**只差 `--facet-proj 10→0` 与 `--diag-terms`**
⇒ **R-1 通过，实验有效。**

**★ 附带一条独立确认**：`_r281_check.sh` 直接读**存活进程的 cmdline**，
看到 `p45L0`/`p45P0` 的 `facet-proj 0`、`p45L`/`p45P` 的 `facet-proj 10`
⇒ **`_r253` 与 `_r225` 的开关设置被从**进程层**独立证实**（不只是脚本里写了）。

### §153.4 预登记判据（`_r280` 头部已写死）

* **R-2** ★ **核心**：`saSet2P0` vs `saSet2F2P0` 的 **`r_selfac` 末态相对差**，
  与归档（`saSet2` vs `saSet2F2`）的 **−2.72e-04** 比。
  * **若新相对差 ≥ 10×（≈2.7e-3）⇒ `§145.3` 的原因①（投影压制）是主因**；
  * **若仍 ≈ 2.72e-04 ⇒ 原因②③（F2 只占 8.7% 面积、其上界面能项只占 2–9%）才是约束。**
* **R-3** `--diag-terms`：无投影时 F2 的 `|stk·κ|/|Δed|` 是否比归档时更大。
* ⚠ **两种结果都有信息量，都必须如实报。**

### §153.5 ⚠ 我自己的两个调度错误（**都属硬规则 ㉘ 的同类**）

1. **`_r272`**（上一轮）：5 个并发臂叠在 6 个重进程上、**没做时间预算** ⇒ 被工具超时打断。
2. **`_r280` 第一次启动**：我把**长跑启动器**包在 `timeout 100` 里
   ⇒ 脚本在 `_r178_repro.py --emit` 阶段就被杀 ⇒ **一个臂都没起**（日志/产物全无）。
   **⇒ 修正**：改用**托管后台作业**（`run_in_background`），**不用 shell `timeout` 包长跑**。

**⇒ 硬规则 ㉘ 补充**：
**启动器（launcher）本身是长跑**（它要 `wait` 子进程）⇒
**必须用托管后台作业启动，不得用 `timeout` 包裹**。

### §153.6 在跑（7 个进程）

| 作业 | 进度 |
|---|---|
| `_r225`（`p45L`/`p45P`，**投影**，P1-45 对照基线）| ~360/400（即将完成）|
| **`_r253`（P0，`--facet-proj 0`）** | `p45L0`/`p45P0` ~140/400 |
| **`_r280`（P0，**本实验**）** | `saSet2P0`/`saSet2F2P0` 刚启动（400 步，~7.6 s/步 ⇒ ~51 min）|
| `_r240`（`saSet2EDV`，逐变体 `ed`）| ~100/400 |
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
