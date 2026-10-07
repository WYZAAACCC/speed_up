#!/bin/bash
# _r360_perm_probe.sh —— ★ 硬规则 ㊴：**跑长臂之前先跑"只建不算"的探针**，逐臂打闸门。
#
# 目的：为"变体置换"实验（把 6 个块的变体**重新指派**）筛出**过闸门**的构型。
# 闸门（`§99` 规程⑧）：**块间** `nf2(t=0)==0` **且** **块内** `cov_norm >= 0.95`。
#
# ⚠ 本次探针用 `--steps 1`（只建 + 一步），代价 ~1–2 min/臂。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r360_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r360_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

# 4 个指派（每块 2 根同变体板条；变体池相同 {1,2,3,4,7,8}）
#   base = saSet2 的原始指派 (V1,V2,V3,V4,V7,V8)
run() {   # run <laths> <tag>
  local LAT="$1" TAG="$2"
  local CMD
  CMD=$(printf '%s' "$BASE" | sed "s/--laths [0-9,]*/--laths ${LAT}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}/")
  CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 1/')
  CMD=$(printf '%s' "$CMD" | sed 's/--every [0-9]*/--every 1/')
  rm -rf "_exp/_bk_mb/dry_${TAG}"
  printf '%s' "$CMD" | grep -q -- "--laths ${LAT}" || echo "   ❌ $TAG laths 没替换上"
  printf '%s' "$CMD" | grep -q -- '--steps 1' || echo "   ❌ $TAG steps 没替换上"
  echo "  --- 探针 $TAG : ${LAT} ---"
  eval "$CMD" > "_w2_r360_${TAG}.log" 2>&1 &
  echo "      PID=$! $(date '+%T')"
}

echo "=== 变体置换实验 · 闸门探针 $(date '+%F %T') ==="
run "1,1,2,2,3,3,4,4,7,7,8,8" permB0
run "1,1,4,4,2,2,8,8,3,3,7,7" permB1
run "2,2,3,3,7,7,1,1,8,8,4,4" permB2
run "7,7,8,8,4,4,3,3,2,2,1,1" permB3
wait
echo "=== 探针结束 $(date '+%T') ==="
for t in permB0 permB1 permB2 permB3; do
  f="_w2_r360_${t}.log"
  printf '  %-8s Traceback=%s\n' "$t" "$(grep -c Traceback "$f" || true)"
  grep -E '精确判据|块内界面自检|cov_norm|播种后' "$f" | head -4
done
