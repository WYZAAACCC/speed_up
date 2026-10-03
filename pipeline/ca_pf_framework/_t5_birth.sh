#!/bin/bash
# _t5_birth.py --- ★★★★★ 那些后期新场（10–17, 93）**是怎么诞生的**（哪个通道 + 什么条件）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import re
L = '_w2_t5_short_t5N276.log'
TARGET = {10,11,12,13,14,15,16,17,93}
rows = []
try:
    for line in open(L, errors='ignore'):
        if '形核' in line and '场 ' in line:
            f = re.search(r'场 (\d+)', line)
            if not f: continue
            k = int(f.group(1))
            if k not in TARGET: continue
            st = re.search(r'@ step (\d+)', line)
            T  = re.search(r'T=([\d.]+) K', line)
            Th = re.search(r'T_(\d+) 理论=([\d.]+)', line)
            df = re.search(r'df=([\d.eE+-]+)', line)
            ac = re.search(r'累计 (\d+)/(\d+)', line)
            md = re.search(r'模式 \*\*([a-z]+)\*\*', line)
            rows.append((k, int(st.group(1)) if st else -1, md.group(1) if md else '?',
                         T.group(1) if T else '?', df.group(1) if df else '?',
                         ac.group(0) if ac else '?'))
except FileNotFoundError:
    print('  （无 %s）' % L); raise SystemExit
seen = set(); uniq = []
for r in rows:
    if r[:2] not in seen:
        seen.add(r[:2]); uniq.append(r)
print('=' * 104)
print('★ 后期新场的「诞生记录」（从引擎公告提取）')
print('=' * 104)
print('  %-5s %-9s %-9s %-10s %-14s %s' % ('场', 'step', '**模式**', 'T(K)', 'df', '累计'))
for k, st, md, T, df, ac in sorted(uniq):
    print('  %-5d %-9d **%-8s** %-10s %-14s %s' % (k, st, md, T, df, ac))
print()
print('  ── 判据 ──')
from collections import Counter
c = Counter(md for _, _, md, *_ in uniq)
print('  模式分布：%s' % dict(c))
print('  * `attach` = 接到**已有场**上（同变体、贴近已有板条）;')
print('  * `stack`  = **sympathetic**（同变体、在已有板条附近起新场）;')
print('  * `fresh`  = **新块**（随机位点，变体由 `--var-rule` 决定）。')
PYEOF
