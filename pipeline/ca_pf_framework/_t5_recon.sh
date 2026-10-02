#!/bin/bash
# _t5_recon.sh --- 实验(5) 的侦察：基线 abA / 任务(5) 定义 / 已有简化审计
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① abA 在哪 ════'
for d in $(ls -d _exp/*/dry_abA _exp/*/*/dry_abA 2>/dev/null | head -6); do
  echo "  $d"
  ls -la "$d" 2>/dev/null | head -6 | sed 's/^/      /'
done
echo
echo '════ ② abA 的 meta.json（完整命令行 = 实验(5) 的物理基线）════'
for d in $(ls -d _exp/*/dry_abA _exp/*/*/dry_abA 2>/dev/null | head -3); do
  echo "  ── $d/meta.json ──"
  /root/miniconda3/envs/ml/bin/python - "$d/meta.json" <<'PYEOF' 2>/dev/null
import json, sys, textwrap
try:
    m = json.load(open(sys.argv[1], encoding='utf-8'))
except Exception as e:
    print('    ⚠ 读不到：%s' % e); raise SystemExit
print('    顶层键：%s' % list(m)[:14])
a = m.get('exp_args') or m.get('args') or {}
if isinstance(a, dict):
    for k in sorted(a):
        v = a[k]
        if v in (None, '', False, 0, 0.0, [], {}):
            continue
        print('      %-22s = %s' % (k, str(v)[:84]))
PYEOF
done
echo
echo '════ ③ "任务(5)" 的定义 ════'
ls -la R581_TASK5_*.md 2>/dev/null | sed 's/^/  /'
for f in R581_TASK5_VERDICT.md R581_TASK5_INTERIM.md; do
  [ -f "$f" ] || continue
  echo "  ── $f（前 40 行）──"
  head -40 "$f" | sed 's/^/    /'
done
echo
echo '════ ④ 已有的简化审计文档 ════'
ls -la R581_SIMPLIFICATION_AUDIT.md 2>/dev/null | sed 's/^/  /'
[ -f R581_SIMPLIFICATION_AUDIT.md ] && grep -n '^#' R581_SIMPLIFICATION_AUDIT.md | head -30 | sed 's/^/    /'
