#!/usr/bin/env bash
# _stop_t13b_quick.sh --- 停掉"跑不动"的 T13b_quick：
#   心跳实测 f 在 20 步里只从 0.00208 涨到 0.00217（+4% 相对）⇒ 板条**几乎不长**。
#   根因（【推理】，待下一轮验证）：种子缩到 R=150 nm/t=50 nm 之后，**薄小板的弹性自能**
#   与 Δf=2e8 相抵 ⇒ 净驱动力≈0（T20 已实测：df=0.5e8 时 R=240/t=100 的板**变小**）。
#   ⇒ 两条约束耦合：① `d ≥ 2.5·2R_seed`（R9）要**小种子**；② 种子要**够大才长得动**。
#   ⇒ 正解是**放大盒子**而不是缩种子：R=300 nm/t=100 nm + `d ≥ 1.5 µm`
#     ⇒ n=64/128/256 分别要 L ≥ 6.0/7.6/9.5 µm ⇒ **L = 9.6 µm 一档全包**（与 T16 同盒）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T13b_verify_nv*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 2
pgrep -a python | cut -c1-58
