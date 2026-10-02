#!/bin/bash
# _t5_alphakm.sh --- 查清 alpha_km 的口径：abA 的 0.041739 vs p2 的 0.011
cd "$(dirname "$0")" || exit 1
echo '════ ① alpha_km 在代码里的定义与用法 ════'
grep -n 'alpha_km\|alpha-km' _bk_exp.py 2>/dev/null | head -22 | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ② N8 的"自动取 K"逻辑（注释说 686 行）════'
sed -n '676,700p' _bk_exp.py 2>/dev/null | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ③ 引擎侧：athermal 律怎么用 alpha_km ════'
grep -n 'alpha_km\|T_of_k\|n_target' windowB_surface.py windowB_km.py 2>/dev/null | head -18 | cut -c1-132 | sed 's/^/  /'
echo
echo '════ ④ abA 的 nuc_fresh_every / K 相关字段 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import json
m = json.load(open('_exp/_bk_mb/dry_abA/meta.json', encoding='utf-8'))
a = m.get('exp_args', m)
for k in sorted(a):
    if any(s in k for s in ('alpha', 'fresh', 'block', 'nuc', 'K', 'k_')):
        print('  %-24s = %r' % (k, a[k]))
PYEOF
echo
echo '════ ⑤ abA 日志里 alpha_km / K 的**实际生效值** ════'
for f in _r445_abA.log _r426_abA.log; do
  [ -f "$f" ] || continue
  echo "  ── $f ──"
  grep -nE 'alpha_km|α_KM|自动取|K *=|n_target|athermal 形核律' "$f" 2>/dev/null | head -8 | cut -c1-130 | sed 's/^/     /'
done
