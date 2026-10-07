#!/bin/bash
# _r386_goodA400.sh —— ★★★ **主修正项**：用"能自协调"的变体集重跑条件③的对照。
#
# ## 为什么这是主修正项（`§178`）
# 所有历史臂与在跑的 4 条臂都用 `1,1,2,2,3,3,4,4,7,7,8,8`（变体集 `{1,2,3,4,7,8}`），
# 而该集合的 `r_selfac` **可动下界是 0.4816**（924 个六元组里排 913 名）
# ⇒ **结构上不可能自协调**。
# 项目自己的判据（`BLOCK_SELFAC.md` §3.2/§94）要求"**每对一个**"（如 `1,3,5,7,9,11`），
# 其 `r_min ≈ 0.001`。
#
# ## 闸门（硬规则 ㊴，**已过**，`_r378` 探针）
#   `nf2(t=0)` = **0** ✅ ；`cov_norm` = **0.999** ✅（比用过的任何集合都好）
#
# ## 设计
# 与 `saSet2` 逐字相同（`_r178_repro.py --emit` 重建），**只改 `--laths`/`--tag`/`--steps 400`**，
# 并追加 `--diag-terms`（拿 `vv.n` 与 `vb.med_ed`，供 `§174` 的离线 `ed` 重建做同臂对照）。
#
# ## 判据（**先写死**）
# * **G-1** 跑完 400 步、`Traceback=0`、闸门复验（`nf2(t=0)=0` 且 `cov_norm ≥ 0.95`）。
# * **G-2 ★** `r_selfac` 末值 vs 同集合的 `r_min`（≈0.001）比：
#   **若显著降到 ≲0.1 ⇒ 换集合就够，"缺一个力"的说法作废**；
#   **若仍停在 ~0.5 ⇒ 集合不是唯一原因，动力学/参数要另查。**
# * **G-3** `§173` 在新集合上重做（该集合内部对比度大得多：R 范围 0→0.0045）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r386_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r386_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

CMD=$(printf '%s' "$BASE" | sed 's/--laths [0-9,]*/--laths 1,1,3,3,5,5,7,7,9,9,11,11/')
CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag goodA_400/")
CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 400/')
case "$CMD" in *"--diag-terms"*) ;; *) CMD="$CMD --diag-terms" ;; esac

printf '%s' "$CMD" | grep -q -- '--laths 1,1,3,3,5,5,7,7,9,9,11,11' || echo "  ❌ laths 没替换"
printf '%s' "$CMD" | grep -q -- '--steps 400' || echo "  ❌ steps 没替换"
printf '%s' "$CMD" | grep -q -- '--tag goodA_400' || echo "  ❌ tag 没替换"
echo "--- 最终命令行（token $(printf '%s' "$CMD" | wc -w)）---"
printf '   %s\n' "$CMD"

rm -rf _exp/_bk_mb/dry_goodA_400
echo "=== goodA 400 步开始 $(date '+%F %T') ==="
eval "$CMD" > _w2_r386_run.log 2>&1
echo "=== 退出码 $? $(date '+%F %T') ==="
echo "Traceback 数: $(grep -c Traceback _w2_r386_run.log || true)"
grep -E 'cov_norm|两块异变体接触面' _w2_r386_run.log | head -3
grep -oE '^  \[ *[0-9]*\].*' _w2_r386_run.log | tail -2
