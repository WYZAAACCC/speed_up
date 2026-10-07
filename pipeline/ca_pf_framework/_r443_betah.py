#!/usr/bin/env python3
"""_r443_betah.py —— `--beta-h` 的**默认值 vs 归档实际用的值**（查配置错误）。"""
import ast
import json
import os

P = print
P('=' * 84)
P('_r443 —— `--beta-h` 口径核对')
P('=' * 84)

# CLI 默认
tree = ast.parse(open('_bk_exp.py', encoding='utf-8').read())
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'add_argument':
        if node.args and isinstance(node.args[0], ast.Constant) \
                and node.args[0].value in ('--beta-h', '--beta-w'):
            kw = {k.arg: getattr(k.value, 'value', None) for k in node.keywords}
            P('  CLI %-10s default = %r' % (node.args[0].value, kw.get('default')))

P('\n  归档/双臂实际用的值（读 meta.json 的 exp_args）：')
base = '_exp/_bk_mb'
names = ['dry_saSet2', 'dry_saSet2P0', 'dry_permB1_400', 'dry_goodA_400',
         'dry_permB4_200', 'dry_permB5_200', 'dry_abA', 'dry_abB']
P('  %-18s %-10s %-10s %s' % ('算例', 'beta_h', 'beta_w', '备注'))
for n in names:
    p = os.path.join(base, n, 'meta.json')
    if not os.path.exists(p):
        P('  %-18s %s' % (n, '✗ 无 meta.json'))
        continue
    m = json.load(open(p))
    ea = m.get('exp_args', {})
    bh = ea.get('beta_h', m.get('beta_h'))
    bw = ea.get('beta_w', m.get('beta_w'))
    note = ''
    if n.startswith('dry_ab'):
        note = '← **本轮双臂**（用了默认）'
    P('  %-18s %-10s %-10s %s' % (n, bh, bw, note))
P('=' * 84)
