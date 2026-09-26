#!/bin/bash
# 逐块切除对照：定位「mortar 交换在生产副本里是死的」由哪一块引入。
# 判据：gam0_int 是否从 0 开始变化（非平衡初值 GAMIC=0，驱动力 k_att*(c-Gam) != 0）。
set +u
cd /mnt/f/speed_up/pipeline/gibbs/prod3d || exit 1
for D in "$@"; do
  echo "########## DROP = $D ##########"
  TISO=1800 GAMIC=0 DROP="$D" PRECOND=mumps NLATOL=1e-7 DTMAX=1e-7 \
    WGB=8e-6 DX=2e-6 python3 make_gibbs3d.py > /dev/null 2>&1
  # ⚠ 必须用**绝对路径**：_run_case.sh 会先 cd 到 /root/work/<case>，
  #   相对路径在那里不存在 ⇒ case.i 变空 ⇒ 报 "no generation block"。
  F=/mnt/f/speed_up/pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d_iso_neq_drop${D}.i
  sed 's/\r$//' _run_case.sh > /tmp/rc.sh
  WALL=600 bash /tmp/rc.sh "g3dd_$D" "$F" Executioner/end_time=2e-7 2>&1 \
    | grep -E 'rc=|未收敛|^time|^[0-9.]+e-0'
done
