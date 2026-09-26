#!/bin/bash
F=/root/moose/framework/include/constraints/MortarConstraintBase.h
echo "=== MortarType 定义 ==="
grep -rn "enum class MortarType" -A8 /root/moose/framework/include/ 2>/dev/null | head -14
echo "=== MortarConstraintBase protected 成员（关键）==="
awk '/^protected:/{f=1} f{print}' "$F" | grep -vE "^\s*///|^\s*//" | grep -E "_u|_grad_u|_test|_phi|secondary|primary|_var|_dt" | head -45