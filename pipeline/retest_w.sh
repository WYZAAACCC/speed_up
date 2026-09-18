#!/bin/bash
# 用新的 align4 形式（逐晶粒对齐度的 eta^2 加权平均）重跑短算例
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

SRC=/mnt/f/speed_up/pipeline
D=/root/work/s1d_w
MOOSE=/root/moose/modules/phase_field/phase_field-opt
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

for f in gen_aniso.py splice_aniso.py stage1_meltpool_c.i; do
  sed 's/\r$//' "$SRC/$f" > "$f"
done
cp "$SRC/columnar_seeds.csv" .

echo "=== 重新生成 aniso 块并拼接 ==="
python3 gen_aniso.py --out aniso_block.i 2>&1 | tail -6
python3 splice_aniso.py
sed -i 's/^  end_time = .*/  end_time = 6e-6/' stage1_meltpool_d.i
sed -i 's/file_base = stage1d$/file_base = w/' stage1_meltpool_d.i
grep -n "end_time\|file_base" stage1_meltpool_d.i

echo
echo "=== 跑 6 步 ==="
time setsid --wait "$MOOSE" -i stage1_meltpool_d.i > run.log 2>&1
echo "退出码 $?"
grep -a "Finished Setting Up" run.log
printf "收敛步数: "; grep -ac "Solve Converged" run.log
echo
echo "非线性残差序列："
grep -a "Nonlinear |R|" run.log | head -20 | sed 's/^/  /'
echo
echo "报错："
grep -a -m3 -E '\*\*\* ERROR|NANORINF|DIVERGED|Did NOT Converge' run.log || echo "  无"
