#!/usr/bin/env python3
"""_r454_fixscope.py —— **"参数化 + 两个框架缺口"能不能修、代价多大**（先核实事实）。"""
import re

P = print
P('=' * 92)
P('_r454 —— 可修性核查')
P('=' * 92)

src = open('windowB_surface.py', encoding='utf-8').read()
exp = open('_bk_exp.py', encoding='utf-8').read()
clo = open('windowB_closure.py', encoding='utf-8').read()

# ---- 1) beta_h 是否随温度更新？
P('\n[1] `beta_h` 会不会随温度更新？')
code_lines = [ln for ln in src.splitlines()
              if 'mob_beta' in ln and not ln.lstrip().startswith('#')]
P('    `mob_beta` 在**代码**里出现 %d 行：' % len(code_lines))
for ln in code_lines[:8]:
    P('      %s' % ln.strip()[:100])
# set_T 里有没有动它
m = re.search(r'def set_T\(.*?\n(.*?)\ndef ', src, re.S)
body = m.group(1) if m else ''
P('    `set_T()` 的函数体里有没有 `mob_beta`/`beta`：%s'
  % ('有' if ('mob_beta' in body or 'beta' in body) else '**没有**'))
P('    ⇒ 结论：`beta_h` 是**常数**（建对象时定死），**不随温度更新**')

# ---- 2) 框架自带的温度形式接线了没？
P('\n[2] 框架自带的温度形式接线了没？')
for fn in ('beta_h_of_T', 'beta_h_run_average', 'beta_h_min'):
    P('    `%s`：`windowB_closure` 里%s；`_bk_exp.py` 里%s'
      % (fn,
         '有定义' if ('def %s' % fn) in clo else '**无**',
         '有调用' if fn in exp else '**无调用**'))

# ---- 3) 临界核判据的现状
P('\n[3] 临界核判据')
P('    `use_fcrit` 在 `_bk_exp.py` 的调用：%s'
  % ('有' if 'use_fcrit=bool' in exp else '**无**'))
P('    `fcrit` 的表达式（`windowB_surface`）：')
for ln in src.splitlines():
    if 'fcrit =' in ln and not ln.lstrip().startswith('#'):
        P('      %s' % ln.strip()[:100])

# ---- 4) 面内分割 / 块数律
P('\n[4] 块数律（面内分割）')
for kw in ('面内', 'Voronoi', 'in-plane', 'areal', 'N_A'):
    hits = [ln.strip()[:90] for ln in clo.splitlines()
            if kw in ln and not ln.lstrip().startswith('#')]
    P('    `%s`：代码里 %d 处' % (kw, len(hits)))
    for h in hits[:2]:
        P('       %s' % h)

# ---- 5) limitations() 自陈
P('\n[5] `limitations()` 自陈的局限条数')
m2 = re.search(r'def limitations\(\):(.*?)\n\ndef ', clo, re.S)
if m2:
    n = len(re.findall(r"^\s+'", m2.group(1), re.M))
    P('    共 **%d** 条' % n)
P('=' * 92)
