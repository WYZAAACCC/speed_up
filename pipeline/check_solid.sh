#!/bin/bash
# 核查 LPBF 凝固建模在 MOOSE 里的可行性

cd /root/moose || exit 1

echo "===== 1. GBEvolutionBase：T 是参数还是变量？ ====="
sed -n '1,80p' modules/phase_field/src/materials/GBEvolutionBase.C
echo "--- 参数声明 ---"
grep -n 'addParam\|addRequiredParam\|addCoupledVar' modules/phase_field/src/materials/GBEvolutionBase.C

echo
echo "===== 2. 有没有「多晶粒 + 液相」的相场示例 ====="
echo "--- 同时含 GrainTracker 和 liquid/melt 的输入文件 ---"
for f in $(grep -rl 'GrainTracker' modules --include='*.i' 2>/dev/null); do
    if grep -qi 'liquid\|melt\|solidif' "$f"; then echo "  $f"; fi
done
echo "--- 含 melting kernel 的源码 ---"
ls modules/phase_field/src/kernels/ | grep -i 'melt\|solid\|liquid\|kobayashi'

echo
echo "===== 3. GrandPotentialSolidification.i 的结构 ====="
sed -n '1,60p' modules/phase_field/examples/anisotropic_interfaces/GrandPotentialSolidification.i

echo
echo "===== 4. 有没有温度耦合的晶界迁移率（Arrhenius）====="
grep -rn 'Q\b' modules/phase_field/src/materials/GBEvolutionBase.C | head -10
echo "--- 其他含温度依赖迁移率的材料 ---"
grep -rln 'exp(-.*Q.*kb\|_Q\b' modules/phase_field/src/materials/ | head -10

echo
echo "===== 5. 潜热 / 热源能力 ====="
ls modules/heat_transfer/src/kernels/ 2>/dev/null | head -20
echo "--- heat_conduction 模块是否编译 ---"
ls modules/heat_conduction/ 2>/dev/null | head

echo
echo "===== 6. 3D_6000_gr.i 的规模参数 ====="
grep -n 'nx\|ny\|nz\|grain_num\|op_num\|end_time' modules/phase_field/examples/grain_growth/3D_6000_gr.i | head -20
