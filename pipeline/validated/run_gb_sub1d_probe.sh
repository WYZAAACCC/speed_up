#!/bin/bash
# 探针：dc 到底随 Omega0 线性吗？还是被时间/输运限制？
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/make_1d_gb.py" ] || HERE="/mnt/f/speed_up/pipeline/validated"
ROOT="${ROOT:-/root/work/gb_probe}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
rm -rf "$ROOT"; mkdir -p "$ROOT"

probe () {  # tag omega0 t_end
  tag=$1; om=$2; te=$3
  D="$ROOT/$tag"; mkdir -p "$D"
  python3 "$HERE/make_1d_gb.py" --out "$D/gb.i" \
     --dx 0.25e-9 --wgb 2e-9 --ldom 100e-9 --t-end "$te" \
     --f-part h_solid --f-seg "$om" --kc 1e-14 \
     --dl 2.52e-9 --ds 4e-13 --dgb 4e-10 > "$D/gen.log" 2>&1 || { echo "$tag 生成失败"; return; }
  ( cd "$D" && "$MOOSE" -i gb.i > run.log 2>&1 ) || { echo "$tag 运行失败"; return; }
  python3 - "$D/gb_out.csv" "$tag" "$om" "$te" <<'PY'
import csv, sys
f, tag, om, te = sys.argv[1:5]
r = list(csv.DictReader(open(f)))
last, prev = r[-1], r[-2] if len(r) > 1 else r[-1]
cmax, cmin, cedge = float(last["c_max"]), float(last["c_min"]), float(last["c_edge"])
gg = float(last["gamma_gb"])
den = 1.428
pred = abs(float(om)) / (2e-9 * den)
print("  %-22s Om=%-9s t_end=%-9s 步=%-4d c_max=%.8f c_min=%.8f c_edge=%.8f dc=%.3e  预期dc=%.3e  比值=%.1f  gamma=%.3e"
      % (tag, om, te, len(r), cmax, cmin, cedge, cmax-cmin, pred, (cmax-cmin)/pred, gg))
PY
}

echo "=== A: 扫 Omega0（t_end 固定 2e-6）—— 判据：dc 应正比于 Omega0 ==="
probe om1e-11 -1e-11 2.0e-6
probe om5e-11 -5e-11 2.0e-6
probe om5e-10 -5e-10 2.0e-6
probe om5e-9  -5e-9  2.0e-6
echo
echo "=== B: 扫 t_end（Omega0 固定 -5e-11）—— 判据：dc 应收敛到平衡 ==="
probe t2e-6  -5e-11 2.0e-6
probe t2e-5  -5e-11 2.0e-5
probe t2e-4  -5e-11 2.0e-4
probe t2e-3  -5e-11 2.0e-3