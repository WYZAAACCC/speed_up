#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r724_lit_kinetics.py —— **S6 的文献检索**：在本机 217 篇抽取文本里找
Ti64 α′ 的**界面迁移速度 `v(T)`** 与**生长激活能 `Q_G`**。

## 为什么是 S6
`R712 §6.2` 的"生长是否限制环节"判据
```
v(T) = v(1100K)·exp[−(Q_G/R)(1/T − 1/1100)]
Π = n·(v/q)³  ≫ 1   ⇔   instantaneous growth 成立
```
**现有 `Q_G = 8.2 kJ/mol` 与 `v(1100K) = 4.1e-4 m/s` 都是 Fe–0.7at%Al 的**（`R712 §11.2` 未决项 1）。
⇒ **Ti64 无同类实测** ⇒ 本脚本去**实测这个"有没有"**，并**如实登记缺口**。

## 口径（**先写死，避免"搜到就算有"**）
| 类别 | 接受为命中的词 |
|---|---|
| 速度 | `interface velocity` / `growth velocity` / `migration velocity` / `growth rate` + 单位 `m/s` |
| 激活能 | `activation energy` + (`growth` / `migration` / `interface`) + 单位 `kJ/mol` / `eV` |
| **必须同时** | 文中出现 Ti 合金语境（`Ti-6Al-4V` / `Ti64` / `Ti–6Al–4V`） |

⚠ **只在"Ti64 语境"的命中才计入结论** —— 别的合金只作对照（`R712 §0.3` 的 E7 教训：
跨合金拟合曾给出 `Q_G = −5.1 kJ/mol` 却写"吻合 162%"）。

## 用法
    python3 _r724_lit_kinetics.py [--dir _litidx/lit_txt_all] [--all-alloys]
"""
import argparse
import os
import re
import sys

PAT_VEL = re.compile(r'(interface|growth|migration|advance|front)\s+(velocity|speed|rate)', re.I)
PAT_VEL_UNIT = re.compile(r'(m\s*/\s*s|m\s*s\s*(?:−|-|\^)?1|ms−1|ms-1)', re.I)
PAT_Q = re.compile(r'activation\s+energy', re.I)
PAT_QWORD = re.compile(r'(growth|migration|interface|boundary|diffus)', re.I)
PAT_QUNIT = re.compile(r'(kJ\s*/?\s*mol|kJ\s*mol|eV\b)', re.I)
PAT_TI64 = re.compile(r'(Ti\s*[-–—]?\s*6\s*Al\s*[-–—]?\s*4\s*V|Ti64|Ti-6Al-4V)', re.I)
PAT_MART = re.compile(r'(martensit|α\s*[\'′]|alpha\s*prime|acicular)', re.I)


def scan(path):
    try:
        txt = open(path, encoding='utf-8', errors='ignore').read()
    except OSError:
        return None
    lines = txt.split('\n')
    vel, q, ti = [], [], []
    for i, ln in enumerate(lines):
        if PAT_VEL.search(ln) and PAT_VEL_UNIT.search(ln):
            vel.append((i + 1, ln.strip()[:200]))
        if PAT_Q.search(ln) and PAT_QWORD.search(ln) and PAT_QUNIT.search(ln):
            q.append((i + 1, ln.strip()[:200]))
        if PAT_TI64.search(ln):
            ti.append(i + 1)
    return dict(n_lines=len(lines), ti_lines=ti, vel=vel, q=q,
                mart=bool(PAT_MART.search(txt)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='_litidx/lit_txt_all')
    ap.add_argument('--max-show', type=int, default=6)
    a = ap.parse_args()
    if not os.path.isdir(a.dir):
        print('⛔ 目录不存在：%s' % a.dir)
        return 1
    files = sorted(f for f in os.listdir(a.dir) if f.endswith('.txt'))
    print('=' * 104)
    print('S6 文献检索：`v(T)` 与 `Q_G`（目录 %s，%d 篇）' % (a.dir, len(files)))
    print('=' * 104)
    hits_ti_vel, hits_ti_q, hits_other_q = [], [], []
    for f in files:
        r = scan(os.path.join(a.dir, f))
        if r is None:
            continue
        is_ti = len(r['ti_lines']) > 0
        if is_ti and r['vel']:
            hits_ti_vel.append((f, r))
        if r['q']:
            (hits_ti_q if is_ti else hits_other_q).append((f, r))

    print('\n## 1) **Ti64 语境**下同时出现"界面速度 + 单位"的文献：**%d 篇**'
          % len(hits_ti_vel))
    for f, r in hits_ti_vel[:a.max_show]:
        print('\n  【%s】' % f[:88])
        print('     出现 Ti64 的行数 = %d；martensite/α′ 语境 = %s'
              % (len(r['ti_lines']), r['mart']))
        for ln, t in r['vel'][:3]:
            print('       L%-6d %s' % (ln, t))

    print('\n## 2) **Ti64 语境**下同时出现"激活能 + 生长/迁移/扩散 + 单位"的文献：**%d 篇**'
          % len(hits_ti_q))
    for f, r in hits_ti_q[:a.max_show]:
        print('\n  【%s】' % f[:88])
        for ln, t in r['q'][:3]:
            print('       L%-6d %s' % (ln, t))

    print('\n## 3) 非 Ti64 语境但含激活能的文献（**只作对照，不入结论**）：%d 篇'
          % len(hits_other_q))
    for f, _ in hits_other_q[:8]:
        print('   - %s' % f[:92])

    print('\n' + '=' * 104)
    print('⇒ **判定（`R712 §11.2` 未决项 1）**：Ti64 语境的界面速度命中 **%d** 篇、'
          '激活能命中 **%d** 篇' % (len(hits_ti_vel), len(hits_ti_q)))
    if not hits_ti_vel and not hits_ti_q:
        print('   ⛔ **本机文献库无 Ti64 α′ 的 `v(T)`/`Q_G` 实测** ⇒ '
              '`R712 §6.2` 的 `Π` 判据**仍只能用 Fe–Al 值示意**')
        print('   ⇒ 缺口**如实登记**，不外推、不拟合（`R712 §0.3` 的 E7 教训）')
    else:
        print('   ⚠ 有命中 ⇒ **须逐条读上下文确认是不是"界面迁移"的激活能**'
              '（形核势垒/蠕变/扩散的激活能都在同一个正则里）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
