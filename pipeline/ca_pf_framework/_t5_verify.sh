#!/bin/bash
# _t5_verify.sh --- 交付完整性核对（本目标产出是否都已落盘）
cd /mnt/f/speed_up || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 未提交的改动（应只剩无关紧要的）════'
git status --porcelain 2>/dev/null | head -12 | sed 's/^/  /'
echo
echo '════ ② 最近 6 次提交 ════'
git log --oneline -6 | sed 's/^/  /'
echo
echo '════ ③ 本目标的关键产物（应都存在）════'
for f in R581_T5_RESTART.md _t5_armon.py _t5_mon_keeper.sh _t5_finalwatch2.py \
         _t5_ab_elong.sh _t5_ab_dose2.sh _t5_dose_hi.sh _t5_mon2.sh _t5_alive.sh; do
  p="pipeline/ca_pf_framework/$f"
  if [ -f "$p" ]; then printf '  ✅ %-24s %s 字节\n' "$f" "$(stat -c%s "$p")"
  else printf '  ❌ %-24s **缺失**\n' "$f"; fi
done
echo
echo '════ ④ 数据盘（F 盘）上的日志 ════'
for f in _w2_t5_ar_monitor.log _w2_t5_mon_keeper.log _w2_t5_final_ar.log _w2_t5_ab_dose.log; do
  p="pipeline/ca_pf_framework/$f"
  if [ -f "$p" ]; then printf '  ✅ %-26s %s 字节  最后写 %s\n' "$f" "$(stat -c%s "$p")" "$(stat -c%y "$p" | cut -d. -f1)"
  else printf '  ⚠ %-26s （未建）\n' "$f"; fi
done
echo
echo '════ ⑤ 文档行数 ════'
wc -l pipeline/ca_pf_framework/R581_T5_RESTART.md 2>/dev/null | sed 's/^/  /'
