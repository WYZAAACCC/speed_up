#!/bin/bash
# 一次性清理 WSL 崩溃损坏的所有 libtool 产物，然后重新编译
#
# 背景：WSL 因 OOM 崩溃时，正在写的 libtool 文件（.la 归档 / .lo 对象包装）
#       会变成 0 字节或半成品，导致后续报 "not a valid libtool archive/object"。
#       已遇到两个：contrib/hit 和 contrib/pcre。
#       不再逐个修，直接全清。
#
# 注意：只删 .la / .lo / 0 字节文件，保留正常的 .o 目标文件，
#       所以不需要完整重编，主要是重新链接。

cd /root/moose || exit 1

echo "=============================================="
echo " 1. 统计损坏产物"
echo "=============================================="
echo -n "  .la 归档总数    : "; find . -name '*.la' 2>/dev/null | wc -l
echo -n "  .lo 对象总数    : "; find . -name '*.lo' 2>/dev/null | wc -l
echo -n "  0 字节 .la      : "; find . -name '*.la' -size 0 2>/dev/null | wc -l
echo -n "  0 字节 .lo      : "; find . -name '*.lo' -size 0 2>/dev/null | wc -l
echo -n "  0 字节 .o       : "; find . -name '*.o'  -size 0 2>/dev/null | wc -l

echo
echo "=============================================="
echo " 2. 清理所有 libtool 产物 + 0 字节文件"
echo "=============================================="
find . -name '*.la' -delete 2>/dev/null
find . -name '*.lo' -delete 2>/dev/null
find . -name '*.o'  -size 0 -delete 2>/dev/null
find . -name '*.C'  -size 0 -delete 2>/dev/null
echo "  完成"

echo
echo "=============================================="
echo " 3. 重新编译（-j 8）"
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
    ls -lh /root/moose/modules/phase_field/phase_field-opt 2>/dev/null
else
    echo "错误摘要："
    grep -nE "error:|Error [0-9]|fatal error" /root/build_phase_field.log 2>/dev/null | head -20
fi
