#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for f in _t5_aralign.py _t5_seven.py _t5_fragalign.py _t5_split3d2.py; do
  echo "===== $f ====="
  if [ -f "$f" ]; then
    grep -nE 'sys\.argv|argparse|usage|def main|^TAG|^STEPS|^DEFAULT' "$f" | head -14
  else
    echo "  (不存在)"
  fi
done
echo
echo "===== 可用的分析脚本清单 ====="
ls -1 _t5_*.py 2>/dev/null | tr '\n' ' '
