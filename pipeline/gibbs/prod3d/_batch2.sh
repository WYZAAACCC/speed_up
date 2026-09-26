#!/bin/bash
# 第二批并行作业：全部用 dt 规则（k_att·dt = 0.01 ⇒ DTMAX=1e-8）
#   amr2  : AMR 开（6 步，interval=2 ⇒ 至少适配 3 次）—— 数值项 1
#   noamr2: 同设置但 AMR 关（A/B 对照）
#   m2d2  : 二维熔池（修 m2d 的 13 次不收敛）
#   iso3d2: 等温非平衡 3D（给后面的 T5/拖曳改动做基线）
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
BASE="STAGGER=1 AUTOSC=0 PRECOND=mumps NLATOL=1e-7 DTMAX=1e-8 WGB=8e-6 DX=2e-6"
gen() {  # gen <suf> <extra env...>
  suf=$1; shift
  env $BASE OUTSUF="$suf" "$@" python3 make_gibbs3d.py > /dev/null 2>&1
  f=$(ls -t *"$suf".i 2>/dev/null | head -1)
  [ -n "$f" ] || { echo "**生成失败 $suf"; return 1; }
  echo "$suf -> $f"
}
gen _amr2   AMR=1
gen _noamr2 AMR=0
gen _m2d2   DIM2=1
gen _iso3d2 TISO=1800 GAMIC=0 DISP=1
H=/mnt/f/speed_up/pipeline/gibbs/prod3d
cat > /tmp/batch2.list <<EOF
amr2|$H/$(ls -t *_amr2.i | head -1)|Executioner/end_time=6e-7
noamr2|$H/$(ls -t *_noamr2.i | head -1)|Executioner/end_time=6e-7
m2d2|$H/$(ls -t *_m2d2.i | head -1)|Executioner/end_time=3e-7
iso3d2|$H/$(ls -t *_iso3d2.i | head -1)|Executioner/end_time=3e-7
EOF
cat /tmp/batch2.list
