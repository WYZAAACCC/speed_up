#!/bin/bash
# _t5_git_s252.sh --- 落盘：形核账目监控 + stack 判定作业 + 修复版重跑启动器
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_nucmon.py \
        pipeline/ca_pf_framework/_t5_start_nucmon.sh \
        pipeline/ca_pf_framework/_t5_restart_nucmon.sh \
        pipeline/ca_pf_framework/_t5_waitstack.sh \
        pipeline/ca_pf_framework/_t5_nv276F.sh \
        pipeline/ca_pf_framework/_t5_mon_add276F.sh \
        pipeline/ca_pf_framework/_t5_fraggeom.py \
        pipeline/ca_pf_framework/_t5_smokechk.sh \
        pipeline/ca_pf_framework/_t5_smokefin.sh \
        pipeline/ca_pf_framework/_t5_smoke_stack.sh \
        pipeline/ca_pf_framework/_t5_fix_commit_smoke.sh \
        pipeline/ca_pf_framework/_t5_perconn.py \
        pipeline/ca_pf_framework/_t5_capnum.sh \
        pipeline/ca_pf_framework/_t5_prog.sh \
        pipeline/ca_pf_framework/_t5_damage.sh \
        pipeline/ca_pf_framework/_t5_vardist.py \
        pipeline/ca_pf_framework/_t5_fragnbr.py \
        pipeline/ca_pf_framework/_t5_gap.py \
        pipeline/ca_pf_framework/_t5_fragbirth.py \
        pipeline/ca_pf_framework/_t5_newfield.py \
        pipeline/ca_pf_framework/_t5_degrade.py \
        pipeline/ca_pf_framework/_t5_recomp.py \
        pipeline/ca_pf_framework/_t5_conn.py \
        pipeline/ca_pf_framework/_t5_regchk.py \
        pipeline/ca_pf_framework/_t5_solidity.py \
        pipeline/ca_pf_framework/_t5_final3d.py \
        pipeline/ca_pf_framework/_t5_3dview.py \
        pipeline/ca_pf_framework/_t5_3dview2.py \
        pipeline/ca_pf_framework/_t5_birth.sh \
        pipeline/ca_pf_framework/_t5_nfsvA.sh \
        pipeline/ca_pf_framework/_t5_seedcode.sh \
        pipeline/ca_pf_framework/_t5_seedcall.sh \
        pipeline/ca_pf_framework/_t5_vrconsume.sh \
        pipeline/ca_pf_framework/_t5_argdiff.sh \
        pipeline/ca_pf_framework/_t5_logfind.sh \
        pipeline/ca_pf_framework/_t5_freshchk.sh \
        pipeline/ca_pf_framework/_t5_seedcode.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s252 工具落盘：形核账目监控 · stack 判定 · 修复版重跑（t5N276F）

## 本批新增的关键工具（**对应扩展后的用户目标**）
| 工具 | 覆盖的目标 |
|---|---|
| **`_t5_nucmon.py`** | **① 形核的数量与时间 ② 马氏体数量是否够 ③ 板条是否正确对应到各自的场** |
| **`_t5_waitstack.sh`** | **等首个 `stack` 事件，直接判"修复在真实算例上是否生效"** |
| **`_t5_nv276F.sh`** | **修复版重跑**（与 `t5N276` 逐项一致，唯一差别 = 代码修复）|
| `_t5_mon_add276F.sh` | 把 `t5N276F` 纳入几何/块两路监控 |
| `_t5_fraggeom.py` | 碎片几何（质心位移 ⇒ 判"跨盒面折返"还是"独立核"）|
| `_t5_perconn.py` | **周期 vs 非周期**连通（判碎片是否盒面假象）|
| `_t5_fragnbr.py` | **按碎片**测邻居成分（判"表示斑驳"还是"物理独立"）|
| `_t5_recomp.py` | **按连通分量**重测形状（修正"按场测"的口径错误）|
| `_t5_gap.py`（膨胀半径扫描）· `_t5_conn.py`（三档连通）· `_t5_solidity.py`（实心度）|
| `_t5_capnum.sh` · `_t5_prog.sh` · `_t5_damage.sh` · `_t5_vardist.py` · `_t5_fragbirth.py` |
| `_t5_final3d.py` · `_t5_3dview*.py`（三维图，英文标签版可读）|

## 本轮的判定链（**五个候选逐一被实测排除**）
| # | 候选 | 判定 |
|---|---|---|
| 1 | `--var-rule ed` 槽位耗尽 ⇒ 退路 | ❌ 证伪（`nfsv_strict=True` 默认禁用退路；`t5NR`/random 也碎）|
| 2 | `nfsv` 找不到空场 | ❌ 证伪（`nfsv_ok=67`，`nfsv_nofield` 从未触发）|
| 3 | 最小镜像跨盒面 | ❌ 证伪（周期连通后仍 279 块）|
| 4 | 残余母相薄膜切割 | ❌ 证伪（膨胀 12 体素后仍 11/20 场多块）|
| 5 | 同变体碰撞前沿归属斑驳 | ❌ 证伪（**按碎片**测：90% 碎片隔的是**母相**）|

## ★★ 而真正的根因（**已修，见 b8108011**）
**`stack` 分支三处用源场 `k` 而非新场 `k_new`** ⇒
**15 次 stack 不产生新板条（少 15 根）+ 同一场被塞第二/三个种子（"碎片"）**。
**⇒ 实测账目：计划 66 根 ⇒ 实际 19 根；唯一性 0.56。**

## 碎片口径的更正（**我先前夸大了**）
冒烟测试实测：所谓"2–5 个碎片"其实是 **1 个主块（1466–2095 胞）+ 1–2 个微小卫星（35–736 胞）**，
**多数场的最大块占比 **97–100%**** ⇒ **"碎片个数"这个指标误导** ⇒
**正确口径是「最大连通分量占比」**（已记账）。

## 修复版重跑（`t5N276F`）的预登记判据
① `nslab_n` 应从 19 升到接近 69 ② 唯一性应从 0.56 升到 ≈1.0
③ 按分量的长宽比应显著高于 2.93 ④ 最大块占比应 ≥90% ⑤ `nblk_sig≥2` 且 `nf2>0`
MSGEOF
git log --oneline -1
