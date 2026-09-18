#!/bin/bash
# 展示 AntitrappingCurrent 的实际用法（C4 需要）。
# 【坑】内联命令里 F=$(...) 会被 Git Bash->WSL 吞掉，必须写脚本。
echo "############ echebarria_iso.i（Karma-Plapp 经典基准）############"
grep -B6 -A12 'AntitrappingCurrent' /root/moose/modules/phase_field/examples/anisotropic_interfaces/echebarria_iso.i | head -40
echo
echo "############ 它的 f_name 对应的材料 ############"
grep -B3 -A12 "property_name = .*[Ss]uscept\|susceptibility" /root/moose/modules/phase_field/examples/anisotropic_interfaces/echebarria_iso.i | head -30
echo
echo "############ GrandPotentialAnisotropyAntitrap.i ############"
grep -B6 -A12 'AntitrappingCurrent' /root/moose/modules/phase_field/test/tests/GrandPotentialPFM/GrandPotentialAnisotropyAntitrap.i | head -40
