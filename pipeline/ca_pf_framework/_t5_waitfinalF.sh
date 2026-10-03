#!/bin/bash
# _t5_waitfinalF.sh --- ★★★★★ 等 `t5N276F` 到终态，做**终态判定**（判据④⑤）+ 七项汇总
#
# ## 预登记判据（**跑之前写死**）
#   ④ 终态长宽比 ≥ 5（修复前终态 **1.22**）
#   ⑤ 终态长厚比 ≥ 10（修复前终态 **1.15**）
#   ★ 并同时报：活跃场数、占比、`nblk_sig`、`nf2`、`blk_laths`、唯一性
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LIM=${1:-14400}
T=0
echo "  等 t5N276F 结束（最多 ${LIM} s；判据：进程消失 且 末步稳定）"
LAST=0; STABLE=0
while [ "$T" -lt "$LIM" ]; do
  P=$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5N276F')
  S=$(tail -1 _exp/_bk_t5/dry_t5N276F/series.csv 2>/dev/null | cut -d, -f1)
  [ -z "$S" ] && S=0
  if [ "$P" -eq 0 ]; then
    STABLE=$((STABLE + 1))
    [ "$STABLE" -ge 3 ] && { echo "  ★ 引擎已退出（末步 $S）"; break; }
  else
    STABLE=0
  fi
  LAST=$S
  sleep 60; T=$((T + 60))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s  末步 = ${LAST}"
echo
echo '════ ① 终态日志（退出摘要）════'
grep -E '准静态钟|提前结束|走到 step|exit=|判决' _w2_t5_short_t5N276F.log 2>/dev/null | tail -5 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ② 终态块表（末 3 行）════'
$PY - <<'PYEOF'
import csv
p='_exp/_bk_t5/dry_t5N276F/series.csv'
b=[r for r in csv.DictReader(open(p,newline='')) if (r.get('nblk_sig') or '').strip()]
for r in b[-3:]:
    print('  step %-6s nslab_n=%-4s nf3_col=%-4s nf2=%-6s nblk_sig=%-3s n_var_sig=%-3s blk_laths=%s'
          %(r['step'],r.get('nslab_n'),r.get('nf3_col'),r.get('nf2'),r.get('nblk_sig'),
            r.get('n_var_sig'),(r.get('blk_laths') or '')[:26]))
PYEOF
echo
echo '════ ③ ★ 终态步对齐对照 + 判据④⑤ ════'
S=$(tail -1 _exp/_bk_t5/dry_t5N276F/series.csv 2>/dev/null | cut -d, -f1)
$PY _t5_samecmp.py "${S},2160" t5N276,t5N276F 2>&1 | sed -n '3,9p'
echo
echo '════ ④ 形核账目（终态）════'
$PY - <<'PYEOF'
import json, os
from collections import Counter
F='_exp/_bk_t5/dry_t5N276F/nuc_dbg.json'
if not os.path.exists(F):
    print('  （nuc_dbg.json 还没落盘）'); raise SystemExit
j=json.load(open(F)); ev=j.get('T_events',[])
if not ev:
    print('  （T_events 空）'); raise SystemExit
f=[e['field'] for e in ev]
print('  事件 %d ｜ 不同场 %d ｜ **唯一性 = %.2f**（修复前 0.56）'
      %(len(ev),len(set(f)),len(set(f))/len(ev)))
print('  模式分布 = %s'%dict(Counter(e['mode'] for e in ev)))
print('  n_target(末) = %s'%ev[-1].get('n_target'))
PYEOF
echo
echo '════ ⑤ 全部监控日志的最后读数 ════'
for L in _w2_t5_lathmon.log _w2_t5_nucmon_t5N276F.log _w2_t5_n276_monitor.log; do
  [ -f "$L" ] && { echo "  ── $L ──"; grep -E '\[t5N276F\]' "$L" 2>/dev/null | sort -u | tail -2 | cut -c1-190 | sed 's/^/     /'; }
done
