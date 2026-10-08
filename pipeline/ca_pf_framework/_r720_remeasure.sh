#!/usr/bin/env bash
# _r720_remeasure.sh —— 在**共同安全步**重取 `f_flat` / PCA（`R720` 的更正实验）。
#
# 背景：`_r720_touch.py` 实测本轮的臂**全都撞过盒**（CLIbig@100 / Mlo3@150 /
#   CLIell@175 / B2P_q0@225 / Mhi12@325；只有 B2P_pre 从未）
#   ⇒ "同配置矩阵 @175"混合了不同数量的撞盒后数据。
# 本脚本只做一件事：把每臂的读数**限制在各自的 `box_touch=0` 区间内**重取。
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_block

# tag:安全步（由 _r720_touch.py 给出：碰撞前最后一个安全 step）
CASES="B2P_q0:100 B2P_q0:200 B2P_pre:100 B2P_pre:400 CLIell:100 CLIbig:75 Mlo3:100 Mhi12:300"

for c in $CASES; do
  tag="${c%%:*}"; st="${c##*:}"
  [ -f "$ROOT/dry_$tag/snap_$(printf '%05d' "$st").npz" ] || { echo "【$tag @$st】⚠ 无快照"; continue; }
  echo "==================== $tag @$st ===================="
  nice -n 10 taskset -c 0-3 "$PY" _b2_meas.py "$ROOT" "$tag" "$st" 2>&1 \
    | grep -E 'f_flat（|PCA 最大|场数=' | sed 's/^/  /'
done
