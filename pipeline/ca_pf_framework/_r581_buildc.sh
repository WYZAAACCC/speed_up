#!/bin/bash
# _r581_buildc.sh --- ★ 构建 `_r581_ufv` C 扩展，并把**可复现性证据**落盘。
#
# goal §(9)/(8)⑤ 的要求：**构建可复现**（编译器版本 / 命令 / 源码与 `.so` 的 SHA256）。
# 本脚本把这三样全部写进 `_r581_ufvc_build.txt`，**任何人可据此重建**。
#
# ⚠ `${PY}` 必须与跑仿真的解释器**同一个**（ABI 要对上）。
# ⚠ `-ffp-contract=off` 与 `-fno-fast-math` **不可省**：FMA 收缩会改变舍入次数
#    ⇒ `_minmod` 不再逐位（见 `_r581_ufv.c` 的记账第 4 条）。
set -eu
cd "$(dirname "$0")" || exit 1
PY="${PY:-/root/miniconda3/envs/ml/bin/python}"
SRC=_r581_ufv.c
OUT=_r581_ufv.so
REC=_r581_ufvc_build.txt

INC_NP=$("$PY" -c 'import numpy;print(numpy.get_include())')
INC_PY=$("$PY" -c 'import sysconfig;print(sysconfig.get_paths()["include"])')
GCCV=$(gcc --version | head -1)
PYV=$("$PY" -c 'import sys;print(sys.version.split()[0])')
NPV=$("$PY" -c 'import numpy;print(numpy.__version__)')

CMD=(gcc -O2 -fPIC -shared -ffp-contract=off -fno-fast-math
     -fno-unsafe-math-optimizations
     -I"$INC_NP" -I"$INC_PY" "$SRC" -o "$OUT" -lm)

echo "=== 构建 $OUT @ $(date '+%F %T') ==="
printf '  %s\n' "${CMD[*]}"
"${CMD[@]}"

{
  echo "=============================================================="
  echo "R581-L6 C 扩展构建记录（**可复现性证据**）"
  echo "时间        : $(date '+%F %T %z')"
  echo "编译器      : $GCCV"
  echo "解释器      : $PY  (Python $PYV)"
  echo "numpy       : $NPV   include=$INC_NP"
  echo "python inc  : $INC_PY"
  echo "主机        : $(uname -srm)"
  echo "CPU         : $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ //')"
  echo "--------------------------------------------------------------"
  echo "构建命令（逐字，可重建）："
  echo "  ${CMD[*]}"
  echo "⚠ 关键选项：-ffp-contract=off（禁 FMA 收缩）、-fno-fast-math"
  echo "  ⇒ 缺任何一个都可能让 _minmod 不再逐位（见 _r581_ufv.c 记账第 4 条）"
  echo "--------------------------------------------------------------"
  echo "SHA256："
  echo "  源码 $SRC : $(sha256sum "$SRC" | cut -d' ' -f1)"
  echo "  产物 $OUT : $(sha256sum "$OUT" | cut -d' ' -f1)"
  echo "  本脚本    : $(sha256sum "$0" | cut -d' ' -f1)"
  echo "  大小      : $(stat -c%s "$OUT") B"
  echo "=============================================================="
} | tee "$REC"
echo "★ 已写 $REC"
