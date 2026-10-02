#!/bin/bash
# _t5_chk68.sh --- 第 68 轮：验证 `--therm-hist` 接线（**默认档必须仍是 linear**）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo '════ ① 语法 ════'
$PY -m py_compile _bk_exp.py && echo '  ✅ _bk_exp.py SYNTAX_OK（真跑过）'
$PY -m py_compile _t5_therm.py && echo '  ✅ _t5_therm.py SYNTAX_OK'
echo
echo '════ ② ★ 默认档必须是 linear（判据：不传 --therm-hist 时 default=linear）════'
$PY - <<'PYEOF'
import re
src = open('_bk_exp.py', encoding='utf-8').read()
m = re.search(r"add_argument\('--therm-hist',\s*default='(\w+)'", src)
print('  argparse 的 default = **%s**  ⇒ %s'
      % (m.group(1) if m else '（没找到！）',
         'PASS ✅' if (m and m.group(1) == 'linear') else 'FAIL ❌'))
# 分派点也必须"默认走原路"
i = src.find("if str(getattr(a, 'therm_hist', 'linear')) == 'lpbf':")
print('  分派点存在 = %s' % (i > 0))
j = src.find("            _T_of_t = KM.linear_cool(_Tstart, _Tend, (_Tstart - _Tend) / _q)\n        _dG_of_T",
             i)
print('  `else` 分支里仍是**原来那一行**（逐字） = %s' % (j > 0))
PYEOF
echo
echo '════ ③ 长跑未受影响（其命令行里没有 --therm-hist ⇒ 走默认 linear）════'
printf '  t5H3 进程仍在: %s\n' "$(ps -eo args --no-headers 2>/dev/null | grep -c '[_]bk_exp.py')"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "    pid=%s 已跑=%s\n", $1, $2}'
