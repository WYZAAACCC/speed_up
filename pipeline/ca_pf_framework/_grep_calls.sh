#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
mkdir -p _audit_logs/baseline
cp _audit_logs/*.log _audit_logs/baseline/ 2>/dev/null
cp meltpool_growth_gid.npz _audit_logs/baseline/meltpool_gid_decentered_baseline.npz
echo "基线已存:"; ls -la _audit_logs/baseline/
echo; echo "=== 调用点统计（capture= / thermal_capture / spontaneous / allow_spont / seed_solid / scheil_chemistry / L 属性）"
for pat in "capture=" "thermal_capture" "spontaneous" "allow_spont" "seed_solid_from_substrate" "scheil_chemistry" "\.L\b" "active_box"; do
  echo "--- $pat"
  grep -rn --include=*.py "$pat" . | grep -v "^./_" | head -12
done