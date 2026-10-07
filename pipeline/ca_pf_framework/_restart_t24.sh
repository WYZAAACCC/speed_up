#!/usr/bin/env bash
# _restart_t24.sh --- 用**真正的 Burgers 6 族**重启 B4 真实 RVE 统计。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY -c "import ast;ast.parse(open('T24_verify_grouping.py').read());print('SYNTAX OK')" || exit 2
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T24_verify_grouping*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 2
setsid nohup "$PY" -u T24_verify_grouping.py --mode rve --L-um 4.8 --dx-nm 50 \
        --n0 64 --f-target 0.10 --adv proj2 > _t24rve.log 2>&1 < /dev/null &
echo "T24rve pid=$!"
sleep 15
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-72
