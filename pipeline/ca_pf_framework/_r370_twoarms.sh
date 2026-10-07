#!/bin/bash
# _r370_twoarms.sh —— ★★ 消掉 `§176.4` 的**步数混杂**：两条臂并行，各补一侧。
#
# ## 混杂是什么
# `§176.4` 的复现对比是 `saSet2`@**400** vs `permB1_200`@**200** —— 步数不同
# ⇒ 既可能是"指派不同"，也可能是"时刻不同"。**必须消掉。**
#
# ## 两条臂（**并行**，互不依赖；机器 20 核 / 21 GB 可用）
# * **A `permB1_400`**：permB1 的指派跑到 **400** 步
#   ⇒ 与 `saSet2`@400（已有 `§176.3` 的数）**同步数**对比。
#   ★ 顺带一个**免费的可重复性检验**：它与 `permB1_200` 前 200 步应当**逐位相同**
#     （同参数、同种子、确定性）⇒ 用 `_r350` 的 `coldiff` 比 series.csv。
# * **B `saSet2DT200`**：`saSet2` 的指派跑到 **200** 步 + `--diag-terms`
#   ⇒ 与 `permB1_200`@200 **同步数**对比，且**本臂有 `diag_terms.json`**
#     ⇒ `_r358` 的 Z-1 已知答案对照可做（`saSet2`@200 原本因无对照而作废）。
#
# ## 前置闸门（硬规则 ㊴）
# 两个指派都已在 `_r360` 探针里过闸门（permB1 `cov_norm`=0.961、base 0.966）✓
# ⇒ 无需再探针，跑完再核一次即可。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r370_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r370_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

launch() {   # launch <laths> <steps> <tag> <diag?>
  local LAT="$1" STEPS="$2" TAG="$3" DIAG="$4"
  local CMD
  CMD=$(printf '%s' "$BASE" | sed "s/--laths [0-9,]*/--laths ${LAT}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--steps [0-9]*/--steps ${STEPS}/")
  if [ "$DIAG" = "1" ]; then
    case "$CMD" in *"--diag-terms"*) ;; *) CMD="$CMD --diag-terms" ;; esac
  fi
  printf '%s' "$CMD" | grep -q -- "--laths ${LAT}" || echo "   ❌ $TAG laths 没替换"
  printf '%s' "$CMD" | grep -q -- "--steps ${STEPS}" || echo "   ❌ $TAG steps 没替换"
  printf '%s' "$CMD" | grep -q -- "--tag ${TAG}" || echo "   ❌ $TAG tag 没替换"
  rm -rf "_exp/_bk_mb/dry_${TAG}"
  echo "  --- $TAG : laths=${LAT} steps=${STEPS} diag=${DIAG} ---"
  eval "$CMD" > "_w2_r370_${TAG}.log" 2>&1 &
  echo "      PID=$! $(date '+%T')"
}

echo "=== 同步数复现 · 两臂并行 开始 $(date '+%F %T') ==="
launch "1,1,4,4,2,2,8,8,3,3,7,7" 400 permB1_400 0
launch "1,1,2,2,3,3,4,4,7,7,8,8" 200 saSet2DT200 1
wait
echo "=== 两臂结束 $(date '+%F %T') ==="
for t in permB1_400 saSet2DT200; do
  f="_w2_r370_${t}.log"
  printf '  %-14s Traceback=%s 末步=%s\n' "$t" "$(grep -c Traceback "$f" || true)" \
    "$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')"
  grep -E 'cov_norm' "$f" | head -1
done
