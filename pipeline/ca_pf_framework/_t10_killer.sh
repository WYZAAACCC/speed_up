#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== ① keeper 日志：22:0x–22:1x 的记录 ==="
for F in _w2_t5_mon_keeper.log _w2_t5_keeper_all.log; do
  echo "--- $F ---"
  tail -14 "$F" 2>/dev/null | cut -c1-175
done
echo
echo "=== ② keeper 续起的监控脚本，哪些带 kill？ ==="
for F in _t5_armon.py _t5_blkmon.py _t5_milewatch.py _t5_arwatch.py _t5_finalwatch2.py; do
  [ -f "$F" ] || continue
  N=$(grep -c 'os.kill\|subprocess.*kill\|SIGKILL\|SIGTERM' "$F" 2>/dev/null)
  echo "  $F : kill 相关行 = $N"
  [ "${N:-0}" -gt 0 ] && grep -n 'os.kill\|SIGKILL\|SIGTERM\|kill' "$F" | head -6 | cut -c1-160 | sed 's/^/      /'
done
echo
echo "=== ③ 现在还有哪些旧监控/守护在跑（可能反复重启杀手）==="
ps -eo pid,etime,args --no-headers 2>/dev/null | grep -E '\.py|\.sh' | grep -vE 'grep|_t10_' | cut -c1-150
