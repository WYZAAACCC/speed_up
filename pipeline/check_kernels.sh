#!/bin/bash
cd /root/moose/modules/phase_field || exit 1

echo "===== ACGrGrBase：驱动力来自哪个材料属性 ====="
sed -n '1,60p' src/kernels/ACGrGrBase.C
echo "--- 参数声明 ---"
grep -n 'addParam\|addRequiredParam\|getMaterialProperty\|getParam' src/kernels/ACGrGrBase.C

echo
echo "===== ACGrGrPoly：computeDFDOP 全文 ====="
grep -n 'computeDFDOP' -A25 src/kernels/ACGrGrPoly.C | head -45

echo
echo "===== ACInterface：参数与用的属性 ====="
grep -n 'addParam\|getMaterialProperty\|getParam' src/kernels/ACInterface.C | head -25

echo
echo "===== ACBulk（基类）：_L 从哪来 ====="
grep -n 'addParam\|getMaterialProperty\|_L(' src/kernels/ACBulk.C include/kernels/ACBulk.h 2>/dev/null | head -20

echo
echo "===== 有没有现成的、可温度变的材料能提供 mu/kappa_op/L ====="
echo "--- 含 property_name = mu 的示例 ---"
grep -rn "property_name = mu\|property_name = 'mu'" --include='*.i' . | head -5
echo "--- ACGrGrPoly 用到的材料属性在其它 .i 里怎么给的 ---"
grep -rln 'ACGrGrPoly' --include='*.i' . | head -5
