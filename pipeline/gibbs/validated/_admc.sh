#!/bin/bash
echo "=== ADMortarConstraint.h 全文（去掉许可证头） ==="
grep -vE "^//\*|^ \* " /root/moose/framework/include/constraints/ADMortarConstraint.h