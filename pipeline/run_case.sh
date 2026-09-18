#!/bin/bash
# =============================================================================
# 通用算例运行器（阶段一及其变体）
#
# 用法:
#   bash run_case.sh <输入文件> [运行目录] [end_time] [进程数]
#   bash run_case.sh stage1_meltpool.i s1v2 8.0e-4 12
#
# 行为:
#   1. 把 F 盘上的 .i 同步到 WSL（顺便转换行尾）
#   2. 语法检查
#   3. 清理旧输出，后台跑
#
# 注意（踩过的坑）:
#   - 必须先 conda activate moose，否则 mpirun 找不到
#   - 多行/带变量的命令一律写成 .sh 再执行，
#     经 Git Bash -> wsl.exe 多层引号会吞掉 $变量
# =============================================================================

# 【注意】不要用 set -u：conda 的 activate.d 脚本里有未定义变量
# （CONDA_BUILD），开了 -u 会在 activate 时就退出。

SRC_NAME="${1:?用法: bash run_case.sh <输入文件> [运行目录] [end_time] [进程数]}"
RUN_NAME="${2:-$(basename "$SRC_NAME" .i)}"
END_TIME="${3:-}"
NP="${4:-12}"

SRC="/mnt/f/speed_up/pipeline/$SRC_NAME"
RUN="/root/work/$RUN_NAME"
BIN=/root/moose/modules/phase_field/phase_field-opt

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

mkdir -p "$RUN"
sed 's/\r$//' "$SRC" > "$RUN/in.i"
# 一并复制种子/数据文件（PolycrystalVoronoi 的 file_name 是相对运行目录的）
for f in /mnt/f/speed_up/pipeline/*.csv; do
    [ -f "$f" ] && sed 's/\r$//' "$f" > "$RUN/$(basename "$f")"
done
cd "$RUN" || exit 1

echo "=============================================="
echo " 输入 $SRC_NAME  ->  $RUN/in.i"
echo "=============================================="
"$BIN" -i in.i --check-input 2>&1 | tail -6
if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    echo "语法检查失败"
    exit 1
fi

# file_base 由输入文件决定，这里把常见的都清掉
rm -f ./*.e ./*_out.csv ./*.csv.run run.log

echo
echo " 运行: ${END_TIME:-<用输入文件里的 end_time>} / $NP 进程"
date '+  开始 %H:%M:%S'

if [ -n "$END_TIME" ]; then
    mpirun -np "$NP" "$BIN" -i in.i Executioner/end_time="$END_TIME" > run.log 2>&1
else
    mpirun -np "$NP" "$BIN" -i in.i > run.log 2>&1
fi
RC=$?

date '+  结束 %H:%M:%S'
echo "  退出码 $RC"
echo "  DIVERGED 次数: $(grep -c DIVERGED run.log 2>/dev/null)"
echo
echo "  --- 日志尾 ---"
grep -v '^$' run.log | tail -12
