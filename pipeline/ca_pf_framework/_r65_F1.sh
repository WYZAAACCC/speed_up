#!/bin/bash
# F-1（§57 预登记）：在**已有臂**上离线量 `f_flat` 的衰减曲线，分辨侵蚀来源。
#   · `--adv` 三档（adv_proj2 / adv_upwind / adv_central）⇒ 分辨"平流扩散"
#   · `--band-cells` 四档（bc5/bc10/bc20/bc40）⇒ 分辨"速度延拓"
#   **不跑新仿真**（数据都在 F 盘）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for t in adv_proj2 adv_upwind adv_central bc5 bc10 bc20; do
  d="_exp/_bk_mb/dry_$t"
  [ -d "$d" ] || { echo "### $t 无目录"; continue; }
  echo "########## $t"
  timeout 900 $PY _r65_corner.py "$d" 2>&1 \
    | grep -E '^\s+(0|20|40|60|80|100|200|300|400)\s' | head -10
  echo
done
