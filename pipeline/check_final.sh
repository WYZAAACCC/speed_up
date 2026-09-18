#!/bin/bash
cd /root/moose || exit 1

echo "===== 1. mu 的定义（核对 ACGBPoly 的因子 2 问题）====="
sed -n '80,140p' modules/phase_field/src/materials/GBEvolutionBase.C

echo
echo "===== 2. 官方有没有用过 GrainGrowthAction 的 c 参数 ====="
grep -rln 'c = \|c=' modules/phase_field/test/tests/grain_growth* modules/phase_field/examples/grain_growth 2>/dev/null | head
echo "--- 全库搜 'ACGBPoly' ---"
grep -rln 'ACGBPoly' modules/ --include='*.i' 2>/dev/null | head

echo
echo "===== 3. heat_conduction / 热源能力 ====="
ls modules/ | head -40
echo "--- heat source kernels ---"
ls modules/heat_transfer/src/kernels/ 2>/dev/null | head -20

echo
echo "===== 4. 3D_6000_gr.i 规模 ====="
grep -n 'nx\|ny\|nz\|grain_num\|op_num\|end_time\|uniform_refine' modules/phase_field/examples/grain_growth/3D_6000_gr.i | head -15

echo
echo "===== 5. GrandPotentialSolidification.i 的方程部分 ====="
sed -n '60,160p' modules/phase_field/examples/anisotropic_interfaces/GrandPotentialSolidification.i
