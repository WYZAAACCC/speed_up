#!/bin/bash
# _t10_pre_shutdown.sh --- 重启 WSL 前：停引擎 + 固化峰值证据 + 数据改名保留
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_t10_pre_shutdown.log
: > "$LOG"
{
  echo "════ 重启 WSL（24GB→28GB）前的收尾  $(date '+%m-%d %H:%M:%S') ════"
} >> "$LOG"

# ① 记录当前跑的真实峰值（这是"23GB 看门狗下未被杀"的证据）
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) P=$X; break ;; esac
done
if [ -n "$P" ]; then
  echo "  引擎 pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ')" >> "$LOG"
  awk '/^VmRSS|^VmHWM|^VmSwap|^Threads/{printf "    %s\n", $0}' /proc/$P/status >> "$LOG"
  echo "  ⇒ 峰值 VmHWM 换算：$(awk '/VmHWM/{printf "%.2f GB", $2/1048576}' /proc/$P/status)" >> "$LOG"
else
  echo "  引擎不在" >> "$LOG"
fi
echo "  free:" >> "$LOG"; free -m | sed -n '2,3p' | sed 's/^/    /' >> "$LOG"

# ② 停掉一切（WSL 重启也会杀，但先停干净）
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*_t10_mon.sh*|*_t10_relaunch2.sh*|*_t5_mon_keeper*|*_t5_keeper_all*) kill -9 "$X" 2>/dev/null ;;
  esac
done
sleep 4

# ③ 数据改名保留（**不删**）
TS=$(date +%m%d_%H%M)
for D in _exp/_bk_t5/dry_t10N160; do
  [ -d "$D" ] && mv "$D" "${D}_wd23peak2249_$TS" && echo "  $D → $(basename ${D}_wd23peak2249_$TS)" >> "$LOG"
done
# 顺带归档旧退出码证据
[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_$(date +%m%d_%H%M).txt
echo "  数据目录清单：" >> "$LOG"
ls -d _exp/_bk_t5/dry_t10N160* 2>/dev/null | sed 's/^/    /' >> "$LOG"
echo "done $(date '+%H:%M:%S')" >> "$LOG"
cat "$LOG"
