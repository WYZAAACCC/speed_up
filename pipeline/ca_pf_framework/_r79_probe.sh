#!/bin/bash
# _r79_probe.sh —— 一次性探测：回归进度 + 已有 MB-2/eng 算例的 `var_rule`
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== 现在 $(date '+%F %T')"
echo "=== 跑着的 _bk_exp 进程数：$(ps -eo args --no-headers | grep -c '[_]bk_exp.py')"
echo "=== 回归产物："
ls -la _exp/_bk_eng/dry_r30reg/series.csv 2>/dev/null || echo "  （还没有 series.csv）"
echo "  日志行数：$(wc -l < _w2_r30_regress.log)"
tail -6 _w2_r30_regress.log
echo
echo "=== 已有 eng/mb2 算例的参数："
for d in eng_mb2 eng_mb2b eng_mb2c eng_mb3 eng_mb3b eng_mb3c eng_mb2_62; do
  [ -f "_exp/_bk_mb/$d/meta.json" ] || { echo "### $d （无 meta）"; continue; }
  $PY - "$d" <<'PY'
import json, sys
d = sys.argv[1]
m = json.load(open('_exp/_bk_mb/%s/meta.json' % d))
e = m.get('exp_args', {})
print('### %-12s var_rule=%-7s nuc_init=%-4s laths=%-28s N=%s dx=%s steps=%s arm=%s'
      % (d, e.get('var_rule'), e.get('nuc_init'), str(e.get('laths')),
         e.get('N'), e.get('dx_nm'), e.get('steps'), e.get('arm')))
PY
done
