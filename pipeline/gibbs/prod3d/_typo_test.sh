#!/bin/bash
# 判决性测试：把约束的 type 改成不存在的名字。
#   若 MOOSE 报 "unknown object" => 这个块**确实被处理**（问题在约束内部/装配）
#   若 MOOSE 不报（照常跑）      => 这个块**被静默忽略**（问题在输入接线）
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R=/root/work/typ
rm -rf "$R"; mkdir -p "$R"; cd "$R" || exit 1
SRC=/mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq.i
sed 's/\r$//' "$SRC" > case.i
cp -f /mnt/f/speed_up/pipeline/columnar_seeds.csv .
sed -i 's/type = GBFluxExchange/type = GBFluxExchangeZZZ/' case.i
grep -n 'GBFluxExchangeZZZ' case.i | head -3
timeout 300 /root/projects/gibbs/gibbs-opt -i case.i > run.log 2>&1
echo "rc=$?"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -m1 -A4 '\*\*\* ERROR' | head -6
echo "--- 是否走到了求解 ---"
grep -c 'Time Step 1' run.log
