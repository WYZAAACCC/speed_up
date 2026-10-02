#!/bin/bash
# _t5_df_audit.sh --- ★ ① 纠正 wall_s 量具错  ② 逐行核对"驱动力是否随温度变"
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① 纠正：wall_s 是**累计列**，总量 = 末行值（不是求和）════'
$PY - <<'PYEOF'
import csv
d = '_exp/_bk_mb/dry_abA/series.csv'
rows = list(csv.DictReader(open(d, encoding='utf-8', errors='replace')))
w = [(r['step'], float(r['wall_s'])) for r in rows if r.get('wall_s') not in (None, '')]
print('  行数 %d ；wall_s 首 = %.0f s ；**末 = %.0f s = %.2f h**'
      % (len(w), w[0][1], w[-1][1], w[-1][1]/3600))
print('  ⚠ 我先前"求和 = 1064.67 h"是**错的**（把累计列当增量列）')
print('  ⇒ 这个量级（%.1f h）才是 N=112 / 5922 步的真实历时参考' % (w[-1][1]/3600))
print('  ⇒ 单步均时 = %.2f s/步（末值 / 步数）' % (w[-1][1]/max(int(w[-1][0]), 1)))
PYEOF
echo
echo '════ ② ★ 驱动力随温度：逐行核对（用户点名）════'
echo '  ── `dG_of_T` / `T_of_t` 的定义 ──'
grep -n 'dG_of_T\|T_of_t' _bk_exp.py 2>/dev/null | head -12 | cut -c1-120 | sed 's/^/    /'
echo
echo '  ── `windowB_surface.py` 里 df 的更新点（前后 22 行）──'
sed -n '3715,3748p' windowB_surface.py | cat -n | sed 's/^/    /' | cut -c1-120
echo
echo '  ── 调用 `advance_T` 的地方（每步都调吗）──'
grep -n 'advance_T\|advance(' _bk_exp.py 2>/dev/null | head -12 | cut -c1-120 | sed 's/^/    /'
echo
echo '════ ③ 用户点名的"线性降温占位"（S14/N2）到底在哪 ════'
grep -n 'linear_cool\|占位' windowB_surface.py 2>/dev/null | head -12 | cut -c1-120 | sed 's/^/    /'
grep -n 'linear_cool' _bk_exp.py 2>/dev/null | head -8 | cut -c1-120 | sed 's/^/    /'
