#!/bin/bash
# _r581_nucdiag.sh --- ★★★★★ 诊断：**负对照 2/3 为什么没 FAIL**
#   —— 先查"这一轮到底有没有**消耗 RNG**、有没有**走到 reinit 节拍**"
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
for L in _w2_r581_rsmoke_rs3.log _w2_r581_rsmoke_rs2.log _w2_r581_neg_nc_neg2.log \
         _w2_r581_neg_nc_neg3.log; do
  [ -f "$L" ] || continue
  echo "════ $L ════"
  printf '  形核事件行数（任意写法）= %s\n' \
    "$(grep -cE '形核|nucleat|n_eng_ev' "$L" 2>/dev/null || echo 0)"
  printf '  reinit 相关行数         = %s\n' \
    "$(grep -ciE 'reinit|重新初始化' "$L" 2>/dev/null || echo 0)"
  printf '  `n_eng_ev=` 末值         = %s\n' \
    "$(grep -oE 'n_eng_ev=[0-9]+' "$L" 2>/dev/null | tail -1)"
  printf '  `n_act`/`nslab` 末值     = %s\n' \
    "$(grep -oE 'nslab=[0-9]+' "$L" 2>/dev/null | tail -1)"
  echo '  ── 含"形核"的行（前 4，任何位置）──'
  grep -n '形核' "$L" 2>/dev/null | head -4 | cut -c1-116 | sed 's/^/    /'
  echo
done
echo '════ 直方图：各 run 的 series.csv 里 n_eng_ev / n_act 列 ─═══'
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import csv, os
for tag in ('rs3', 'rs2', 'nc_neg2', 'nc_neg3'):
    p = '_exp/_bk_rsmoke/dry_%s/series.csv' % tag
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    if not rows:
        continue
    k = list(rows[0].keys())[0]
    cand = [c for c in rows[0] if 'eng' in c or 'act' in c or 'nuc' in c or c in ('nslab_n', 'nf3')]
    print('  ── %-8s（%d 行）候选列：%s' % (tag, len(rows), cand[:8]))
    for c in cand[:5]:
        vals = [(r[k], (r.get(c) or '').strip()) for r in rows]
        nz = [v for v in vals if v[1] not in ('', '0', '0.0')]
        print('     %-16s 非零 %2d/%2d 处；最后几个：%s'
              % (c, len(nz), len(vals), nz[-4:]))
PYEOF
