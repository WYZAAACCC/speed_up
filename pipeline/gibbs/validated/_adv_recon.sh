#!/bin/bash
echo "=== 对流类核 ==="
ls /root/moose/framework/src/kernels/ | grep -iE "advect|convect" 
echo
echo "=== Advection 的参数 ==="
grep -A12 "validParams" /root/moose/framework/src/kernels/Advection.C 2>/dev/null | grep -E "addParam|addRequiredParam|addClassDescription" | head -8
echo
echo "=== MatAdvection 的参数 ==="
grep -E "addParam|addRequiredParam|getMaterialProperty|getVector" /root/moose/framework/src/kernels/MatAdvection.C 2>/dev/null | head -8
echo
echo "=== 有没有常量向量材料 ==="
ls /root/moose/framework/src/materials/ | grep -iE "vector|GenericConstant" | head -8