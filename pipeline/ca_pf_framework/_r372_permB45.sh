#!/bin/bash
# _r372_permB45.sh —— ★★ 把"2 个指派的一次对比"升级成**4 个指派的分布**。
#
# ## 合格池（全部已过 `_r360`/`_r371` 探针闸门：`nf2(t=0)=0` 且 `cov_norm >= 0.95`）
# | 指派 | 块序列 | cov_norm |
# |---|---|---|
# | permB0 (= `saSet2` 基准) | V1,V2,V3,V4,V7,V8 | 0.966 |
# | permB1 | V1,V4,V2,V8,V3,V7 | 0.961 |
# | **permB4** | **V3,V1,V8,V2,V7,V4** | **1.035** |
# | **permB5** | **V4,V7,V1,V3,V8,V2** | **1.022** |
# （permB2 0.944 / permB3 0.892 / permB6 0.898 / permB7 0.938 **不过** ⇒ 不开长跑。）
#
# ## 要什么
# `§173` 的判据是"F2 接触是否偏好 rank-1 相容对"，报的是一个**百分位**。
# 一个指派给一个百分位 ⇒ 3 个新指派把 n=2 变成 **n=4 的分布**，
# 才能问"这个百分位是否**系统性地**偏离 0.5"，而不是"两个数像不像"。
#
# ## 设计（单变量：只改"变体→块"的指派；步数与基准同为 200）
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r372_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r372_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

run() {
  local LAT="$1" TAG="$2"
  local CMD
  CMD=$(printf '%s' "$BASE" | sed "s/--laths [0-9,]*/--laths ${LAT}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}/")
  CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 200/')
  rm -rf "_exp/_bk_mb/dry_${TAG}"
  printf '%s' "$CMD" | grep -q -- "--laths ${LAT}" || echo "   ❌ $TAG laths 没替换"
  printf '%s' "$CMD" | grep -q -- '--steps 200' || echo "   ❌ $TAG steps 没替换"
  printf '%s' "$CMD" | grep -q -- "--tag ${TAG}" || echo "   ❌ $TAG tag 没替换"
  echo "  --- $TAG : ${LAT} ---"
  eval "$CMD" > "_w2_r372_${TAG}.log" 2>&1 &
  echo "      PID=$! $(date '+%T')"
}

echo "=== 4 指派分布 · 两个新臂 开始 $(date '+%F %T') ==="
run "3,3,1,1,8,8,2,2,7,7,4,4" permB4_200
run "4,4,7,7,1,1,3,3,8,8,2,2" permB5_200
wait
echo "=== 结束 $(date '+%F %T') ==="
for t in permB4_200 permB5_200; do
  f="_w2_r372_${t}.log"
  printf '  %-12s Traceback=%s 末步=%s\n' "$t" "$(grep -c Traceback "$f" || true)" \
    "$(grep -o '^  \[ *[0-9]*\]' "$f" | tail -1 | tr -d ' []')"
  grep -oE 'cov_norm` = [0-9.]+.*(✅|❌)' "$f" | head -1
done
