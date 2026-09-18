#!/bin/bash
# 编译 MOOSE framework + phase_field 模块
#
# 注意：
#   - MOOSE 用 unity build，单个编译单元很吃内存（2-4 GB）
#   - 并行度太高会 OOM 把 WSL 整个搞崩，所以用 -j 8
#   - WSL 崩溃会留下 0 字节的半成品文件，必须先清掉再编

cd /root/moose || exit 1

echo "=============================================="
echo " 1. 扫描 WSL 崩溃留下的 0 字节残骸"
echo "=============================================="
BAD=$(find framework modules -name '*.o' -size 0 2>/dev/null | wc -l)
BADLO=$(find framework modules -name '*.lo' -size 0 2>/dev/null | wc -l)
echo "  0 字节 .o  : $BAD"
echo "  0 字节 .lo : $BADLO"

if [ "$BAD" -gt 0 ] || [ "$BADLO" -gt 0 ]; then
    echo "  清理中..."
    find framework modules -name '*.o'  -size 0 -delete 2>/dev/null
    find framework modules -name '*.lo' -size 0 -delete 2>/dev/null
    echo "  已清理"
else
    echo "  无残骸，干净"
fi
echo -n "  当前目标文件数: "
find framework modules -name '*.o' 2>/dev/null | wc -l

echo
echo "=============================================="
echo " 2. 编译 MOOSE + phase_field（-j 8）"
echo "=============================================="

cd /root/moose/modules/phase_field || exit 1
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

START=$(date +%s)
make -j 8 2>&1 | tee /root/build_phase_field.log
RC=${PIPESTATUS[0]}
END=$(date +%s)

echo
echo "=============================================="
echo " 编译结束，退出码 $RC，耗时 $((END - START)) 秒"
echo "=============================================="

if [ "$RC" -eq 0 ]; then
    echo "可执行文件："
    ls -lh /root/moose/modules/phase_field/phase_field-opt 2>/dev/null
else
    echo "错误摘要："
    grep -nE "error:|Error [0-9]|fatal error" /root/build_phase_field.log 2>/dev/null | head -20
fi
