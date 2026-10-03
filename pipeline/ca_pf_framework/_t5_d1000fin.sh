#!/bin/bash
# _t5_d1000fin.sh --- `t5AD_1000`（eng-elong=10）的终态（它刚跑完）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 是否已结束（进程 + 末步 + 目标）════'
printf '  进程 = %s   末步 = %s  （目标 steps=1400）\n' \
  "$(ps -eo args --no-headers 2>/dev/null | awk '/--tag t5AD_1000/{n++} END{print n+0}')" \
  "$(tail -1 _exp/_bk_t5/dry_t5AD_1000/series.csv 2>/dev/null | cut -d, -f1)"
echo
echo '════ ② 终态日志（退出摘要）════'
for L in _w2_t5_ad_t5AD_1000.log _w2_t5_short_t5AD_1000.log; do
  [ -f "$L" ] && { echo "  ── $L ──"; tail -12 "$L" | cut -c1-140 | sed 's/^/     /'; break; }
done
echo
echo '════ ③ 终态几何量（目标②：eng-elong=10 在 1400 步时的长宽比/长厚比）════'
grep -E '  t5AD_1000 +step ' _w2_t5_ar_monitor.log 2>/dev/null | sort -u | tail -5 | sed 's/^/  /'
echo
echo '════ ④ 终态块表（③④⑤）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv, os
p = '_exp/_bk_t5/dry_t5AD_1000/series.csv'
if not os.path.exists(p):
    print('  （无 series.csv）'); raise SystemExit
rows = list(csv.DictReader(open(p, newline='')))
print('  总行数 = %d，末步 = %s' % (len(rows), rows[-1]['step']))
print('  %-7s %-8s %-7s %-5s %-9s %-10s %s' % ('step','nslab_n','nf3_col','nf2','nblk_sig','n_var_sig','blk_laths'))
for r in rows:
    if (r.get('nblk_sig') or '').strip():
        print('  %-7s %-8s %-7s %-5s %-9s %-10s %s' % (r['step'], r.get('nslab_n'), r.get('nf3_col'),
              (r.get('nf2') or '').strip(), (r.get('nblk_sig') or '').strip(),
              (r.get('n_var_sig') or '').strip(), (r.get('blk_laths') or '')[:12]))
PYEOF
