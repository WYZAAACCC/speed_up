#!/bin/bash
echo "=== EqualValueConstraint.h ==="
cat /root/moose/framework/include/constraints/EqualValueConstraint.h
echo "=== EqualValueConstraint.C ==="
cat /root/moose/framework/src/constraints/EqualValueConstraint.C
echo "=== MortarConstraintBase 的 computeQpResidual 签名 ==="
grep -n "computeQpResidual\|MortarType\|virtual void computeResidual\|precomputeQpResidual" /root/moose/framework/include/constraints/MortarConstraintBase.h | head -20
echo "=== MortarType 枚举 ==="
grep -rn "enum class MortarType" -A6 /root/moose/framework/include/utils/MortarType.h 2>/dev/null || find /root/moose -name "MortarType.h" | head -2