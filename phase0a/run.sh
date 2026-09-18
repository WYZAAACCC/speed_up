#!/bin/bash
# =============================================================================
# Phase 0a 运行脚本
#
# 工作方式：
#   - 输入文件从 F:\speed_up\phase0a\ 同步到 WSL 家目录（/mnt/f 的 I/O 慢）
#   - 在 WSL 里跑仿真（快）
#   - 结果拷回 F:\speed_up\phase0a\（你在 Windows 上直接看）
#
# 用法：
#   bash run.sh              # 默认 4 个 MPI 进程
#   bash run.sh 8            # 指定进程数
#   bash run.sh 1            # 串行
# =============================================================================

set -e

NP="${1:-4}"
SRC=/mnt/f/speed_up/phase0a
RUN=$HOME/work/phase0a
BIN=$HOME/moose/modules/phase_field/phase_field-opt

# ---- 关键：必须激活 conda 环境，否则 mpirun / python3(numpy) 都找不到 ----
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

echo "=============================================="
echo " Phase 0a：晶粒消失时溶质是否守恒？"
echo "=============================================="
echo "MPI 进程数 : $NP"
echo "mpirun     : $(command -v mpirun || echo '未找到')"
echo "python3    : $(command -v python3)"
echo "numpy      : $(python3 -c 'import numpy; print(numpy.__version__)' 2>&1 | head -1)"
echo

if [ ! -x "$BIN" ]; then
    echo "错误：找不到可执行文件 $BIN"
    exit 1
fi

# ---- 同步输入文件到 WSL ----
mkdir -p "$RUN"
sed 's/\r$//' "$SRC/phase0a.i"  > "$RUN/phase0a.i"
sed 's/\r$//' "$SRC/analyze.py" > "$RUN/analyze.py"

cd "$RUN"
rm -f *.csv *.e *.png run.log analyze.log

# ---- 跑仿真 ----
echo "开始仿真..."
START=$(date +%s)

if [ "$NP" -gt 1 ]; then
    mpirun -np "$NP" "$BIN" -i phase0a.i 2>&1 | tee run.log
else
    "$BIN" -i phase0a.i 2>&1 | tee run.log
fi

END=$(date +%s)
echo
echo "仿真完成，耗时 $((END - START)) 秒"

# ---- 分析 ----
echo
echo "=============================================="
echo " 分析"
echo "=============================================="
python3 analyze.py . 2>&1 | tee analyze.log || echo "（分析失败）"

# ---- 回拷 F 盘 ----
echo
echo "回拷结果到 F 盘..."
cp -f *.csv       "$SRC/" 2>/dev/null || true
cp -f *.png       "$SRC/" 2>/dev/null || true
cp -f run.log     "$SRC/" 2>/dev/null || true
cp -f analyze.log "$SRC/" 2>/dev/null || true
mkdir -p "$SRC/exodus"
cp -f *.e "$SRC/exodus/" 2>/dev/null || true

echo "完成。结果在 $SRC"
