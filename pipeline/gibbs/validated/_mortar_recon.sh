#!/bin/bash
F=/root/moose/modules/combined/examples/mortar/mortar_gradient.i
echo "=== [Variables] ==="
awk '/^\[Variables\]/{f=1} f{print} /^\[\]/{if(f){exit}}' "$F"
echo "=== [MortarConstraints]/[Constraints]/[InterfaceKernels] ==="
for blk in MortarConstraints Constraints InterfaceKernels Kernels; do
  if grep -q "^\[$blk\]" "$F"; then echo "--- [$blk] ---"; awk -v b="[$blk]" 'index($0,b)==1{f=1} f{print} /^\[\]/{if(f){exit}}' "$F"; fi
done
echo
echo "=== LowerDIntegratedBC 的说明 ==="
sed -n '1,40p' /root/moose/framework/include/bcs/LowerDIntegratedBC.h 2>/dev/null | grep -vE "^//\*|^ \* (This file|https|All rights|Licensed|you may|the terms|See the|https)" | head -25
echo
echo "=== MortarConstraint 的现成子类 ==="
grep -rho "registerMooseObject(\"[A-Za-z]*\", [A-Za-z]*)" /root/moose/framework/src/constraints/*.C 2>/dev/null | sed "s/.*, //;s/)//" | sort -u | head -20