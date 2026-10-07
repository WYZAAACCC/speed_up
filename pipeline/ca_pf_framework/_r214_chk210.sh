#!/bin/bash
# _r214_chk210.sh —— 确认 `_r210` 的臂到底带没带 `--diag-terms`（不猜，直接查）。
cd "$(dirname "$0")" || exit 1
echo "=== ① `_r178_repro.py --emit` 打出的命令行（末 320 字符）==="
if [ -f _w2_r210_saSet2_emit.log ]; then
  grep -m1 'miniconda3' _w2_r210_saSet2_emit.log | tail -c 320
  echo
else
  echo "  (emit log 不存在)"
fi
echo
echo "=== ② `_r210.log` 里打印的**最终**命令行（末 320 字符）==="
grep -m1 '最终命令行' -A2 _w2_r210.log | tail -c 340
echo
echo "=== ③ run log 里 '三项量级' 出现次数（>0 才算带上了）==="
for f in _w2_r210_saSet2DT_run.log _w2_r210_saOddGDT_run.log; do
  if [ -f "$f" ]; then
    printf '  %-30s %s 行, 命中 %s\n' "$f" "$(wc -l < "$f")" \
      "$(grep -c '三项量级' "$f" || true)"
  else
    printf '  %-30s (不存在)\n' "$f"
  fi
done
echo
echo "=== ④ run log 尾部（看它跑到哪、有没有报错）==="
tail -8 _w2_r210_saSet2DT_run.log 2>/dev/null
echo
echo "=== ⑤ 进度 ==="
printf '  saSet2DT  rows=%s last=%s\n' \
  "$(wc -l < _exp/_bk_mb/dry_saSet2DT/series.csv 2>/dev/null)" \
  "$(tail -1 _exp/_bk_mb/dry_saSet2DT/series.csv 2>/dev/null | cut -d, -f1)"
