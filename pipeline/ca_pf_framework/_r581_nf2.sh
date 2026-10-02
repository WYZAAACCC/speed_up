#!/bin/bash
# _r581_nf2.sh --- ★★★★★ 量 F/G 的 **F2 面积**（`limitations()` 第 6 条：归档算例里它为 0、从未被检验）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── series.csv 的列名（找 nf2 / nf3 / nslab）──'
H=_exp/_bk_mn64/dry_F/series.csv
head -1 "$H" 2>/dev/null | tr ',' '\n' | cat -n | grep -iE "nf2|nf3|nslab|f2|f3" | sed 's/^/  /'
echo
echo '── 各臂末行的 nf2 / nf3 / nslab（按列号取）──'
python3 - <<'PYEOF' 2>/dev/null || /root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv, os
ROOT = '_exp/_bk_mn64'
for t in ('A', 'B', 'C', 'D', 'E', 'F', 'G'):
    p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    if not rows:
        continue
    hdr = list(rows[0].keys())
    cand = [k for k in hdr if any(s in k.lower() for s in ('nf2', 'nf3', 'nslab', 'f2_', 'f3_'))]
    last = rows[-1]
    step = last.get(hdr[0], '?')
    vals = {k: last.get(k, '?') for k in cand}
    print('  %-4s step=%-6s %s' % (t, step, vals))
PYEOF
echo
echo '── 若上面没有 nf2 列，就直接从快照算（3-D 接触面）──'
echo '  （下一步用 _r581_c6judge.py 那类判据；此处先看列名）'
