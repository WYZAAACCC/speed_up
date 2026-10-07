#!/usr/bin/env bash
# R493 —— 诊断：`--nuc-fresh-every K>1` 时 `stack` 通道**为什么**一个也放不成。
#
# 背景（`R481_NUC_SITES.md §6 F1`）：`_r482` 用 `--nuc-init 2 --nuc-fresh-every 4`
# 跑两臂，**都是 0 个形核事件**。驱动侧的逻辑是
#     `_fresh_now = ((n_ath_tgt % K) == 0)`   （`_bk_exp.py:1638`）
# 而 `n_ath_tgt` **从 1 起** ⇒ K=4 时前 3 个事件必须由 **stack** 完成。
# ⇒ 若 stack 一个也放不成，`n_ath_tgt` 永远到不了 4 ⇒ `fresh` **永远不被调用**。
#
# 本脚本只**读日志**，不重跑，把两件事查清：
#   ① `_r482` 的日志里到底有没有 stack/fresh 的痕迹（驱动打没打这些计数）；
#   ② 驱动有没有把引擎的 `dbg` 计数落盘（在哪落）。
set -u
cd "$(dirname "$0")"

echo "=== 1. _r482 A 臂里所有与形核有关的行 ==="
grep -nE '形核|nfsv|fresh_blocked|attach|stack|pending' _w2_r482_r482A.log 2>/dev/null | head -20
echo "  （以上为空 ⇒ 驱动在'零事件'时**什么都不打** —— 这本身就是'静默缺口'的一部分）"

echo
echo "=== 2. 驱动里 `dbg` 计数器会不会落盘 ==="
grep -n "dbg" _bk_exp.py | grep -iE "rec|json|meta|dump|P\(" | head -10

echo
echo "=== 3. `nuc_cfg` 的 `attach` / `nfsv` 在驱动里传的是什么 ==="
grep -nE "attach=|nfsv=|attach_overlap=" _bk_exp.py | head -10

echo
echo "=== 4. 引擎里 `stack` 通道要求什么（只列关键判据行） ==="
grep -nE "n_stack|'stack'|k_new|hardened" windowB_surface.py | sed -n '1,25p'

echo
echo "=== 5. R492 进度 ==="
for T in r492on r492off; do
  N1=$(grep -c '引擎形核' "_w2_r492_${T}.log" 2>/dev/null || echo 0)
  N2=$(grep -c '\[qs\] 档' "_w2_r492_${T}.log" 2>/dev/null || echo 0)
  printf '  %-10s 形核行=%s  qs档行=%s\n' "$T" "$N1" "$N2"
done
