#!/bin/bash
# _t5_git_s239.sh --- ★★★★★★ 起 5 µm 盒 · nv=276(12 变体) · eng-elong=7 · 全算子 · 断点续跑
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_nv276.sh pipeline/ca_pf_framework/_t5_n276chk.sh \
        pipeline/ca_pf_framework/_t5_whopid.sh pipeline/ca_pf_framework/_t5_stop_old.sh \
        pipeline/ca_pf_framework/_t5_stop_old2.sh pipeline/ca_pf_framework/_t5_mature.py \
        pipeline/ca_pf_framework/_t5_fillnum.sh pipeline/ca_pf_framework/_t5_armon.py 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s239 ★★★★★★ 起 5 µm 盒 · nv=276(12 变体) · eng-elong=7 · 全算子 · 断点续跑

## 用户要求（原话）
"起一个 5 微米计算盒子内，nv=276，nvar 为 12，N=160 的仿真算例，用上之前证明有效的 eng-elong，
使用断点续跑以及所有优化过的算子，如果内存不够的话就关掉几个进程。我需要在这个算例里面观察到
马氏体板条正常生长，长宽比要正常，马氏体板条之间堆叠成块，并且块与块之间相互影响并且出现自协调。"

## ⚠ 我改了一处参数（**记账，理由**）
**"5 µm 盒" 与 "N=160" 互斥**：
 * N=160 × dx=62.5 nm = **10.00 µm**（不是 5 µm）；
 * 要 5.00 µm：① N=80 + dx=62.5 nm  ② N=160 + dx=31.25 nm；
 * 而方案 ② 的 N³ 与 N=160 相同 ⇒ `nv=276` 需 **~42 GB** ⇒ **超本机 22 GB（不可行）**。
=> **取 N=80（dx=62.5 nm）= 真正的 5.00 µm 盒** ⇒ `nv=276` 只需 ~5.7 GB ⇒ **可行** ✓

## 配置（逐项）
 --N 80（盒 5.00 µm）· --nvar 12（= Ti64 的 Burgers 变体数）· --m 23 ⇒ **nv = 12×23 = 276**
 --B 3（B·n = 3×23 = 69 ≤ 276；N8 自洽 ceil(69/23)=3）
 --eng-elong 7.00（**已证明有效**：长宽比 1.85→6.55，稳定 ≤2%/5× 步数，无副作用）
 --steps 6000 · --ckpt-every 100 --ckpt-keep 2（**断点续跑**）· 13 个优化算子**全开**
 --overlap-nm 62.5（= 1Δx）

## 内存让路（用户授权）
起前余 11847 MB；脚本内建：若余量 < 6000 MB ⇒ 先停 `t5AM_ell`/`t5AM_combo`（**其结论已出**）。
实测起后 13376 用 / **10535 余** ⇒ 未触发让路。

## 实测确认（横幅逐字）
 tag=t5N276 N=80 ⇒ 盒 5.00 µm ✓ · nv=276 B=3 steps=6000 ✓ · 物理基线 abA（导出 n=23）✓ ·
 优化算子 13 项 ✓ · 断点续跑 ckpt-every 100/keep 2 ✓ · **无 ❌ / Traceback** ✓
 进程 pid=35373 存活；ckpt 已落 1 个。

## 监控
 `_t5_armon.py` 的 TAGS 已加入 `t5N276` ⇒ 每 5 分钟自动测它的长宽比/长厚比（用户要观察"长宽比正常"）。

## 前情：本条之前的清理（同批提交）
* **停了 4 条已定论的臂**（`t5AB_B`/`t5AB_C`/`t5AB_D`/`t5AD_500`）⇒ 引擎 10 → 6，**释放 4.5 GB**；
* ⚠ **第一轮停止失败**（我按 `grep dry_<tag>` 匹配进程，而**引擎命令行里是 `--tag <tag>`**）⇒
  改用 `/proc/<pid>/cmdline` 取 pid→tag 映射表，第二轮成功；
* **数据一概未动**（不删、不 mv）；**按精确 pid**（不用 pkill -f，AGENTS.md §3.10）。
MSGEOF
git log --oneline -1
