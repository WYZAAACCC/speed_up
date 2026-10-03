#!/bin/bash
# _t5_mobprog.sh --- 确认修好后两臂**真的能前进**（这是 BUG 修复的决定性判据）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
for i in $(seq 1 20); do          # 最多 20 × 30 s = 10 min
  S1=$(tail -1 _exp/_bk_t5/dry_t5AM_ell/series.csv 2>/dev/null | cut -d, -f1)
  S2=$(tail -1 _exp/_bk_t5/dry_t5AM_combo/series.csv 2>/dev/null | cut -d, -f1)
  if [ -n "$S1" ] && [ "$S1" -ge 40 ] 2>/dev/null; then break; fi
  # 崩溃检测：进程没了且步数没到目标
  A=$(ps -eo args --no-headers 2>/dev/null | grep -c 'dry_t5AM_ell')
  [ "$A" -eq 0 ] && { echo "⚠ t5AM_ell 进程已消失（可能又崩）"; break; }
  sleep 30
done
echo "NOW = $(date '+%F %T')"
for t in t5AM_ell t5AM_combo; do
  printf '  %-12s 末步=%-6s 行数=%-4s 进程=%s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(wc -l < _exp/_bk_t5/dry_$t/series.csv 2>/dev/null)" \
    "$(ps -eo args --no-headers 2>/dev/null | grep -c "dry_$t")"
done
echo '════ 若末步 ≥40 ⇒ **BUG 修好、公式真正跑起来了**（决定性判据）════'
echo '── 两臂日志末尾 3 行（确认无新 traceback）──'
for t in t5AM_ell t5AM_combo; do
  echo "  ── $t ──"
  tail -3 _w2_t5_short_$t.log 2>/dev/null | cut -c1-130 | sed 's/^/     /'
  grep -c Traceback _w2_t5_short_$t.log 2>/dev/null | sed 's/^/     Traceback 次数=/'
done
