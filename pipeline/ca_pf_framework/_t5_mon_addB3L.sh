#!/bin/bash
# _t5_mon_addB3L.sh --- 把 `t5B3L`（低密度判别臂）纳入板条状态监控
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_lathmon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧 lathmon pid=$P"
done
sleep 3
setsid $PY _t5_lathmon.py t5N276F,t5B2,t5B3L,t5N276 600 150 < /dev/null >> _w2_t5_lathmon.log 2>&1 &
sleep 80
SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
echo "  lathmon 进程数 = $(printf '%s\n' "$SNAP" | grep -c 'python _t5_lathmon.py')"
echo "  四臂引擎进程："
for t in t5N276F t5B2 t5B3L; do
  printf '     %-9s %s\n' "$t" "$(printf '%s\n' "$SNAP" | grep -c "bk_exp.py.*--tag $t")"
done
echo
echo '── 各臂最新板条状态 ──'
for t in t5N276F t5B2 t5B3L; do
  L=$(grep -E "\[$t\]" _w2_t5_lathmon.log 2>/dev/null | sort -u | tail -1)
  [ -n "$L" ] && echo "$L" | cut -c1-175 | sed 's/^/  /'
done
echo
free -m | sed -n 2p | sed 's/^/  /'
