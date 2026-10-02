#!/bin/bash
# _t5_freshdiag.sh --- §111 方案②：短诊断臂（小 K）取 `fresh_*` 归因计数
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ 语法 ════'
$PY -m py_compile _t5_short.py && echo '  ✅ SYNTAX_OK（真跑过）'
echo
echo '════ ★ 默认档必须"不传"该参数（判据：归档路径逐字不变）════'
$PY - <<'PYEOF'
import importlib.util as u, sys
src = open('_t5_short.py', encoding='utf-8').read()
ok = "if int(getattr(a, 'nuc_fresh_every', 0) or 0) > 0 else []" in src
print('  透传的守卫条件存在 = %s  ⇒ %s' % (ok, 'PASS ✅' if ok else 'FAIL ❌'))
print('  默认值 = 0  ⇒ 默认**一个参数都不传** ⇒ 长跑/归档逐字不变')
PYEOF
echo
echo '════ 短诊断臂：N=96 / 200 步 / --nuc-fresh-every 2（让它更快尝试 fresh）════'
$PY _t5_short.py --tag t5fd --N 96 --nvar 12 --m 6 --B 3 --steps 200 \
   --cores 16-19 --mem-limit-gb 4.0 --every 20 --snap-every 200 --pair-every 50 \
   --ckpt-every 100 --overlap-nm 62.5 --nuc-fresh-every 2 --archive-old \
   > _w2_t5_fd_A.log 2>&1
echo "  exit=$?"
echo
echo '════ ★ 模式分布（这是要看的）════'
grep -oE '模式 \*\*[a-z]+\*\*' _w2_t5_short_t5fd.log 2>/dev/null | sort | uniq -c | sed 's/^/  /'
echo '  ── fresh 被拒的行 ──'
grep -nE 'fresh` 被拒|fresh.*拒' _w2_t5_short_t5fd.log 2>/dev/null | head -5 | cut -c1-140 | sed 's/^/  /'
echo
echo '════ ★ `nuc_dbg.json`（跑完才写，这是归因计数的来源）════'
J=_exp/_bk_t5/dry_t5fd/nuc_dbg.json
if [ -f "$J" ]; then
  $PY - "$J" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
dbg = d.get('dbg', {}) or {}
print('  ── dbg 里与 fresh 有关的计数 ──')
for k in sorted(dbg):
    if 'fresh' in k.lower() or 'nofield' in k.lower() or 'cov' in k.lower() or 'exc' in k.lower() \
       or k in ('ok','oob','nocand','att','attach_ok'):
        print('     %-22s = %s' % (k, dbg[k]))
print('  ── 其它顶层键 ──')
for k in ('n_fresh_fallback_to_stack','n_events_by_mode','n_eng_ev','n_athermal_ev'):
    if k in d:
        print('     %-26s = %s' % (k, d[k]))
PYEOF
else
  echo "  ⚠ $J 不存在"
fi
