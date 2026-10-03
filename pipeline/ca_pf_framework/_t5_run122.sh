#!/bin/bash
# _t5_run122.sh --- 重跑补丁（锚点已修正）+ 复核 + 长跑未受影响
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
rm -f _t5_short.py.bak_s122
/root/miniconda3/envs/ml/bin/python _t5_patch122.py 2>&1 | head -16
echo
echo '════ 长跑未受影响 ════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
echo
echo '════ ★ 默认档仍"不传"那两个参数（判据）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
src = open('_t5_short.py', encoding='utf-8').read()
g1 = "if str(getattr(a, 'var_rule', 'ed')) != 'ed' else []" in src
g2 = "if int(getattr(a, 'nuc_fresh_every', 0) or 0) > 0 else []" in src
print('  var-rule 的"默认不传"守卫    = %s ⇒ %s' % (g1, 'PASS ✅' if g1 else 'FAIL ❌'))
print('  fresh-every 的"默认不传"守卫 = %s ⇒ %s' % (g2, 'PASS ✅' if g2 else 'FAIL ❌'))
PYEOF
