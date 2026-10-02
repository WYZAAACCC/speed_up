#!/bin/bash
# _t5_chk3.sh --- 检查 t5G3 是否存活 + 形核是否解封
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo '── 进程 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
N=$(ps -eo args --no-headers 2>/dev/null | grep -c '[_]bk_exp.py')
echo "  ⇒ 进程数 = $N"
echo
echo '── 进度（引擎每 --every 20 步打一行）──'
grep -oE '\[ *[0-9]+\] Vt=[0-9.]+' _w2_t5_short_t5G3.log 2>/dev/null | tail -3 | sed 's/^/  /'
echo "  日志 $(stat -c%s _w2_t5_short_t5G3.log 2>/dev/null || echo 0) 字节，末次修改 $(stat -c%y _w2_t5_short_t5G3.log 2>/dev/null | cut -c1-19)"
echo
echo '── ★ 形核计数（判据：被拒应显著下降）──'
printf '  形核公告 = %s\n' "$(grep -c 'athermal 形核' _w2_t5_short_t5G3.log 2>/dev/null)"
printf '  被引擎拒 = %s\n' "$(grep -c '被引擎拒' _w2_t5_short_t5G3.log 2>/dev/null)"
echo '  ── 拒绝行（前 4）──'
grep '被引擎拒' _w2_t5_short_t5G3.log 2>/dev/null | head -4 | cut -c1-118 | sed 's/^/     /'
echo
echo '── ★ series 的 nslab_n（决定性：能否 > 4）──'
$PY - <<'PYEOF'
import csv, os
p = '_exp/_bk_t5/dry_t5G3/series.csv'
if not os.path.exists(p):
    print('  ⏳ 还没有 series.csv（构造期未过或刚开始）')
else:
    r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    print('  %d 行：' % len(r))
    for x in r[-6:]:
        print('     step %-5s nslab_n=%-4s nf3=%-7s nblk=%-4s Vt=%s'
              % (x['step'], (x.get('nslab_n') or '')[:4], (x.get('nf3') or '')[:7],
                 (x.get('nblk_sig') or '')[:4], x['Vt'][:14]))
    ns = [(x['step'], x.get('nslab_n')) for x in r if (x.get('nslab_n') or '').strip()]
    print('  nslab_n 轨迹: %s' % ns[:10])
PYEOF
echo
free -m | sed -n 2p | sed 's/^/  /'
