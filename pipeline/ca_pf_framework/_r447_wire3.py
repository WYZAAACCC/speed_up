#!/usr/bin/env python3
"""_r447_wire3.py —— `§200`（`--stack-pick-dg`）的**接线自检**（不跑仿真）。"""
import ast
import sys

P = print
P('=' * 82)
P('_r447 —— `--stack-pick-dg` 接线自检')
P('=' * 82)

ok = True

# 1) CLI
tree = ast.parse(open('_bk_exp.py', encoding='utf-8').read())
found = None
for n in ast.walk(tree):
    if isinstance(n, ast.Call) and getattr(n.func, 'attr', '') == 'add_argument':
        if n.args and isinstance(n.args[0], ast.Constant) \
                and n.args[0].value == '--stack-pick-dg':
            found = {k.arg: getattr(k.value, 'value', None) for k in n.keywords}
P('\n[1] CLI 参数：%s' % (found or '❌ 未找到'))
ok &= (found is not None and found.get('default') == 0)
P('    default == 0（归档行为）：%s' % ('✅' if (found or {}).get('default') == 0
                                        else '❌'))

# 2) 驱动 → 引擎
src = open('windowB_surface.py', encoding='utf-8').read()
drv = open('_bk_exp.py', encoding='utf-8').read()
a = 'stack_pick_dg=bool(int(getattr(a, \'stack_pick_dg\', 0)))' in drv
P('\n[2] 驱动把开关传给引擎：%s' % ('✅' if a else '❌'))
ok &= a
b = 'stack_pick_dg=bool(stack_pick_dg)' in src
P('    引擎 `nuc_cfg` 把它存进 `self._nuc`：%s' % ('✅' if b else '❌'))
ok &= b
c = "c.get('stack_pick_dg', False)" in src
P('    stack 通道读取它：%s' % ('✅' if c else '❌'))
ok &= c
d = 'def nuc_cfg(self, R_nuc, t_nuc, gamma=0.15, n_init=0, p_auto=0.0,' in src \
    and 'stack_pick_dg=False,' in src
P('    形参有默认 `False`：%s' % ('✅' if d else '❌'))
ok &= d

# 3) 惰性：默认分支必须**逐字**是原来那一行
e = src.count('k = int(ks[rng.integers(0, len(ks))])')
P('\n[3] 原写法 `k = int(ks[rng.integers(0, len(ks))])` 出现 %d 次' % e)
P('    （dG 分支内 2 处回退 + 默认分支 1 处 = 3 次为正常）')
ok &= (e >= 3)
f = 'if c.get(\'stack_pick_dg\', False) and not hardened:' in src
P('    dG 分支有 `not hardened` 门控：%s' % ('✅' if f else '❌'))
ok &= f

P('\n' + '=' * 82)
P('总判定：%s' % ('✅ PASS' if ok else '❌ FAIL'))
P('=' * 82)
sys.exit(0 if ok else 1)
