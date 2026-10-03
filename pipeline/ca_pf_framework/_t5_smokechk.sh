#!/bin/bash
# _t5_smokechk.sh --- 冒烟测试进度 + **判据②（场号唯一性）** 的实时核算
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5FIX
echo "NOW = $(date '+%F %T')"
printf '  进程 = %s   末步 = %s\n' \
  "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- "--tag $TAG")" \
  "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)"
echo
echo '════ 形核事件（从引擎日志实时抓）════'
grep -E 'athermal 形核|引擎形核' _w2_t5_short_$TAG.log 2>/dev/null | tail -12 | \
  sed -E 's/.*@ step ([0-9]+).*场 ([0-9]+).*模式 \*\*([a-z]+)\*\*.*/  step \1  场 \2  模式 \3/' | sed 's/^/  /'
echo
echo '════ ★ 判据①②：场号唯一性（修复前 t5N276 = 19/34 = 0.56）════'
$PY - <<'PYEOF'
import json, os
from collections import Counter
F = '_exp/_bk_t5/dry_t5FIX/nuc_dbg.json'
if not os.path.exists(F):
    print('  （nuc_dbg.json 还没落盘 —— 引擎跑完才写）')
    raise SystemExit
j = json.load(open(F))
ev = j.get('T_events', [])
if not ev:
    print('  （T_events 为空）'); raise SystemExit
fields = [e['field'] for e in ev]
modes = Counter(e['mode'] for e in ev)
print('  事件数 = **%d**' % len(ev))
print('  不同场号 = **%d**' % len(set(fields)))
print('  ⇒ **唯一性比 = %.2f**（修复前 = 0.56；**修复后应接近 1.0**）'
      % (len(set(fields)) / len(ev)))
print('  模式分布 = %s' % dict(modes))
print()
print('  逐事件（step / 场号 / 模式）：')
seen = set()
for e in ev:
    k = e['field']
    mark = '' if k in seen else '  ← 新场'
    seen.add(k)
    print('     step %-6d 场 %-4d %-7s%s' % (e['step'], k, e['mode'], mark))
print()
print('  ── 判据（**预先写死**）──')
r = len(set(fields)) / len(ev)
print('  * **唯一性 >= 0.9** ⇒ ✅ stack 现在建新场 ⇒ **修复成功**;')
print('  * **0.6 - 0.9** ⇒ ⚠ 部分生效 ⇒ 还有第二处同类缺陷;')
print('  * **< 0.6** ⇒ ❌ 没生效（与修复前同级）⇒ 要重查。')
print('  ⇒ 本次读数：**%.2f** ⇒ %s' % (r, '✅ 成功' if r >= 0.9 else ('⚠ 部分' if r >= 0.6 else '❌ 未生效')))
PYEOF
