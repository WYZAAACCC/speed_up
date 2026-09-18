#!/bin/bash
L=/root/work/s1d_w/run.log
[ -f "$L" ] || L=/root/work/s1d_smoke/run.log
echo "=== D 版告警的完整文本（去重）==="
grep -a -A3 '\*\*\* Warning \*\*\*' "$L" | sed 's/^/  /' | head -60
echo
echo "=== 线性求解失败出现的次数 ==="
grep -ac "DIVERGED_ITS" "$L"
echo
echo "=== 头 3 次失败前后的上下文 ==="
grep -a -B2 -A2 "DIVERGED_ITS" "$L" | head -24
