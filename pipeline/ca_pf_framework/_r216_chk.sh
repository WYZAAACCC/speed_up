#!/bin/bash
# _r216_chk.sh —— 一次看全：run log 大小/尾部/诊断命中 + 进度 + 进程。
# 用法：bash _r216_chk.sh <runlog> <臂名>
cd "$(dirname "$0")" || exit 1
LOG=${1:-_w2_r210_saSet2_run.log}
ARM=${2:-saSet2DT}
echo "=== run log: $LOG ==="
if [ -f "$LOG" ]; then
  echo "  大小 = $(stat -c %s "$LOG") 字节；行数 = $(wc -l < "$LOG")"
  echo "  '三项量级' 命中 = $(grep -c '三项量级' "$LOG" || true)"
  echo "  '135.7'   命中 = $(grep -c '135\.7' "$LOG" || true)"
  echo "  'diag_terms' 命中 = $(grep -c 'diag_terms' "$LOG" || true)"
  echo "  Traceback 命中 = $(grep -c 'Traceback' "$LOG" || true)"
  echo "  --- 尾部 14 行 ---"
  tail -14 "$LOG" | sed 's/^/    /'
else
  echo "  ❌ 不存在"
fi
echo
echo "=== 进度：$ARM ==="
F="_exp/_bk_mb/dry_$ARM/series.csv"
if [ -f "$F" ]; then
  echo "  rows = $(wc -l < "$F")；last_step = $(tail -1 "$F" | cut -d, -f1)"
else
  echo "  (还没有 series.csv)"
fi
[ -f "_exp/_bk_mb/dry_$ARM/diag_terms.json" ] && \
  echo "  ✅ diag_terms.json 已落盘" || echo "  (diag_terms.json 尚未落盘)"
echo
echo "=== 进程 / 内存 ==="
echo "  _bk_exp.py 进程数 = $(pgrep -fc '_bk_exp[.]py' || true)"
free -m | head -2 | sed 's/^/  /'
