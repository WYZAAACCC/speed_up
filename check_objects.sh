#!/bin/bash
# 核对 phase0a.i 里用到的 MOOSE 对象是否存在于源码中，并定位所属模块

cd /root/moose || exit 1

echo "对象名                                定位"
echo "-----------------------------------------------------------------------"
for obj in RandomIC MatDiffusion GenericConstantMaterial \
           ElementIntegralVariablePostprocessor FeatureFloodCount \
           GrainBoundaryArea TimestepSize BndsCalcAux FeatureFloodCountAux \
           PolycrystalVoronoi PolycrystalColoringIC GBEvolution ACGBPoly; do
    hit=$(find ./framework ./modules -name "${obj}.C" 2>/dev/null | head -1)
    if [ -n "$hit" ]; then
        printf "  %-34s %s\n" "$obj" "$hit"
    else
        printf "  %-34s ！！未找到\n" "$obj"
    fi
done

echo
echo "=== 编译进度 ==="
echo -n "  目标文件数: "; find /root/moose -name '*.o' 2>/dev/null | wc -l
echo -n "  日志大小  : "; stat -c %s /root/build_phase_field.log 2>/dev/null
echo -n "  错误行数  : "; grep -icE 'error:|Error [0-9]' /root/build_phase_field.log 2>/dev/null
