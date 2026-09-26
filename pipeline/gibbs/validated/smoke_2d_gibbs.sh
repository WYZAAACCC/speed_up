#!/bin/bash
# =============================================================================
# 2D Gibbs 版 smoke test（**不动生产**；缩小网格 + 短时间）
# =============================================================================
# 判据：
#   S1  --check-input 通过（所有对象/参数都认识）
#   S2  JIT 失败 = 0（conda 激活正确）
#   S3  无 "Missing coupled variables" 告警（审计 P0-1 同类；教训 3 当错误看）
#   S4  短跑能收敛，c_min > 0（log(c) 不越界）
# 用法： bash smoke_2d_gibbs.sh
# =============================================================================
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/../stage1_meltpool_gibbs.i" ] || HERE="/mnt/f/speed_up/pipeline/gibbs/validated"
INC="${INC:-$HERE/../stage1_meltpool_gibbs.i}"
ROOT="${ROOT:-/root/work/g2d}"
SAVE="${SAVE:-/mnt/f/speed_up/pipeline/gibbs/results_2d}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"

rm -rf "$ROOT"; mkdir -p "$ROOT" "$SAVE"; cd "$ROOT"
cp "$INC" gibbs2d.i

echo "=============================================================="
echo " 2D Gibbs smoke：$MOOSE"
echo "=============================================================="
echo "--- S1: --check-input（缩小网格）---"
timeout 1800 "$MOOSE" --check-input -i gibbs2d.i Mesh/gen/nx=86 Mesh/gen/ny=30 > chk.log 2>&1
echo "rc=$?"
sed "s/\x1b\[[0-9;]*m//g" chk.log | grep -cE 'Missing coupled variables' > warn.txt
sed "s/\x1b\[[0-9;]*m//g" chk.log | tail -20
echo
echo "S3 Missing-coupled 告警条数 = $(cat warn.txt)"
echo
echo "--- S2/S4: 短跑（10 步量级）---"
timeout 3600 "$MOOSE" -i gibbs2d.i Mesh/gen/nx=86 Mesh/gen/ny=30 \
    Executioner/end_time=4.0e-6 Outputs/exo/enable=false \
    Outputs/checkpoint/enable=false > run.log 2>&1
echo "rc=$?"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'JIT compile failed' > jit.txt
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -c 'Solve Did NOT Converge' > ncv.txt
echo "S2 JIT 失败 = $(cat jit.txt)"
echo "   未收敛   = $(cat ncv.txt)"
echo "--- 错误 ---"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -B1 -A5 -m2 '\*\*\* ERROR' | head -20
echo "--- CSV 末两行 ---"
tail -2 gibbs2d_out.csv 2>/dev/null
cp -f gibbs2d.i chk.log run.log gibbs2d_out.csv warn.txt jit.txt ncv.txt "$SAVE/" 2>/dev/null
echo "结果已复制到 $SAVE"