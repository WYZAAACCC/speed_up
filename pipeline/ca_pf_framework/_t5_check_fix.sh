#!/bin/bash
# _t5_check_fix.sh --- ★ 检验修复是否成立（新臂 nvar=4/m=12 vs 旧臂）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo
echo '── ★ 形核计数：新臂 t5F4（nvar=4,m=12） vs 旧臂 t5L0（nvar=12,m=4）──'
for t in t5F4 t5L0 t5L62; do
  f="_w2_t5_short_$t.log"
  [ -f "$f" ] || { printf '  %-6s （无日志）\n' "$t"; continue; }
  printf '  %-6s 形核公告=%-4s 被拒=%-4s\n' "$t" \
    "$(grep -c 'athermal 形核' "$f")" "$(grep -c '被引擎拒' "$f")"
done
echo
echo '── ★ series 末行（决定性：nslab_n 能否 > 4）──'
$PY - <<'PYEOF'
import csv, os
for t in ('t5F4', 't5L0', 't5L62'):
    p = '_exp/_bk_t5/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-6s （无 series）' % t); continue
    r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    L = r[-1]
    print('  %-6s %2d 行 末步 %-5s  nslab_n=%-4s nf3=%-7s nblk=%-4s Vt=%s'
          % (t, len(r), L['step'], L.get('nslab_n'), (L.get('nf3') or '')[:7],
             (L.get('nblk_sig') or '')[:4], L['Vt'][:14]))
    ns = [(x['step'], x.get('nslab_n')) for x in r if (x.get('nslab_n') or '').strip()]
    if ns:
        print('          nslab_n 轨迹: %s' % ns[:8])
PYEOF
echo
echo '── 新臂的形核/拒绝行（前 6）──'
grep -nE 'athermal 形核|被引擎拒' _w2_t5_short_t5F4.log 2>/dev/null | head -6 | cut -c1-124 | sed 's/^/  /'
echo
free -m | sed -n 2p | sed 's/^/  /'
