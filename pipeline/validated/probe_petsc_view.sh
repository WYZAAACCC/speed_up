#!/bin/bash
# 查 PETSc 的 SNESTestJacobian 实现，搞清 -view / -display 到底吐出什么
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

PD="${PETSC_DIR:-}"
echo "PETSC_DIR=$PD"
[ -d "$PD" ] || PD=$(python3 -c "import os;print(os.environ.get('PETSC_DIR',''))" 2>/dev/null)
echo "resolved PETSC_DIR=$PD"

F=$(find "$PD" -name "snes.c" -path "*snes*" 2>/dev/null | head -1)
echo "snes.c = $F"
[ -n "$F" ] || { echo "找不到 petsc 源码"; exit 1; }

echo "=== SNESTestJacobian 相关函数 ==="
grep -n "SNESTestJacobian\|test_jacobian\|TestJacobian" "$F" | head -40

echo
echo "=== View 函数体 ==="
awk '/SNESTestJacobian_View/,/^}/' "$F" | head -60
