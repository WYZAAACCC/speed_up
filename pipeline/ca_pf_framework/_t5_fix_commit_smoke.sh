#!/bin/bash
# _t5_fix_commit_smoke.sh --- 提交修复 + 起冒烟测试（验证 stack 现在真的建新场）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/windowB_surface.py \
        pipeline/ca_pf_framework/_t5_fix_stack.py \
        pipeline/ca_pf_framework/_t5_verify_fix.sh \
        pipeline/ca_pf_framework/_t5_nucacct.py \
        pipeline/ca_pf_framework/_t5_deep1.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s251 ★★★★★★ 修 `stack` 通道不建新场的缺陷（一行级三处）

## 缺陷（逐字定位，`windowB_surface.py`）
三个通道播种时用的场号：
```
2173:  out.append((kk,    'fresh'))    ✓ 新场
2567:  self.seed_plate(k_new, …)        ✓ 新场
2572:  out.append((k_new, 'attach'))    ✓ 新场
2629:  self.seed_plate(**k**, …)        ✗ **源场**
2632:  along=_along_of(**k**)           ✗ **源场**
2634:  out.append((**k**, 'stack'))     ✗ **源场**
```
=> **`nfsv` 算出了新场 `k_new`（2320–2332），但 `stack` 分支三处都用源场 `k` ⇒ 新场被丢弃。**

## 后果（**实测账目，`_t5_nucacct.py`**）
```
t5N276：34 个形核事件
   attach 18 次 ⇒ **创建 18 个新场** ✓
   fresh   1 次 ⇒ **创建  1 个新场** ✓
   **stack 15 次 ⇒ 创建 0 个新场** ✗
=> 不同场号只有 **19** 个 ⇒ **19 根板条**
=> 引擎计划 **66** 根（`n_target`）⇒ 实际 19 根 ⇒ **少 15 根，正好 = stack 次数**
=> 而同一个场被塞进第二个种子 ⇒ **碎片化**（实测：新场首现即 2–5 块）
```
**⇒ 一个缺陷同时造成两个现象：板条数只有 1/3.5，且场被"撑碎"。**
**⚠ 也解释了 `nfsv_ok = 67`（算了但没用）与 `nfsv_nofield = 0`（从不缺空场）。**

## 修法（**最小改动，默认路径逐位不变**）
三处 `k` → `k_new`。**安全性论证**：
1. `k_new` 初值 = `k`（2320 行），**只有 `nfsv` 找到空场时才被改写**
   ⇒ **`nfsv` 关掉时三处仍是 `k`** ⇒ **逐位不变** ✓;
2. `nfsv` 要求**同变体**（`vg.get(_j) == _v`）⇒ `_along_of(k_new)` 与 `_along_of(k)` **同向** ✓;
3. `cover`/`reg` 守卫（2625）不引用 `k` ⇒ 不受影响 ✓。

## 验证（**已完成**）
* `py_compile` 通过（**对磁盘文件**，不只内存字符串）;
* `diff` 恰好 **3 行**（`seed_plate` / `along` / `out.append`）;
* 三通道口径复核：fresh ✓ · attach ✓ · **stack ✓（本次修）**;
* 备份 `windowB_surface.py.bak_stackfield`（sha256 前 16 位 `ba087645f5fb43f1`）;
* **冒烟测试已起**（下一步，判据：`stack` 事件的场号必须是**新场**）。

## ⚠ 记账
本条是**代码缺陷修复**，不涉及物理/数值方案选择 ⇒ 未改动任何物理参数。
MSGEOF
git log --oneline -1
