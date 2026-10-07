#!/bin/bash
# _r419_wire.sh —— §186/§187 修复的**接线自检**（不跑仿真，只验语法与开关）
# ⚠ 自纠错：第一版在双引号 echo 里用了反引号 ⇒ bash 当命令替换执行，
#   刷出一堆 "command not found"（**这是本脚本的排版 bug，不是代码 bug**）。
#   本版**一律不用反引号**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python

echo "======== 1) 语法编译 ========"
"$PY" -m py_compile _bk_exp.py windowB_surface.py _r68_facet_op.py \
  && echo "  [OK] 三个文件编译通过"

echo
echo "======== 2) --facet-excl 已在 CLI 里（默认值必须是 0） ========"
"$PY" - <<'PYEOF'
import ast, sys
tree = ast.parse(open('_bk_exp.py', encoding='utf-8').read())
found = False
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'add_argument':
        if node.args and isinstance(node.args[0], ast.Constant) \
                and node.args[0].value == '--facet-excl':
            kw = {k.arg: k.value for k in node.keywords}
            d = getattr(kw.get('default'), 'value', None)
            print('  找到 --facet-excl：default = %r' % (d,))
            print('  ⇒ 默认值判定：%s' % ('[OK] 0（修好的行为）' if d == 0
                                          else '[FAIL] 不是 0！'))
            found = True
if not found:
    print('  [FAIL] 没找到 --facet-excl')
    sys.exit(1)
PYEOF

echo
echo "======== 3) facet_project() 真的读了该属性（含默认 0） ========"
grep -n "facet_excl" windowB_surface.py _bk_exp.py

echo
echo "======== 4) facet_excl 没有混进传给 advance(**kw) 的 kw ========"
"$PY" - <<'PYEOF'
import ast, sys
tree = ast.parse(open('_bk_exp.py', encoding='utf-8').read())
bad = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'kw' \
                    and isinstance(node.value, ast.Call):
                for k in node.value.keywords:
                    if k.arg == 'facet_excl':
                        bad.append(k.lineno)
print('  kw=dict(...) 里出现 facet_excl 的行号：%s' % (bad or '无'))
print('  ⇒ %s' % ('[OK] 干净（不会 TypeError）' if not bad
                  else '[FAIL] 又混进去了！'))
sys.exit(1 if bad else 0)
PYEOF

echo
echo "======== 5) 引擎侧 advance() 的形参里没有 facet_excl（佐证 4） ========"
"$PY" - <<'PYEOF'
import ast
tree = ast.parse(open('windowB_surface.py', encoding='utf-8').read())
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'advance':
        names = [a.arg for a in node.args.args]
        names += [a.arg for a in node.args.kwonlyargs]
        print('  advance() 的形参：%s' % ', '.join(names))
        print('  facet_excl 在其中？ %s'
              % ('[FAIL] 是' if 'facet_excl' in names
                 else '[OK] 否 —— 所以若把它放进 kw 必然 TypeError（这正是 #51）'))
        break
PYEOF
echo
echo "======== 6) 回归用的开关组合里不含 --facet-proj ========"
if grep -q -- '--facet-proj' _r30_regress.sh; then
  echo "  [WARN] 回归脚本里出现了 --facet-proj —— 需重查逐位不变性"
else
  echo "  [OK] 回归不带 --facet-proj ⇒ facet_project() 一次都不被调用 ⇒ 逐位不变"
fi
