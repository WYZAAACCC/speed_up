#!/bin/bash
# 把两个引擎版本的**完整 diff** 存成证据文件（溯源审计的一部分）
cd /mnt/f/speed_up || exit 1
OUT=pipeline/ca_pf_framework/R1_ENGINE_DIFF_a3e3557_to_89ec9471.diff
{
  echo "# 引擎 diff 证据：lath1/mid1 用的 a3e3557  ->  当前 89ec9471"
  echo "# 生成于 $(date +%Y-%m-%dT%H:%M:%S)"
  echo "# 用途：判定"跨 SHA 组的算例能不能并列比""
  echo "# 命令：git diff c2913a24 9d31b4fa -- pipeline/ca_pf_framework/windowB_surface.py"
  echo
  git diff c2913a24 9d31b4fa -- pipeline/ca_pf_framework/windowB_surface.py
  echo
  echo "# ===== 结论（逐行判定）====="
  echo "# 1) "有配对被处理"的路径：同一个 argsort -> 同一个 _karr/_larr -> 同一个 corr2"
  echo "#    -> 同一个 delta -> 同一个 self.phi + delta  => 数值上完全同一（无算式改动）"
  echo "# 2) "全跳过"路径：原来做 self.phi = self.phi + delta（delta 恒 0），现在直接 return。"
  echo "#    对有限值 x + 0.0 == x 逐位成立；唯一差别是 -0.0 + 0.0 = +0.0（零的符号）。"
  echo "#    而本引擎里 phi 只经 S = phi0/sqrt(phi0^2+dx^2) 使用，没有对 phi 取倒数"
  echo "#    => 零的符号不可观测。"
  echo "# => 两个引擎数值等价；跨 SHA 的并列**可以保留**（历史上限：lath1/mid1 仅用于 m=0 基线）。"
} > "$OUT"
wc -l "$OUT"
echo "已写 $OUT"
