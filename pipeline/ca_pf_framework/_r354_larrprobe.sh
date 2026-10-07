#!/bin/bash
# _r354_larrprobe.sh —— ★★ `§170` 存疑复核：让**引擎自己**吐出 `karr/larr` 的分布。
#
# 背景：`§170` 用 `vv.n ≡ 0`（400/400 步）断定"`advance` 的 `(karr,larr)` 基里
#       异变体面片恒为 0"。而 `_r353` 用归档 `band_*` 重建亚军，实测
#       **几何 F2 胞上 88.9% 的亚军是异变体邻居** ⇒ **两者矛盾**。
# ⇒ 本脚本跑一个**短臂**（同几何、同参数，只把 `--steps` 压到 6），
#   用 `--diag-terms` 把引擎的 `dbg`（`larr_where_kpos` 等）落盘，直接定案。
#
# ⚠ 只改 `--steps` 与 `--tag`；其余由 `_r178_repro.py --emit` 从归档逐参重建。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

"$PY" -u _r178_repro.py saSet2 --emit > _w2_r354_emit.log 2>&1
BASE=$(grep -m1 '^    /root/miniconda3' _w2_r354_emit.log | sed 's/^ *//')
if [ -z "$BASE" ]; then echo "❌ 没抓到重建命令"; exit 1; fi

CMD=$(printf '%s' "$BASE" | sed 's/--steps [0-9]*/--steps 6/')
CMD=$(printf '%s' "$CMD" | sed "s/--tag [^ ]*/--tag larrprobe/")
case "$CMD" in *"--diag-terms"*) ;; *) CMD="$CMD --diag-terms" ;; esac
CMD=$(printf '%s' "$CMD" | sed 's/--snap-every [0-9]*/--snap-every 2/')

printf '%s' "$CMD" | grep -q -- '--steps 6' || echo "  ❌ steps 没改成功"
printf '%s' "$CMD" | grep -q -- '--tag larrprobe' || echo "  ❌ tag 没改成功"
echo "--- 最终命令行（token $(printf '%s' "$CMD" | wc -w)）---"
printf '   %s\n' "$CMD"

rm -rf _exp/_bk_mb/dry_larrprobe
echo "=== 开始 $(date '+%F %T') ==="
eval "$CMD" > _w2_r354_run.log 2>&1
echo "=== 退出码 $? $(date '+%F %T') ==="
echo "Traceback 数: $(grep -c Traceback _w2_r354_run.log || true)"
tail -4 _w2_r354_run.log
