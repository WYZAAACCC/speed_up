#!/usr/bin/env bash
# _restart_t13b_t24.sh --- 用**缩小后的种子**（R=150 nm ⇒ 面内直径 300 nm）重启
#   T13b 与 T24rve：原规格（2R=600 nm, L=4.8 µm）在 n=128/256 档 `d/2R < 2.5`
#   ⇒ 晶核初始重叠、"形核密度"无意义（D12d 的必要≠充分补丁）。
#   T16 保持不变（L=9.6 µm, n0=100 ⇒ d/2R = 3.45 ✓ 有效）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  case "$CMD" in
    *T13b_verify_nv*|*T24_verify_grouping*)
      echo "KILL $P: $(echo "$CMD" | cut -c1-70)"; kill -9 "$P" ;;
  esac
done
sleep 3

$PY -c "import ast;[ast.parse(open(f).read()) for f in ('T13b_verify_nv.py','T24_verify_grouping.py')];print('SYNTAX OK')" || exit 2

setsid nohup "$PY" -u T13b_verify_nv.py --L-um 4.8 --dx-nm 50 --ns 64,128,256 \
        --f-target 0.10 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b   pid=$!"
setsid nohup "$PY" -u T24_verify_grouping.py --mode rve --L-um 4.8 --dx-nm 50 \
        --n0 64 --f-target 0.10 --adv proj2 > _t24rve.log 2>&1 < /dev/null &
echo "T24rve pid=$!"
sleep 25
echo '--- T13b 规格检查 ---'
grep -v -e RuntimeWarning -e 'self.reinit' _t13b.log | head -12
echo '--- alive ---'
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-70
free -g | head -2
