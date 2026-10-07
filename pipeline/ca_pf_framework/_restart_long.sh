#!/usr/bin/env bash
# _restart_long.sh --- A1 改默认后：杀掉仍在跑的旧作业，用**新默认**重启。
#   理由：T16/T13b 里必然发生变体-变体碰撞 ⇒ 旧默认（winner 场曲率）给出的
#   统计量属于**已被取代的格式**，跑完也要作废 ⇒ 早停早重启更省机时。
#   按 cmdline 精确匹配 + 按 cwd 校验，不做进程名一刀切（AGENTS §3.10/§3.11）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

for P in $(pgrep -x python); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null || echo '')
  CWD=$(readlink /proc/$P/cwd 2>/dev/null || echo '?')
  case "$CMD" in
    *T16_verify_rve*|*T13b_verify_nv*)
      echo "KILL pid=$P cwd=$CWD"
      kill -9 "$P" ;;
  esac
done
sleep 3
echo '--- remaining ---'
pgrep -a python | cut -c1-90

setsid nohup "$PY" -u T16_verify_rve.py --L-um 9.6 --dx-nm 50 --n0 100 \
        --f-target 0.10 --adv proj2 > _t16prod.log 2>&1 < /dev/null &
echo "T16prod pid=$!"
setsid nohup "$PY" -u T13b_verify_nv.py --L-um 4.8 --dx-nm 50 --ns 64,128,256 \
        --f-target 0.10 --adv proj2 > _t13b.log 2>&1 < /dev/null &
echo "T13b    pid=$!"
sleep 15
ps -o pid,sess,etime,args --no-headers -C python | cut -c1-78
free -g | head -2
