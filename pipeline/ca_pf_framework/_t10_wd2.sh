#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10N160.log
echo "=== ★ 包装层收尾摘要（会明写「峰值 RSS（VmHWM，看门狗实测）」与「⚠ 被看门狗杀」）==="
grep -a '峰值 RSS\|看门狗\|VmHWM' "$L" 2>/dev/null | cut -c1-200
echo
echo "=== 日志最末尾 25 行（含收尾）==="
tail -25 "$L" 2>/dev/null | cut -c1-200
echo
echo "=== ★ 看门狗实现（_t5_short.py 155-175）==="
sed -n '155,175p' _t5_short.py | cut -c1-175
echo
echo "=== ★ 本轮 mem-limit 值（argv）==="
grep -a 'mem-limit\|内存上限\|限额' "$L" 2>/dev/null | head -5 | cut -c1-175
