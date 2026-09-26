#!/bin/bash
echo "=== LowerDIntegratedBC 的类说明 ==="
grep -A6 'class LowerDIntegratedBC' /root/moose/framework/include/bcs/LowerDIntegratedBC.h 2>/dev/null | head -12
grep -B2 -A6 'addClassDescription' /root/moose/framework/src/bcs/LowerDIntegratedBC.C 2>/dev/null | head -12
echo
echo "=== 谁用了 LowerDIntegratedBC ==="
grep -rl "LowerDIntegratedBC" /root/moose --include=*.i 2>/dev/null | head -6
echo
echo "=== 有没有「低维块 + 通量耦合」的例子（找 lower-d 相关测试名）==="
ls /root/moose/framework/test/tests/ 2>/dev/null | grep -iE "lower|manifold" | head -8
find /root/moose -path "*test*" -name "*.i" 2>/dev/null | xargs grep -l "LowerDBlockFromSideset" 2>/dev/null | grep -viE "mortar|gap|periodic" | head -8