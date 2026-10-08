#!/usr/bin/env bash
# _r746_check.sh —— 查导出的包：冒烟测试结果 + 源目录未被改动。
set -uo pipefail
B=/mnt/f/speed_up/winb_core
echo "=== 包内文件数 = $(ls -1 "$B" | wc -l) ==="
echo
echo "=== 冒烟输出目录 ==="
if [ -d "$B/_smoke_out" ]; then
  find "$B/_smoke_out" -maxdepth 2 -type f -printf '  %p  (%s 字节)\n' | head -12
else
  echo "  ⛔ _smoke_out 不存在 ⇒ 冒烟脚本没跑到建目录那一步"
fi
echo
echo "=== 冒烟日志尾部 ==="
L="$B/_smoke_out/smoke.log"
if [ -f "$L" ]; then
  echo "  （行数 $(wc -l < "$L")）"
  tail -20 "$L" | cut -c1-140 | sed 's/^/  /'
else
  echo "  ⛔ 无 smoke.log"
fi
echo
echo "=== 源目录是否被改动（应无输出）==="
cd /mnt/f/speed_up && git status --porcelain -- pipeline/ca_pf_framework/windowB_surface.py pipeline/ca_pf_framework/_bk_exp.py && echo "  ✅ 未改动" || true
