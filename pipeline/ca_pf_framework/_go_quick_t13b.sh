#!/usr/bin/env bash
# _go_quick_t13b.sh --- 杀掉旧的 T13b（256 档、无心跳），启动带心跳的快速诊断跑。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T13b_verify_nv*64,128,256*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
$PY - <<'EOF'
import ast
ast.parse(open('T13b_verify_nv.py').read()); print('SYNTAX OK')
EOF
setsid nohup "$PY" -u T13b_verify_nv.py --L-um 4.8 --dx-nm 50 --ns 64,128 \
        --f-target 0.035 --adv proj2 > _t13b_quick.log 2>&1 < /dev/null &
echo "T13bQuick pid=$!"
sleep 25
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-64
