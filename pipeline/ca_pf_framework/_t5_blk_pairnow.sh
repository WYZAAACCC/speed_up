#!/bin/bash
# _t5_blk_pairnow.sh --- `_pair_now` 的定义 + abA 实际跑的命令行
cd "$(dirname "$0")" || exit 1
echo '════ ① `_pair_now` 的定义 ════'
grep -n '_pair_now *=' _bk_exp.py | cut -c1-130 | sed 's/^/  /'
echo
echo '  ── 前后 12 行 ──'
LN=$(grep -n '_pair_now *=' _bk_exp.py | head -1 | cut -d: -f1)
sed -n "$((LN-8)),$((LN+5))p" _bk_exp.py | cut -c1-126 | sed 's/^/    /'
echo
echo '════ ② abA 日志里的**实际命令行**（meta 可能与实际不符）════'
for f in _r445_abA.log _r426_abA.log; do
  [ -f "$f" ] || continue
  echo "  ── $f ──"
  grep -oE '\-\-pair-every [0-9]+|\-\-every [0-9]+|\-\-snap-every [0-9]+|\-\-N [0-9]+' "$f" 2>/dev/null \
    | sort -u | head -8 | sed 's/^/     /'
  grep -n 'pair_every\|pair-every' "$f" 2>/dev/null | head -5 | cut -c1-120 | sed 's/^/     /'
done
echo
echo '════ ③ abA 的 meta.json 里 pair_every 到底是几 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import json
m = json.load(open('_exp/_bk_mb/dry_abA/meta.json', encoding='utf-8'))
a = m.get('exp_args', m)
for k in ('pair_every', 'every', 'snap_every', 'N', 'steps'):
    print('  %-12s = %r' % (k, a.get(k)))
PYEOF
echo
echo '════ ④ ★ 直接数：abA 的 series 里，pair_every 命中步是否**恰好**也是 CSV 行步 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import csv
rows = list(csv.DictReader(open('_exp/_bk_mb/dry_abA/series.csv',
                                encoding='utf-8', errors='replace')))
steps = [int(r['step']) for r in rows]
print('  CSV 行步：前 8 = %s … 共 %d 行' % (steps[:8], len(steps)))
print('  step %% 20 == 0 的行数 = %d / %d'
      % (sum(1 for s in steps if s % 20 == 0), len(steps)))
blk = set((r.get('nblk_sig') or '').strip() for r in rows)
print('  nblk_sig 全部取值 = %r' % sorted(blk)[:8])
PYEOF
