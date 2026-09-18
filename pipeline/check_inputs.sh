#!/bin/bash
# 对指定的输入文件逐个做语法检查
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
BIN=/root/moose/modules/phase_field/phase_field-opt
SRC=/mnt/f/speed_up/pipeline

for name in "$@"; do
    d="/root/work/chk_${name}"
    mkdir -p "$d"
    sed 's/\r$//' "$SRC/${name}.i" > "$d/in.i"
    echo "=============================================="
    echo " $name"
    echo "=============================================="
    ( cd "$d" && "$BIN" -i in.i --check-input 2>&1 | tail -4 )
    echo
done
