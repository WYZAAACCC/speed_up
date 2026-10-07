#!/bin/bash
# _r371_probe2.sh —— ★ 扩大**合格构型池**（`§169.4` 的功效瓶颈）。
#
# ## 为什么
# `§173`/`§176` 的所有统计检验都**受块数限制**，而且"同变体池、不同指派"的复现
# 目前只有 **2 个**指派（base 0.966、permB1 0.961）。
# ⇒ 只有 ≥3–4 个合格指派，才能把"单次对比"变成**分布**。
#
# ## 做法（硬规则 ㊴：先探针，闸门是 t=0 可测量）
# 用 `--steps 1` 逐臂打 `nf2(t=0)` 与 `cov_norm`，**不过闸门的不开长跑**。
# 本批 4 个新指派（都是变体池 {1,2,3,4,7,8} 的排列）：
#   permB4 (V3,V1,V8,V2,V7,V4)   permB5 (V4,V7,V1,V3,V8,V2)
#   permB6 (V8,V2,V4,V7,V1,V3)   permB7 (V2,V8,V3,V7,V4,V1)
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r371_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r371_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

run() {
  local LAT="$1" TAG="$2"
  local CMD
  CMD=$(printf '%s' "$BASE" | sed "s/--laths [0-9,]*/--laths ${LAT}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}/")
  CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 1/')
  CMD=$(printf '%s' "$CMD" | sed 's/--every [0-9]*/--every 1/')
  rm -rf "_exp/_bk_mb/dry_${TAG}"
  printf '%s' "$CMD" | grep -q -- "--laths ${LAT}" || echo "   ❌ $TAG laths 没替换"
  printf '%s' "$CMD" | grep -q -- '--steps 1' || echo "   ❌ $TAG steps 没替换"
  echo "  --- 探针 $TAG : ${LAT} ---"
  eval "$CMD" > "_w2_r371_${TAG}.log" 2>&1 &
  echo "      PID=$! $(date '+%T')"
}

echo "=== 合格构型池扩充 · 探针 $(date '+%F %T') ==="
run "3,3,1,1,8,8,2,2,7,7,4,4" permB4
run "4,4,7,7,1,1,3,3,8,8,2,2" permB5
run "8,8,2,2,4,4,7,7,1,1,3,3" permB6
run "2,2,8,8,3,3,7,7,4,4,1,1" permB7
wait
echo "=== 探针结束 $(date '+%T') ==="
for t in permB4 permB5 permB6 permB7; do
  f="_w2_r371_${t}.log"
  printf '  %-8s Traceback=%s | ' "$t" "$(grep -c Traceback "$f" || true)"
  grep -oE 'cov_norm` = [0-9.]+.*(✅|❌)' "$f" | head -1
  grep -oE '两块异变体接触面 = \*\*[0-9]+\*\* 个格面' "$f" | head -1
done
