#!/bin/bash
# _r311_edv2.sh —— ★ **硬规则 ㉞ 追溯**：`§146`/`§148`（"`ed` 按位置组织"）只基于 **1 个构型**
# （`saSet2`）。⇒ 换一个**真正不同**的构型再测一次。
#
# ## 为什么选 `mb2fp10` 做第二构型（**与 `saSet2` 的差异**）
# | | `saSet2`（§146 用的）| **`mb2fp10`（本节）** |
# |---|---|---|
# | 板条表 | `1,1,2,2,3,3,4,4,7,7,8,8`（6 块 × 2 根）| **`1,1,1,3,3,3`（2 块 × 3 根）** |
# | 变体数 | 6（1,2,3,4,7,8）| **2（1,3）** |
# | N / Δx | 112 / 62.5 nm | **96 / 62.5 nm** |
# | 场数 | 12 | **6** |
# ⇒ **块数、每块根数、变体数、网格全不同** ⇒ 是**真正的独立构型**。
#
# ## 判据（**先写死**）
# * **E-1** 若 `mb2fp10` 上"**变体内极差 / 变体间极差**"也**≈ 1**
#   ⇒ `§146` 稳健（`ed` 按位置组织是普遍现象）。
# * **E-2** 若比值**明显 < 1** ⇒ `§146` 须收窄（在"每块根数多"的构型上，`ed` 反而按变体组织）。
#   ⚠ 本条**特别重要**：`mb2fp10` 每块 **3 根**（`saSet2` 每块 2 根）
#     ⇒ **变体内样本更多** ⇒ 是对 `§146` 结论**更严格**的检验。
# * **E-3** 只跑 **60 步**（够拿到 step 20/40/60 三个点做趋势；`ed` 每步都在算）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

rm -rf _exp/_bk_mb/dry_mb2fp10EDV
echo "=== §146 第二构型检验（mb2fp10 几何 + --diag-edv）$(date '+%F %T') ==="
"$PY" -u _r178_repro.py mb2fp10 --emit > _w2_r311_emit.log 2>&1
CMD=$(grep -m1 '^    /root/miniconda3' _w2_r311_emit.log | sed 's/^ *//')
if [ -z "$CMD" ]; then echo "❌ 没抓到重建命令"; exit 1; fi
CMD=$(printf '%s' "$CMD" | sed 's/--tag [^ ]*/--tag mb2fp10EDV/')
CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 60/')
case "$CMD" in *"--diag-edv"*) ;; *) CMD="$CMD --diag-edv" ;; esac
echo "  ⇒ 最终命令行（token $(printf '%s' "$CMD" | wc -w)）："
printf '     %s\n' "$CMD"
printf '%s' "$CMD" | grep -q -- '--tag mb2fp10EDV' || echo "     ❌ tag 不对"
printf '%s' "$CMD" | grep -q -- '--steps 60' || echo "     ❌ steps 没改成 60"
echo
echo "  --- 开跑 $(date '+%T') ---"
eval "$CMD" > _w2_r311_run.log 2>&1
echo "  --- 退出码 = $?  $(date '+%T') ---"
echo "=== 结束 $(date '+%F %T') ==="
grep -c Traceback _w2_r311_run.log || true
