#!/bin/bash
# _r579_npgrad.sh --- 打印 numpy `_gradient` 的**内层函数体**（复刻边界公式必须照抄源码）。
set -u
F=/root/miniconda3/envs/ml/lib/python3.12/site-packages/numpy/lib/_function_base_impl.py
echo "--- 所有 _gradient 定义行 ---"
grep -n "_gradient" "$F" | grep -E "def |edge_order == 1|central diff" | head
echo
echo "--- 内层函数体（从 def 到 outvals.append）---"
S=$(grep -n "^    def _gradient" "$F" | head -1 | cut -d: -f1)
echo "start=$S"
if [ -n "${S:-}" ]; then sed -n "${S},$((S+100))p" "$F"; else
  # 退而求其次：打印包含 edge_order 判定的那一段
  T=$(grep -n "edge_order == 1" "$F" | head -1 | cut -d: -f1)
  echo "fallback start=$T"
  sed -n "$((T-30)),$((T+70))p" "$F"
fi
