#!/bin/bash
# _t5_blkmon_restart.sh --- 重启块监控（**判据已修**：块表行 = `nblk_sig` 非空）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_n276_monitor.log

{
  echo "[$(date '+%F %T')] ════ 块监控重启（判据修正）════"
  echo "[$(date '+%F %T')]   ⚠ 旧判据用 `nf2` 非空找块表行 —— 错：`nf2` 是**常规列**（每行都有值），"
  echo "[$(date '+%F %T')]     而块表值只在 **step 的 100 倍数**行 ⇒ 旧判据**永远读不到 nblk_sig**。"
  echo "[$(date '+%F %T')]   ★ 新判据：块表行 = **`nblk_sig` 非空**（实测出现在 step 0/100 …）"
} >> "$LOG"

# 停旧（按精确 pid，不用 pkill -f）
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[p]ython _t5_blkmon' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "[$(date '+%F %T')]   已停旧块监控 pid=$P" >> "$LOG"
done
sleep 3

$PY -m py_compile _t5_blkmon.py && echo "[$(date '+%F %T')]   语法 OK" >> "$LOG"

setsid $PY _t5_blkmon.py 200 300 < /dev/null >> "$LOG" 2>&1 &
sleep 18
N=$(ps -eo args --no-headers 2>/dev/null | grep -c '[p]ython _t5_blkmon')
echo "  新块监控进程数 = $N" >> "$LOG"
echo
echo '── 修后的首轮读数（应能看到 nblk_sig 的真值）──'
grep -E '③ 成块|④ 块间|⑤ 自协调|块表行' "$LOG" 2>/dev/null | tail -5 | sed 's/^/  /'
