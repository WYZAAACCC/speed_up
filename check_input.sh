#!/bin/bash
# 检查 phase0a.i 的语法是否正确（不实际运行）
# MOOSE 的 --check-input 会解析整个输入文件并报告未定义的对象/参数

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=$HOME/work/phase0a
SRC=/mnt/f/speed_up/phase0a

mkdir -p "$RUN"
sed 's/\r$//' "$SRC/phase0a.i" > "$RUN/phase0a.i"

cd "$RUN" || exit 1

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

echo "=============================================="
echo " 输入文件语法检查"
echo "=============================================="
"$BIN" -i phase0a.i --check-input 2>&1 | tail -40
echo
echo "退出码: ${PIPESTATUS[0]}"
