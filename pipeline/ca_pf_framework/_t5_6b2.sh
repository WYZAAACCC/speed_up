#!/bin/bash
# _t5_6b2.sh --- 重跑 6b（修好 argparse 之后）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ 语法 ════'
$PY -m py_compile _t5_short.py && echo '  ✅ SYNTAX_OK（真跑过）'
echo
echo '════ 6b 重跑：`--therm-hist lpbf`（N=96 / 40 步）════'
$PY _t5_short.py --tag t6b --N 96 --nvar 12 --m 6 --B 3 --steps 40 \
   --cores 16-19 --mem-limit-gb 4.0 --every 20 --snap-every 200 --pair-every 50 \
   --ckpt-every 40 --overlap-nm 62.5 --therm-hist lpbf --archive-old \
   > _w2_t5_6b_A.log 2>&1
RC=$?
echo "  6b exit=$RC"
echo
echo '════ 横幅（判据 6b）════'
grep -E '热史档|band|峰值|回退|T: ' _w2_t5_short_t6b.log 2>/dev/null | head -8 | cut -c1-130 | sed 's/^/  /'
echo
$PY - <<'PYEOF'
import os, re
p = '_w2_t5_short_t6b.log'
s = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''
ok_lpbf = bool(re.search(r'热史档 = .lpbf', s))
ok_nofb = not bool(re.search(r'回退到 linear', s))
print('  判据 6b-①「出现 lpbf 横幅」      = %s  ⇒ %s'
      % (ok_lpbf, 'PASS ✅' if ok_lpbf else 'FAIL ❌'))
print('  判据 6b-②「未回退到 linear」     = %s  ⇒ %s'
      % (ok_nofb, 'PASS ✅' if ok_nofb else 'FAIL ❌'))
m = re.search(r'峰值 \(([^)]*)\)', s) or re.search(r'峰值 (\[[^\]]*\]|\S+)', s)
print('  峰值序列（应 5 个、且 C1/C2=1923、C5 在 (763, 873)）= %s'
      % (m.group(1) if m else '（没找到）'))
PYEOF
