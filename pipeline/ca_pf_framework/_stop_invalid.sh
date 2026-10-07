#!/usr/bin/env bash
# _stop_invalid.sh --- 停掉 Δx=75 nm 的两条作业：**板条厚 100 nm 在该分辨率下只有 1.3 胞**
#   ⇒ 零等值面跨不到一个胞、离散体积不可靠、曲率项 ∝1/t 被严重高估 ⇒ 板条**假收缩**。
#   实测（_t13b.log 心跳）：step=20 时 f=0.00034，而晶核分数 f_seed=1.36e-3
#   ⇒ **缩到 25%**。T16（Δx=50 nm ⇒ t/Δx=2）也偏低，一并停。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T16_verify_rve*|*T13b_verify_nv*|*T24_verify_grouping*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 2
pgrep -a python | cut -c1-48
