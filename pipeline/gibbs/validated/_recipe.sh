#!/bin/bash
F=/root/moose/modules/combined/examples/mortar/mortar_gradient.i
wc -l "$F"
echo "=== [Mesh] ==="
awk '/^\[Mesh\]/{f=1} f{print} /^\[\]/{if(f){exit}}' "$F"
echo "=== [Variables] ==="
awk '/^\[Variables\]/{f=1} f{print} /^\[\]/{if(f){exit}}' "$F"
echo "=== 全局结构（一级块 + 类型）==="
grep -nE '^\[[A-Za-z]+\]|^  \[[A-Za-z_]+\]|^    type = ' "$F" | head -60