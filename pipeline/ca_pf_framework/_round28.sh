#!/usr/bin/env bash
# _round28.sh --- 把 T21 改成"轨迹 + 同一 f 插值"后重跑（Round 27 的自我降级要求）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
import ast; ast.parse(open('T21_beta_calib.py').read()); print('SYNTAX OK')
EOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T21_beta_calib*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25 \
        --betas 0,1.5,3.5 --f-target 0.05 > _t21c.log 2>&1 < /dev/null &
echo "T21c pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-56
free -g | head -2
