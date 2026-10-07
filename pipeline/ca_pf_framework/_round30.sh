#!/usr/bin/env bash
# _round30.sh --- 修 T21 的夹逼缺陷后重跑：`f_ar_ref` 3e-3 -> 2e-3，并把扫描扩到 4 档
#   （0 / 1.5 / 3.5 / 6.5），因为 Round 29 已确认 **AR 同时受 Δf 与 β 控制** ——
#   要让"β 的效应"在一个 Δf 上尽可能看清楚，至少需要 4 个 β 点。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
p = 'T21_beta_calib.py'
s = open(p).read()
s = s.replace('f_ar_ref=3.0e-3):', 'f_ar_ref=2.0e-3):')
open(p, 'w').write(s)
import ast; ast.parse(s); print('SYNTAX OK, f_ar_ref -> 2e-3')
EOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T21_beta_calib*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25 \
        --betas 0,1.5,3.5,6.5 --f-target 0.05 > _t21d.log 2>&1 < /dev/null &
echo "T21d pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-54
free -g | head -2
