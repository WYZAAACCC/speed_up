#!/bin/bash
# _t5_waitstack.sh --- ★★★★★ 等 `t5N276F` 出现**第一个 stack 事件**，判它是否建了新场
#
# ## 为什么这是决定性判据
# 修复前（`t5N276`）：**15 次 stack 全部复用源场** ⇒ 唯一性 0.56、少 15 根板条。
# 修复后（本算例）：**每个 stack 事件的场号应当是**新的**** ⇒ 唯一性应保持 ≈1.0。
#
# ## 判据（**预先写死**）
#   `stack` 事件的 `场 N` 若**此前从未出现** ⇒ **修复生效** ✅
#   若**此前出现过** ⇒ **仍有问题** ❌（要回查）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
L=_w2_t5_short_t5N276F.log
LIM=${1:-2400}
T=0
while [ "$T" -lt "$LIM" ]; do
  if awk '/模式 \*\*stack\*\*/{n++} END{exit !(n>0)}' "$L" 2>/dev/null; then
    echo "  ★ 已出现 stack 事件"; break
  fi
  P=$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -c -- '--tag t5N276F')
  [ "$P" -eq 0 ] && { echo "  ⚠ 引擎进程消失"; break; }
  sleep 20; T=$((T + 20))
done
echo "NOW = $(date '+%F %T')  等了 ${T} s"
echo
$PY - <<'PYEOF'
import re, os
L = '_w2_t5_short_t5N276F.log'
RX = re.compile(r'@ step (\d+)：T=([\d.]+) K.*?场 (\d+)（累计 (\d+)/(\d+)；模式 \*\*([a-z]+)\*\*')
ev = []
if os.path.exists(L):
    for line in open(L, errors='ignore'):
        m = RX.search(line)
        if m:
            ev.append((int(m.group(1)), float(m.group(2)), int(m.group(3)), m.group(6)))
print('  ── 全部形核事件（step / T / 场 / 模式）──')
seen = set()
for st, T, f, md in ev:
    tag = ''
    if f in seen:
        tag = '  ← ⚠ **场已存在（复用）**'
    else:
        seen.add(f); tag = '  ← 新场'
    star = '  ★★' if md == 'stack' else '    '
    print('%s step %-6d T=%-7.1f 场 %-4d 模式 %-7s%s' % (star, st, T, f, md, tag))
print()
n = len(ev); u = len(set(f for _, _, f, _ in ev))
print('  事件 %d ｜ 不同场 %d ｜ **唯一性 = %.2f**（修复前 t5N276 = 0.56）'
      % (n, u, (u / n) if n else 0))
stack_ev = [(st, f) for st, _, f, md in ev if md == 'stack']
print('  stack 事件 = %d 个：%s' % (len(stack_ev), stack_ev[:8]))
print()
print('  ── 判据 ──')
if not stack_ev:
    print('  （还没有 stack 事件 ⇒ 无法判定）')
else:
    # stack 事件的场号是否在它**之前**出现过
    first_seen = {}
    for st, _, f, md in ev:
        first_seen.setdefault(f, st)
    ok = all(first_seen[f] == st for st, f in stack_ev)
    print('  ⇒ **%s**' % ('✅ **每个 stack 都建了新场 ⇒ 修复在真实算例上生效**'
                        if ok else '❌ **有 stack 复用场 ⇒ 仍有问题，需回查**'))
PYEOF
echo
echo '════ 进度 ════'
printf '  t5N276F 末步 = %s ｜ nslab_n = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5N276F/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(tail -1 _exp/_bk_t5/dry_t5N276F/series.csv 2>/dev/null | cut -d, -f9)"
printf '  对照 t5N276（修复前）同期：step 600 时 nslab_n = 17\n'
