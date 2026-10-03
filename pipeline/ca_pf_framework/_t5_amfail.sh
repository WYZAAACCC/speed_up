#!/bin/bash
# _t5_amfail.sh --- ★★★★★ 两臂为何只出 step 0 就没了
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "NOW = $(date '+%F %T')"
echo '════ ① 是否还有 t5AM 进程 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep t5AM | cut -c1-70 | sed 's/^/  /'
echo -n '  计数 = '; ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c t5AM
echo
echo '════ ② 两臂日志末尾 12 行（**找报错**）════'
for t in t5AM_ell t5AM_combo; do
  echo "  ── $t ──"
  tail -12 _w2_t5_am_$t.log 2>/dev/null | cut -c1-150 | sed 's/^/     /'
  echo "     （日志大小 = $(stat -c%s _w2_t5_am_$t.log 2>/dev/null) 字节）"
done
echo
echo '════ ③ 末步与快照 ════'
for t in t5AM_ell t5AM_combo; do
  printf '  %-12s 末步=%-6s 快照数=%s\n' "$t" \
    "$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(ls -1 _exp/_bk_t5/dry_$t/snap_*.npz 2>/dev/null | wc -l)"
done
