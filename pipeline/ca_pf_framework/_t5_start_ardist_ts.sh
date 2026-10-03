#!/bin/bash
# _t5_start_ardist_ts.sh --- 启动"长宽比分布时间序列"（setsid）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ardist_ts.log

$PY -m py_compile _t5_ardist_ts.py || { echo '  ❌ 语法错误'; exit 1; }
echo "[$(date '+%F %T')] （启动器）语法 OK，setsid 启动" >> "$LOG"

# 每 600 s 一点（10 分钟），80 轮 ≈ 13 h
setsid $PY _t5_ardist_ts.py t5N276,t5NR 600 80 < /dev/null >> "$LOG" 2>&1 &
sleep 40

SNAP=$(ps -eo pid,args --no-headers 2>/dev/null)
echo "  ardist_ts 进程数 = $(printf '%s\n' "$SNAP" | grep -c 'python _t5_ardist_ts.py')"
echo
echo '── 首个数据点（**应能看出"<3 占比"**）──'
grep -E '\[t5N276\]|\[t5NR\]' "$LOG" 2>/dev/null | tail -4 | sed 's/^/  /'
echo
echo '── 七路监控/守护 ──'
for p in _t5_armon.py _t5_blkmon.py _t5_milewatch.py _t5_arwatch.py _t5_ardist_ts.py _t5_finalwatch2.py; do
  printf '  %-24s %s\n' "$p" "$(printf '%s\n' "$SNAP" | grep -c "python .*$p")"
done
printf '  %-24s %s\n' '_t5_keeper_all.sh' "$(printf '%s\n' "$SNAP" | grep -c 'bash _t5_keeper_all.sh')"
