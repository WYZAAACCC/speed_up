#!/bin/bash
# _r378_goodset_probe.sh —— ★★★ 按项目**自己的判据**播种一个"能自协调"的变体集，先探针过闸门。
#
# ## 判据文档原话（`BLOCK_SELFAC.md` §3.2 的 §94 硬结论）
#   「两个块（两个变体）不可能自协调 —— 最好的 2-变体组合也只把形状应变降到 52.2%。
#     ⇒ 测自协调的盒子**必须 ≥6 个变体，且必须"每对一个"（如 `1,3,5,7,9,11`）。」
#   六对 = (1,2)(3,4)(5,6)(7,8)(9,10)(11,12)。
#
# ## 而实际跑的臂用的是
#   `saSet2` 等：`1,1,2,2,3,3,4,4,7,7,8,8` ⇒ 变体集 {1,2,3,4,7,8}
#   = **(1,2)(3,4)(7,8) 三对各取两个，(5,6)(9,10)(11,12) 三对一个不取**
#   ⇒ 我 `_r377` 实测其 `r_min` = **0.4816**（文档对 `{1..6}` 记的是 0.4828，同型）
#   ⇒ **结构上不可能自协调。**
#
# ## 本探针
#   播 `1,1,3,3,5,5,7,7,9,9,11,11`（每对一个）⇒ 判据下 `r_min ≈ 0.001`。
#   先按硬规则 ㊴ 打闸门（`nf2(t=0)=0` 且 `cov_norm >= 0.95`），过了才值得开长跑。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r378_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r378_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

run() {
  local LAT="$1" TAG="$2"
  local CMD
  CMD=$(printf '%s' "$BASE" | sed "s/--laths [0-9,]*/--laths ${LAT}/")
  CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag ${TAG}/")
  CMD=$(printf '%s' "$CMD" | sed 's/--steps [0-9]*/--steps 1/')
  CMD=$(printf '%s' "$CMD" | sed 's/--every [0-9]*/--every 1/')
  rm -rf "_exp/_bk_mb/dry_${TAG}"
  echo "  --- 探针 $TAG : ${LAT} ---"
  eval "$CMD" > "_w2_r378_${TAG}.log" 2>&1 &
  echo "      PID=$! $(date '+%T')"
}

echo "=== 自协调变体集探针 $(date '+%F %T') ==="
run "1,1,3,3,5,5,7,7,9,9,11,11" goodA
wait
echo "=== 结束 $(date '+%T') ==="
for t in goodA; do
  f="_w2_r378_${t}.log"
  printf '  %-8s Traceback=%s\n' "$t" "$(grep -c Traceback "$f" || true)"
  grep -oE '两块异变体接触面 = \*\*[0-9]+\*\* 个格面' "$f" | head -1
  grep -oE 'cov_norm` = [0-9.]+.*(✅|❌)' "$f" | head -1
  grep -oE '播种 [0-9]+ 片.*' "$f" | head -1
done
