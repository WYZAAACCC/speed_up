#!/bin/bash
# _t5_st43.sh --- 第 43 轮：t5H3 是否突破 m=6 的封顶
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo
echo '── ★ 形核计数：新臂 t5H3（m=24） vs 上一臂 t5G3（m=6）──'
for t in t5H3 t5G3; do
  f="_w2_t5_short_$t.log"
  [ -f "$f" ] || { printf '  %-6s （无日志）\n' "$t"; continue; }
  printf '  %-6s 公告=%-4s  被拒=%-4s\n' "$t" \
    "$(grep -c 'athermal 形核' "$f" 2>/dev/null)" \
    "$(grep -c '被引擎拒' "$f" 2>/dev/null)"
done
echo
echo '── ★ series：nslab_n 轨迹（判据 >6）──'
for t in t5H3 t5G3; do
  $PY - "$t" <<'PYEOF'
import csv, os, sys
t = sys.argv[1]
p = '_exp/_bk_t5/dry_%s/series.csv' % t
if not os.path.exists(p):
    print('  %-6s ⏳ 还没有 series' % t); raise SystemExit
r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
L = r[-1]
print('  ── %s：%d 行，末步 %s ──' % (t, len(r), L['step']))
print('     nslab_n=%s  nf3=%s  nf3_col=%s  nf2=%s  box_touch=%s'
      % (L.get('nslab_n'), (L.get('nf3') or '')[:6], (L.get('nf3_col') or ''),
         L.get('nf2'), L.get('box_touch')))
print('     轨迹: %s' % [(x['step'], x.get('nslab_n')) for x in r
                         if (x.get('nslab_n') or '').strip()][:12])
ns = [int(x['nslab_n']) for x in r if (x.get('nslab_n') or '').strip()]
if ns:
    print('     ⇒ **最大 nslab_n = %d**%s' % (max(ns),
          ('  ✅ **突破 6**' if max(ns) > 6 else '  ⚠ 还没突破 6')))
PYEOF
done
echo
grep -oE '\[ *[0-9]+\] Vt=[0-9.]+ .*nslab=[0-9]+' _w2_t5_short_t5H3.log 2>/dev/null \
  | tail -3 | cut -c1-72 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
