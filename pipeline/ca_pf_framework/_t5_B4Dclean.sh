#!/bin/bash
# _t5_B4Dclean.sh --- 清掉重复的 B4D 进程，只留一个（**按 PID 杀，不用 pkill -f**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "── 当前 B4D 相关进程 ──"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B4D' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
PIDS=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B4D' | awk '{print $1}')
N=$(printf '%s\n' "$PIDS" | awk 'NF' | wc -l)
echo "  计数 = $N"
if [ "$N" -gt 1 ]; then
  for P in $PIDS; do kill -TERM "$P" 2>/dev/null && echo "  已 TERM pid=$P"; done
  sleep 6
  for P in $PIDS; do kill -KILL "$P" 2>/dev/null && echo "  已 KILL pid=$P"; done
  sleep 3
fi
echo "  清理后计数 = $(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5B4D')"
# 数据目录改名保留（**不删**）
D=_exp/_bk_t5/dry_t5B4D
if [ -d "$D" ]; then
  mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  旧数据已改名保留（未删）"
fi
echo
echo "── 重起一个干净跑 ──"
setsid $PY _t5_short.py --tag t5B4D --N 64 --nvar 1 --m 23 --B 1 --steps 600 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --no-nucleation --diag-terms \
    < /dev/null > _w2_t5_short_t5B4D.log 2>&1 &
sleep 200
echo "  进程 = $(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5B4D')"
echo
echo '════ ★ 带符号 `Δed` 输出（F1 = 孤立种子的界面）════'
grep -B1 -A1 'Δed 带符号' _w2_t5_short_t5B4D.log 2>/dev/null | tail -12 | cut -c1-215
echo
echo '════ `|Δed|` 行（对照）════'
grep 'F1 含母相' _w2_t5_short_t5B4D.log 2>/dev/null | tail -3 | cut -c1-215
