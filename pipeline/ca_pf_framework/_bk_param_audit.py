#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_param_audit.py —— **完备性审计**：源码里还有没有没进参数表的"物理量"？

用户 R29 的原话是「把当前物理框架下**所有**物理公式里的参数提取出来」
⇒ "所有"这个词要求一条**可核的完备性检查**，不能只靠我记得。

做法：
  ① 从 `windowB_closure.params()` 收下所有**已被登记**的名字（`name` 字段里的
     反引号内容 + `where`/`source` 里出现的标识符）；
  ② 扫源文件里的**模块级常量赋值**（`NAME = <数字>`）与 **argparse 默认值**
     （`add_argument('--x', ..., default=<数字>)`）；
  ③ 把 ② 里**没被 ① 提到**的列出来，按"看着像不像物理量"分两类：
     * 含物理词头（gamma/kappa/mob/gamma0/DF/MOB/alpha/beta/temp/T_/nu/E_/C_/
       eps/theta/dt/dx/rho/…）的 ⇒ **需要人看一眼**；
     * 其余的（路径、格式、I/O、GUI 开关）⇒ 自动归为"非物理"。

⚠ 这是**报告**不是断言：它不判 PASS/FAIL，只把"可能漏掉的"摆出来。
   （把它写成断言会逼我为了让它变绿而乱改名字，那正是本仓库最反对的做法。）
"""
import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import windowB_closure as CL                                    # noqa: E402

SRC = ['windowB_surface.py', 'windowB_lath.py', 'windowB_km.py',
       'T16_verify_rve.py', '_bk_exp.py', '_bk_closed.py', '_bk_measure.py']
# 物理量的"词头"：命中即认为是**可能漏登记**的物理参数
PHYS_HINT = re.compile(
    r'(gamma|kappa|mob|gamma0|gamma_m|\bDF\b|\bMOB\b|alpha|beta|theta|nu_|_nu\b|'
    r'\bE_|\bC_|eps|lambda|sigma|rho|temp|_T\b|T_|dt|dx|_L\b|_W\b|area|stiff|'
    r'act|surf|barrier|crit|thick|width|energy|force|drive|vel|rate)', re.I)
# 明确**不是**物理量的（I/O、格式、控制流）
NONPHYS = re.compile(r'(path|file|dir|out|tag|seed|step|every|thread|plot|fig|'
                     r'verbose|quiet|utf|encoding|json|csv|npz|log|fmt|width_|'
                     r'linestyle|color|dpi|font)', re.I)

MOD_CONST = re.compile(r'^([A-Z][A-Z0-9_]{2,})\s*=\s*([^#\n]+)$', re.M)
ARG_DEF = re.compile(r"add_argument\(\s*'([^']+)'[^)]*?default\s*=\s*([^,)\n]+)")


def registered():
    """已被参数表登记的字符串集合（名字 + where + source）。

    ★ Round 5 修：第一版只做**裸子串**匹配 ⇒ `--gamma0` / `--reinit-dt` /
      `--facet-eps` 这些**已登记**的参数因为名字形式不同（CLI 带 `--`、连字符 vs
      下划线）被报成"漏了" ⇒ 7 条候选里 4 条是**假阳性**。
      ⇒ 现在把参数表里的名字与 where **归一化**（去 `--`、`-`→`_`）之后再比。
    """
    s = set()
    for p in CL.params():
        s.add(p['name'])
        s.add(p['where'])
        s.add(p['source'])
    txt = ' || '.join(s)
    norm = re.sub(r'[^0-9a-zA-Z_]+', '_', txt.replace('--', ' ')).lower()
    return txt, norm


def _seen(name, reg_txt, reg_norm):
    """参数是否已被登记：①裸子串 ②归一化后按**词**出现。"""
    if name in reg_txt:
        return True
    w = re.sub(r'[^0-9a-zA-Z_]+', '_', name.replace('--', ' ')).lower().strip('_')
    return bool(w) and (w in reg_norm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true', help='连"非物理"的一起列')
    a = ap.parse_args()
    reg_txt, reg_norm = registered()
    suspects, nonphys = [], []
    for f in SRC:
        p = os.path.join(_HERE, f)
        if not os.path.exists(p):
            continue
        t = open(p, encoding='utf-8').read()
        for m in MOD_CONST.finditer(t):
            name, val = m.group(1), m.group(2).strip()
            if not re.search(r'\d', val):
                continue
            if _seen(name, reg_txt, reg_norm):
                continue
            (suspects if PHYS_HINT.search(name) and not NONPHYS.search(name)
             else nonphys).append((f, name, val[:38]))
        for m in ARG_DEF.finditer(t):
            nm, val = m.group(1), m.group(2).strip()
            if not re.search(r'\d', val) or _seen(nm, reg_txt, reg_norm):
                continue
            (suspects if PHYS_HINT.search(nm) and not NONPHYS.search(nm)
             else nonphys).append((f, 'arg %s' % nm, val[:38]))

    print('=' * 100)
    print('参数完备性审计：源码里的常量/默认值 是否都在参数表里')
    print('  （参数表共 %d 条；"未被提到"≠"漏了"，只是**需要人看一眼**）' % len(CL.params()))
    print('=' * 100)
    print('★ 看着像物理量、但参数表没提到的：%d 条' % len(suspects))
    for f, n, v in suspects:
        print('   %-22s %-34s %s' % (f, n, v))
    if a.all:
        print('\n（其余 %d 条：看着像 I/O/格式/控制流）' % len(nonphys))
        for f, n, v in nonphys:
            print('   %-22s %-34s %s' % (f, n, v))
    print('-' * 100)
    print('结论：以上 %d 条**逐条判过**之后，要么并入参数表，要么在此写明为何不算。'
          % len(suspects))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
