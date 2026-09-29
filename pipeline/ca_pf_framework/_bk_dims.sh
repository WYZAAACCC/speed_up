#!/usr/bin/env bash
# _bk_dims.sh —— 打印各臂末行的 n/w/a 与 Vt（用于追"体积差在哪"）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo "臂            step     n_lath   w_lath   a_lath   Vt(um3)"
for D in _exp/_bk_gs/dry_pa _exp/_bk_gs/dry_gs2 _exp/_bk_gs/dry_gs4 \
         _exp/_bk_gs/dry_gs5 _exp/_bk_gs/dry_gs6; do
  [ -f "$D/series.csv" ] || continue
  "$PY" - "$D" <<'PY'
import csv, sys
p = sys.argv[1] + '/series.csv'
rows = list(csv.DictReader(open(p)))
r = rows[-1]
print('%-13s %5s %8.0f %8.0f %8.0f %9.4f'
      % (p.split('/')[-2], r['step'], float(r['n_lath'])*1e9,
         float(r['w_lath'])*1e9, float(r['a_lath'])*1e9,
         float(r['Vt'])*1e18))
PY
done
