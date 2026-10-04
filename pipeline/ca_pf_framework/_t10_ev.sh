#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10E253.log
echo "NOW $(date '+%m-%d %H:%M:%S')"
echo -n "  athermal 形核 = "; grep -ac 'athermal 形核' "$L" 2>/dev/null
echo -n "  s292 补投轮  = "; grep -ac 's292 补投轮' "$L" 2>/dev/null
grep -a 's292 补投轮' "$L" 2>/dev/null | tail -3 | sed 's/^/    /'
echo -n "  fresh 被拒   = "; grep -ac 'fresh` 被拒' "$L" 2>/dev/null
echo "  末条事件："
grep -a 'athermal 形核' "$L" 2>/dev/null | tail -1 | grep -oE 'step [0-9]+：T=[0-9.]+ K.*模式 \*\*[a-z]+\*\*' | cut -c1-120 | sed 's/^/    /'
awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/741/status 2>/dev/null
free -m | sed -n '2,3p' | sed 's/^/  /'
