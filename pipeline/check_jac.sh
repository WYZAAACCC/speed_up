#!/bin/bash
D=/root/work/s1d_jac
echo "现在 $(date '+%H:%M:%S')"
for t in no2b D2b; do
  L="$D/$t.log"
  echo "=== $t ==="
  if [ ! -f "$L" ]; then echo "  未开始"; continue; fi
  grep -a "Finished Setting Up" "$L" | sed 's/^/  /'
  printf "  收敛步: "; grep -ac "Solve Converged" "$L"
  echo "  雅可比自检:"
  grep -a "J - Jfd" "$L" | head -3 | sed 's/^/    /'
  grep -a -m2 -E '\*\*\* ERROR|NANORINF' "$L" | sed 's/^/    /'
done
echo
echo "=== 进程 ==="
pgrep -a phase_field-opt | head -2 || echo "  无 MOOSE 进程"
