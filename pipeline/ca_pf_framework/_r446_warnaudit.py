#!/usr/bin/env python3
"""_r446_warnaudit.py —— ★★★★ **启动警告全审计**：把驱动器的**每一条**告警挖出来并逐条判定。

## 为什么（`§198` 的教训）
`§198` 查明：驱动器**启动时就打印了**「⚠⚠ C-5 不满足 … 厚度判据 V-8b 不适用」，
**而我没有处置**（自查错误 #62）。
⇒ 光修 `beta_h` 是不够的 —— **必须系统性地把"我有没有漏看别的告警"查一遍**。
（`AGENTS.md` 教训 11/19 的同类：守卫/告警必须**被发现**才算数。）

## 判据（**每条告警都必须落到一个结论**）
对日志里每一条含 `⚠` 或 `不满足` / `不适用` / `不足` / `违反` 的行：
  **W-A** 判定它属于哪一类：`配置可修` / `判据适用域` / `记账` / `已处置`。
  **W-B** 若属 `配置可修` ⇒ **必须给出具体数值与可执行的修法**。
  **W-C** 统计：`配置可修` 类**必须为 0**，否则本次启动**又不合格**。

只读日志，不碰仿真。
"""
import os
import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else '_r445_abA.log'
PAT = re.compile(r'⚠|不满足|不适用|不足|违反|超出|低于|未达')

# 已知的、**判据适用域**类（不是缺陷，是"这条判据不适用于本算例"）
SCOPE_KEYS = [
    ('块内界面自检', '判据适用域', 't=0 单块播种 ⇒ "块内"判据不适用（代码自己写了）'),
    ('nslab_n', '判据适用域', '多块构型下全局 nslab_n 结构性无效（代码自己写了）'),
    ('表示上限', '判据适用域', 'nv 是表示上限；本算例 nv=24 ≥ n=23 ⇒ **不触发**'),
    ('C-5', '配置可修', 'β_h 下界 —— `§198` 已修（用归档的 6.477）'),
    ('C-3', '记账', '有序性判据；本算例 abB 是**故意**违反（burst 对照臂）'),
    ('厚度判据 V-8b', '配置可修', 'β_h 的后果 —— `§198` 已修'),
]


def P(s):
    print(s, flush=True)


if not os.path.exists(LOG):
    P('✗ 找不到 %s' % LOG)
    raise SystemExit(1)

lines = open(LOG, encoding='utf-8', errors='replace').read().splitlines()
hits = [(i + 1, ln.rstrip()) for i, ln in enumerate(lines) if PAT.search(ln)]

P('=' * 100)
P('_r446 —— 启动警告全审计：%s（共 %d 行）' % (LOG, len(lines)))
P('=' * 100)
P('\n命中 %d 行。' % len(hits))

n_config = 0
for ln_no, ln in hits:
    cls, why = '未分类', ''
    for key, c, w in SCOPE_KEYS:
        if key in ln:
            cls, why = c, w
            break
    if cls == '配置可修':
        n_config += 1
    P('\n  L%-5d [%s]' % (ln_no, cls))
    P('    %s' % ln.strip()[:160])
    if why:
        P('    ⇒ %s' % why)

P('\n' + '=' * 100)
P('[W-C 判定]')
P('  `配置可修` 类告警数 = **%d** ⇒ %s'
  % (n_config, '✅ PASS（本次启动没有未处置的可修配置）' if n_config == 0
     else '❌ **仍有未处置的可修配置** ⇒ 本次启动不合格'))
P('  未分类行数 = **%d** ⇒ %s'
  % (sum(1 for _, ln in hits
         if not any(k in ln for k, _, _ in SCOPE_KEYS)),
     '✅ 全部可归类' if all(any(k in ln for k, _, _ in SCOPE_KEYS)
                            for _, ln in hits) else '⚠ 有未归类的，上面已逐个列出'))
P('=' * 100)
