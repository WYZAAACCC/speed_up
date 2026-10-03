#!/bin/bash
# _t5_mon_addB2.sh --- 把 `t5B2` 纳入板条状态监控（它是问题 B 的判别实验）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_lathmon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停旧 lathmon pid=$P"
done
sleep 3
# t5B2 与 t5N276 步对齐比较是核心 ⇒ 一起监控
setsid $PY _t5_lathmon.py t5N276F,t5B2,t5N276 600 120 < /dev/null >> _w2_t5_lathmon.log 2>&1 &
sleep 70
SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
echo "  lathmon 进程数 = $(printf '%s\n' "$SNAP" | grep -c 'python _t5_lathmon.py')"
echo "  t5B2 引擎 = $(printf '%s\n' "$SNAP" | grep -c 'bk_exp.py.*--tag t5B2')"
echo
echo '── 首轮（应含 t5B2）──'
grep -E '\[t5B2\]' _w2_t5_lathmon.log 2>/dev/null | tail -2 | cut -c1-190 | sed 's/^/  /'
echo '── 两臂现在都在跑 ──'
printf '  t5N276F 末步=%s   t5B2 末步=%s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5N276F/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(tail -1 _exp/_bk_t5/dry_t5B2/series.csv 2>/dev/null | cut -d, -f1)"
