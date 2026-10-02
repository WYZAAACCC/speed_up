#!/bin/bash
# _r581_s4verdict.sh --- ★★★★★ **S4 的终态判决**：`p2_b5ov`（S4 开）vs `p2_b5`（S4 关）
#   ⚠ 写成脚本再跑（嵌套引号在 PowerShell→WSL 里会被拆坏）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo
echo '── 各臂的**末态**读数（从 series.csv 的最后一行读）──'
for t in p2_b5 p2_b3 p2_b5ov p2_b5ps p2_m12 p2_m12b p2_m20 p2_m12ov; do
  f="_exp/_bk_p2/dry_${t}/series.csv"
  if [ -f "$f" ]; then
    n=$(wc -l < "$f")
    printf '  %-12s 行数=%-6s 末行：%s\n' "$t" "$n" "$(tail -1 "$f" | cut -c1-150)"
  else
    printf '  %-12s （无 series.csv）\n' "$t"
  fi
done
echo
echo '── 末态 step / Vt（用 python 稳妥解析表头）──'
$PY - <<'PYEOF'
import csv, os
ROOT = '_exp/_bk_p2'
TAGS = ['p2_b5', 'p2_b3', 'p2_b5ov', 'p2_b5ps', 'p2_m12', 'p2_m12b', 'p2_m20', 'p2_m12ov']
print(' %-12s %-8s %-12s %-12s %-12s %s' % ('tag', '末step', 'Vt', 'nslab_n', 'nf3_col', '备注'))
print(' ' + '-' * 88)
for t in TAGS:
    p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p, encoding='utf-8')))
    if not rows:
        continue
    r = rows[-1]
    def g(*names):
        for n in names:
            for k in r:
                if k and k.strip().lower() == n.lower():
                    return r[k]
        return '?'
    print(' %-12s %-8s %-12s %-12s %-12s %s'
          % (t, g('step'), g('Vt'), g('nslab_n'), g('nf3_col'),
             'S4=' + ('开' if t.endswith('ov') else '关')))
PYEOF
echo
echo '★ 判据（**预先写死**）：S4 开的末态 `Vt` 若明显 > S4 关的 ⇒ S4 有效（且给出倍数）'
