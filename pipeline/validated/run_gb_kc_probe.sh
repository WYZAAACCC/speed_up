#!/bin/bash
# 决定性验证：dc 是否 kappa_c 主导？
#   机制：CH 的梯度项把偏析阱抹平，长度尺度 w_c = sqrt(kappa_c/(k_c+2A))。
#   生产里 wGB=4um 而 w_c=83.7nm  => w_c << wGB，灶能起作用。
#   子模型里 wGB=2nm 而 w_c 还是 83.7nm => w_c >> wGB，灶被抹平。
#   预测：dc ∝ 1/sqrt(kappa_c)，直到 w_c ~ wGB 后饱和到 |Om0|/(wgb*(k_c+2A)) = 1.75e-2
set +u
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$HERE/make_1d_gb.py" ] || HERE="/mnt/f/speed_up/pipeline/validated"
ROOT="${ROOT:-/root/work/gb_kcprobe}"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
rm -rf "$ROOT"; mkdir -p "$ROOT"

python3 - "$ROOT" <<'PY'
import math
print("  w_c = sqrt(kappa_c/(k_c+2A)) 的对照表（wGB = 2 nm）：")
for kc in (1e-14,1e-16,1e-17,1e-18,1e-19,1e-20,1e-21,1e-22):
    wc = math.sqrt(kc/1.428)
    print("    kappa_c=%-9.0e  w_c=%10.3f nm   w_c/wGB=%9.1f" % (kc, wc*1e9, wc/2e-9))
print("  自相似要求 w_c/wGB 与生产相同（47.8） => kappa_c = 1e-14*(2/4000)^2 = %.2e" % (1e-14*(2e-9/4e-6)**2))
print()
PY

for kc in 1e-14 1e-16 1e-17 1e-18 1e-19 1e-20 1e-21 1e-22; do
  D="$ROOT/kc_$kc"; mkdir -p "$D"
  python3 "$HERE/make_1d_gb.py" --out "$D/gb.i" \
     --dx 0.25e-9 --wgb 2e-9 --ldom 100e-9 --t-end 2.0e-4 \
     --f-part h_solid --f-seg -5e-11 --kc "$kc" \
     --dl 2.52e-9 --ds 4e-13 --dgb 4e-10 > "$D/gen.log" 2>&1 || { echo "kc=$kc 生成失败"; continue; }
  ( cd "$D" && "$MOOSE" -i gb.i > run.log 2>&1 )
  rc=$?
  if [ $rc -ne 0 ]; then echo "  kappa_c=$kc  运行失败 rc=$rc"; continue; fi
  python3 - "$D/gb_out.csv" "$kc" <<'PY'
import csv, math, sys
f, kc = sys.argv[1], float(sys.argv[2])
r = list(csv.DictReader(open(f)))
last = r[-1]
cmax, cmin, cedge = float(last["c_max"]), float(last["c_min"]), float(last["c_edge"])
cs = 0.02268908
wc = math.sqrt(kc/1.428)
naive = 5e-11/(2e-9*1.428)
deq = cmax - cs
print("  kappa_c=%-9.0e w_c=%8.2f nm  w_c/wGB=%8.1f  步=%-4d  dc=%.4e   dc/naive=%.3e   s=%.5f"
      % (kc, wc*1e9, wc/2e-9, len(r), deq, deq/naive, cmax/cs))
PY
done