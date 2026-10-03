#!/bin/bash
# _t5_mon_restart2.sh --- 干净重启监控（**按精确 pid 杀** + **setsid 防管道挂住**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_ar_monitor.log

{
  echo "[$(date '+%F %T')] ════ 重启监控 v2：纳入 t5V2（在跑的长臂）+ t5H3（参照）════"
  echo "  ① 停旧监控（**按精确 pid**，不按模式匹配 —— 避免 pgrep 自匹配）"
} >> "$LOG"

# ① 找旧监控 pid：**用 ps + 精确过滤**（排除本脚本自己）
OLD=$(ps -eo pid,args --no-headers | grep '[p]ython _t5_armon.py' | awk '{print $1}')
for P in $OLD; do
  kill -TERM "$P" 2>/dev/null && echo "     已 TERM pid=$P" >> "$LOG"
done
sleep 4
STILL=$(ps -eo pid,args --no-headers | grep '[p]ython _t5_armon.py' | awk '{print $1}')
for P in $STILL; do kill -9 "$P" 2>/dev/null && echo "     已 KILL pid=$P" >> "$LOG"; done
sleep 2

# ② 语法检查
if $PY -m py_compile _t5_armon.py; then echo "  ② 语法 OK" >> "$LOG"; else echo "  ② ❌ 语法失败"; exit 1; fi

# ③ ★ 启动新监控：**setsid + 全部 stdio 重定向到文件**（防"后台进程保持管道 ⇒ 父 shell 挂住"）
echo "  ③ 启动新监控（80 轮 × 300 s ≈ 6.7 h；setsid + 全重定向）" >> "$LOG"
setsid $PY _t5_armon.py 80 300 < /dev/null >> "$LOG" 2>&1 &
disown 2>/dev/null || true
echo "     已提交（setsid 脱离本 shell）" >> "$LOG"
exit 0
