#!/usr/bin/env bash
# _r534_check.sh —— 语法检查 + 新开关接线核对
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "=== py_compile ==="
$PY -m py_compile _bk_exp.py windowB_surface.py && echo "  OK（两个文件）" || echo "  FAIL"

echo
echo "=== 新开关接线核对（N11：--nfsv-diag）==="
for pat in "nfsv-diag" "nfsv_diag" "nfsv_diag_v" "nfsv_diag_nfields" "nfsv_diag_occ_sizes" "nfsv_diag_tot_occ"; do
  n1=$(grep -c "$pat" _bk_exp.py 2>/dev/null || echo 0)
  n2=$(grep -c "$pat" windowB_surface.py 2>/dev/null || echo 0)
  printf "  %-22s  _bk_exp.py=%s  windowB_surface.py=%s\n" "$pat" "$n1" "$n2"
done

echo
echo "=== --nuc-max-per-step 是否还在（我上一步改注释时不该动它）==="
grep -n "nuc-max-per-step" _bk_exp.py | head -3

echo
echo "=== argparse 能否正常构建（--help 不崩就是接线完整）==="
$PY _bk_exp.py --help > /dev/null 2>&1 && echo "  --help OK" || echo "  --help FAIL"
