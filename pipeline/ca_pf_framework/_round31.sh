#!/usr/bin/env bash
# _round31.sh --- T21 夹逼的**第二次收紧**：β=0 长得太快，step 5 就已 f=0.00205 > f_ar_ref=0.002
#   ⇒ 把参考点降到 **1.3e-3**（= 晶核分数 1.12e-3 之上一点），并在**前 10 步每步采**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
$PY - <<'EOF'
import ast
p = 'T21_beta_calib.py'
s = open(p).read()
s = s.replace('f_ar_ref=2.0e-3):', 'f_ar_ref=1.3e-3):')
old = """        if it <= 40:
            _do = (it % 5 == 0)
        else:
            _do = (it % 10 == 0)"""
new = """        if it <= 10:
            _do = True                      # 前 10 步**每步采**（把参考点稳稳夹住）
        elif it <= 40:
            _do = (it % 5 == 0)
        else:
            _do = (it % 10 == 0)"""
assert old in s, 'sampling block not found'
s = s.replace(old, new)
open(p, 'w').write(s)
ast.parse(s)
print('SYNTAX OK, f_ar_ref -> 1.3e-3, 前 10 步每步采')
EOF
for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T21_beta_calib*) echo "KILL $P"; kill -9 "$P" ;;
  esac
done
sleep 3
setsid nohup "$PY" -u T21_beta_calib.py --mode sweep --L-um 2.4 --dx-nm 25 \
        --betas 0,1.5,3.5,6.5 --f-target 0.05 > _t21e.log 2>&1 < /dev/null &
echo "T21e pid=$!"
sleep 20
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-52
free -g | head -2
