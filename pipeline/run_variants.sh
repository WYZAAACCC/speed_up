#!/bin/bash
# 并行跑 4 个对照变体，定位残差地板来自哪个改动。
# 每个只跑 2 步（end_time=2e-6），但 setup（符号求导）仍要 ~110 s。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

SRC=/mnt/f/speed_up/pipeline
D=/root/work/s1d_var
MOOSE=/root/moose/modules/phase_field/phase_field-opt

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
for f in stage1_meltpool_d.i make_variants.py; do
  sed 's/\r$//' "$SRC/$f" > "$f"
done
cp "$SRC/columnar_seeds.csv" .
python3 make_variants.py || exit 1

echo "=== 并行启动变体 ==="
for v in v0 v2 v4; do
  mkdir -p "$v"
  cp "$v.i" columnar_seeds.csv "$v"/
  ( cd "$v" && setsid --wait "$MOOSE" -i "$v.i" > run.log 2>&1; echo "$v 结束 rc=$?" ) &
done
wait
echo "=== 全部结束 ==="
