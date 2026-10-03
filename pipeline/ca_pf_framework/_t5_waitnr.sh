#!/bin/bash
# _t5_waitnr.sh --- 等 `t5NR` 出现**第一个块表点**（nblk_sig 非空），然后打印两臂对照
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LIM=${1:-1500}
T=0
while [ "$T" -lt "$LIM" ]; do
  N=$(awk -F, 'NR==1{for(i=1;i<=NF;i++) if($i=="nblk_sig") c=i; next} $c!=""{n++} END{print n+0}' \
      _exp/_bk_t5/dry_t5NR/series.csv 2>/dev/null)
  if [ "$N" -ge 2 ]; then echo "  ★ t5NR 已有 $N 个块表点"; break; fi
  A=$(ps -eo args --no-headers 2>/dev/null | awk '/--tag t5NR/{n++} END{print n+0}')
  [ "$A" -eq 0 ] && { echo "  ⚠ t5NR 进程消失"; break; }
  sleep 30; T=$((T + 30))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
echo '════ ★ 两臂块表对照（**唯一变量 = --var-rule**）════'
$PY - <<'PYEOF'
import csv, os
def rows(t):
    p = '_exp/_bk_t5/dry_%s/series.csv' % t
    return list(csv.DictReader(open(p, newline=''))) if os.path.exists(p) else []
print('  %-10s %-7s %-8s %-7s %-5s %-9s %-10s %s'
      % ('臂', 'step', 'nslab_n', 'nf3_col', 'nf2', 'nblk_sig', 'n_var_sig', 'blk_laths'))
print('  ' + '-' * 78)
for t in ('t5N276', 't5NR'):
    for r in rows(t):
        if (r.get('nblk_sig') or '').strip():
            print('  %-10s %-7s %-8s %-7s %-5s %-9s %-10s %s'
                  % (t, r['step'], r.get('nslab_n'), r.get('nf3_col'),
                     (r.get('nf2') or '').strip(), (r.get('nblk_sig') or '').strip(),
                     (r.get('n_var_sig') or '').strip(), (r.get('blk_laths') or '')[:10]))
print()
print('  ── 判据（预先写死）──')
print('  * 若 `t5NR`（random）出现 **n_var_sig > 1** 而 `t5N276`（ed）恒 = 1')
print('    ⇒ **`--var-rule` 是"多变体/多块"的决定因素**（因果归因确定）;')
print('  * 进一步，若 `t5NR` 出现 **nf2 > 0** ⇒ **④ 块间相互影响达成**。')
PYEOF
