#!/bin/bash
# _t10_stop.sh --- 按用户指示停掉 10 µm 算例（数据改名保留，不删）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_t10_stop.log
: > "$LOG"
TS=$(date +%m%d_%H%M)
{
  echo "════ 停算例（用户指示：转去做 TRIP 框架）$TS ════"
  free -m | sed -n '2,3p' | sed 's/^/  停前 /'
} >> "$LOG"

# 记录停止时的状态（保留证据）
EN=""
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  echo "  停时：pid=$EN 历龄=$(ps -o etime= -p $EN | tr -d ' ')" >> "$LOG"
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "    %s\n", $0}' /proc/$EN/status >> "$LOG"
fi
echo "  末个步进行：" >> "$LOG"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10N160.log 2>/dev/null | tail -1 | cut -c1-170 | sed 's/^/    /' >> "$LOG"

# 杀：引擎 + 包装 + 所有本工程盯守
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*"_t5_short.py --tag t10N160"*|*_t10_swapalert.sh*|*_t10_auto.sh*|\
    *"_t10_mon.sh"*|*"_t10_wait.sh"*|*_t10_launch28.sh*)
      echo "  KILL pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;;
  esac
done
sleep 6

# 数据改名保留
for D in _exp/_bk_t5/dry_t10N160; do
  [ -d "$D" ] && mv "$D" "${D}_stopped_$TS" && echo "  数据 → $(basename ${D}_stopped_$TS)" >> "$LOG"
done
{
  echo "  停后内存："; free -m | sed -n '2,3p' | sed 's/^/    /'
  echo "  残留进程检查（应为空）："
  ps -eo pid,args --no-headers 2>/dev/null | grep -E 'bk_exp|_t10_' | grep -v grep | sed 's/^/    /'
  echo "  数据目录清单："
  ls -d _exp/_bk_t5/dry_t10N160* 2>/dev/null | sed 's/^/    /'
} >> "$LOG" 2>&1
cat "$LOG"
