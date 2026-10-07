#!/bin/bash
# _r361_permB1.sh —— ★★ 独立复现臂：**同一变体池、不同"变体→块"指派**（permB1）。
#
# ## 为什么这条最值钱
# `§173`/`§174` 的核心**否定**结论（块-块接触不偏好不变平面相容对；驱动力秩 0.154 是
# `‖Δε⁰‖` 相近传播的结果）都只在**一个指派**（`saSet2` 的 V1,V2,V3,V4,V7,V8）上测过。
# ⇒ 用**另一个过闸门的指派**（`permB1` = V1,V4,V2,V8,V3,V7，`cov_norm`=0.961 ✅）
#   跑同样步数 ⇒ **真正的独立复现**（硬规则 ㉞：关键主张要 ≥2 个结构不同的配置）。
#
# ## 前置（**已过**，硬规则 ㊴）
# `_r360` 探针：4 个指派里只有 permB0(0.966) 与 permB1(0.961) 过 `cov_norm >= 0.95`；
# permB2(0.944)/permB3(0.892) **不过** ⇒ 不开长跑。
#
# ## 设计（单变量：只改"变体→块"的指派）
# 其余逐字取自 `saSet2`（`_r178_repro.py --emit`），只改 `--laths`、`--tag`、`--steps 200`，
# 并追加 `--diag-terms`（**拿到引擎自记的 `vb.med_ed`，用作离线 `ed` 重建的同臂对照**）。
#
# ## 判据（**先写死**）
# * **R-1** 过闸门（`nf2(t=0)==0` 且 `cov_norm >= 0.95`）—— 探针已验，本跑再核一次。
# * **R-2 ★** 在 step 200 上重跑 `§173`（`R` 的 720 置换百分位）与 `§174`
#   （`|Δed|` 的逐胞秩 + Z-4 鉴别）⇒ **看否定结论是否复现**。
# * **R-3** 用本臂的 `vb.med_ed` 再验一次离线 `ed` 重建（`§174.1` 的 Z-1）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r361_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r361_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

CMD=$(printf '%s' "$BASE" | sed 's/--laths [0-9,]*/--laths 1,1,4,4,2,2,8,8,3,3,7,7/')
CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag permB1_200/")
CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 200/')
case "$CMD" in *"--diag-terms"*) ;; *) CMD="$CMD --diag-terms" ;; esac

printf '%s' "$CMD" | grep -q -- '--laths 1,1,4,4,2,2,8,8,3,3,7,7' || echo "  ❌ laths 没替换"
printf '%s' "$CMD" | grep -q -- '--steps 200' || echo "  ❌ steps 没替换"
printf '%s' "$CMD" | grep -q -- '--tag permB1_200' || echo "  ❌ tag 没替换"
echo "--- 最终命令行（token $(printf '%s' "$CMD" | wc -w)）---"
printf '   %s\n' "$CMD"

rm -rf _exp/_bk_mb/dry_permB1_200
echo "=== permB1 200 步开始 $(date '+%F %T') ==="
eval "$CMD" > _w2_r361_run.log 2>&1
echo "=== 退出码 $? $(date '+%F %T') ==="
echo "Traceback 数: $(grep -c Traceback _w2_r361_run.log || true)"
grep -E 'cov_norm|两块异变体接触面' _w2_r361_run.log | head -3
tail -3 _w2_r361_run.log
