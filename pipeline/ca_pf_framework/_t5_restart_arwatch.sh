#!/bin/bash
# _t5_restart_arwatch.sh --- 重启衰减监视器（E3 守卫已修）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
OUT=_w2_t5_ar_decay.log

$PY -m py_compile _t5_arwatch.py || { echo '  ❌ 语法错误'; exit 1; }
echo "[$(date '+%F %T')] （重启）E3 守卫已加：同一臂只报一次，回升到 5 以上则重置" >> "$OUT"

for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_arwatch' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧 arwatch pid=$P"
done
sleep 3
setsid $PY _t5_arwatch.py t5N276,t5NR 120 400 < /dev/null >> "$OUT" 2>&1 &
sleep 15

SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
echo "  arwatch 进程数 = $(printf '%s\n' "$SNAP" | grep -c 'python _t5_arwatch.py')"
echo
echo '── 修后首轮（E3 应只报一次）──'
tail -4 "$OUT" | sed 's/^/  /'
