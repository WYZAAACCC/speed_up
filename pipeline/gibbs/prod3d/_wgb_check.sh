#!/bin/bash
# 用项目自己的工具验证「改 wGB 不改物理」：在 mu0 = 6σ/wGB、κ = a*·wGB·σ、
# L = 4/3·M0/wGB 同步变化的前提下，数值求解 1D 平衡晶界，比对**真实晶界能 σ**。
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
R=/root/work/wgbchk
rm -rf "$R"; mkdir -p "$R"; cd "$R" || exit 1
REPO=/mnt/f/speed_up
cp -f "$REPO/pipeline/frozen/gen_aniso_nonad.py" gen_aniso.py
cp -f "$REPO/pipeline/check_wgb_invariance.py" .
cp -f "$REPO/pipeline/check_gb_energy.py" .
python3 check_wgb_invariance.py --wgb "$@" --pairs span 2>&1 | tail -40
DEST="$REPO/pipeline/gibbs/prod3d/results_wgbchk"
mkdir -p "$DEST"
python3 check_wgb_invariance.py --wgb "$@" --pairs span > "$DEST/log_wgbchk.txt" 2>&1
echo "== 结果已复制到 $DEST/log_wgbchk.txt =="
