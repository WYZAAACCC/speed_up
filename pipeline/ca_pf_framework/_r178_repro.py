#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r178_repro.py —— 从归档 `meta.json` **逐参重建**命令行（用于"事后重跑/惰性复现"）。

## 为什么需要它

`§129` 的 W-1 核对发现：`dry_saSet2F2`(λ=1) 与 `dry_saSet2`(λ=0) 的
**代码 SHA 不同**（本轮改过 `_bk_exp.py`/`windowB_lath.py`/`_bk_measure.py`）。
**⇒ "代码变了"是混杂因素，不能靠"我觉得 λ=0 是惰性的"来排除** ——
必须**用新代码 + λ=0 重跑一段，与归档逐位对比**。

手工敲命令行**一定会漏参数**（`§129` 的 W-1 就是这么发现 `nthreads 3→4` 的）。
⇒ 本工具从 `meta.json` 的 `exp_args`（= `vars(a)`，`:1013`）**逐键重建**，只允许
**显式覆盖**少数几个键，并**打印出未覆盖的全部参数**以便核对。

## 用法

    python _r178_repro.py <tag> [--set steps=120 tag=XXX] [--out _exp/_bk_mb] [--emit]

    --emit 只打印命令，不执行。

## ⚠ 记账

* `exp_args` 是**该次运行实际生效的 argparse 命名空间**（不是默认值）⇒ 重建可靠。
* **但**：`_bk_exp.py` 本轮**新增过参数** ⇒ 旧 meta 里没有它们时，
  重建出来的命令会用**新默认值** —— 若新默认值 ≠ 旧行为，逐位对比就会假失败。
  ⇒ 本脚本会**打印**所有"该 meta 里没有、而当前 argparse 里有"的键（见 `--audit`）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
PY = '/root/miniconda3/envs/ml/bin/python'

# 这些键不进命令行（不是 CLI 参数，或是运行期产物）
SKIP = {'arm'}      # `--arm` 其实存在；这里保留以示可控


def load_exp_args(tag):
    p = os.path.join(MB, 'dry_' + tag, 'meta.json')
    if not os.path.exists(p):
        raise SystemExit('meta.json 不存在：%s' % p)
    m = json.load(open(p))
    ea = m.get('exp_args')
    if not ea:
        raise SystemExit('`%s` 的 meta 里没有 `exp_args` ⇒ 无法逐参重建' % tag)
    return m, ea


def current_parser_keys():
    """拿当前 `_bk_exp.py` 的 argparse 键集合（子进程跑，避免污染本进程）。"""
    code = ('import sys; sys.path.insert(0,"%s");'
            'import _bk_exp as E;'
            'p=E.build_parser() if hasattr(E,"build_parser") else None;'
            'print("|".join(sorted(vars(p.parse_args([])).keys())) if p else "")'
            % HERE)
    try:
        r = subprocess.run([PY, '-c', code], capture_output=True, text=True,
                           timeout=120, cwd=HERE)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        return set(r.stdout.strip().split('|'))
    except (OSError, subprocess.SubprocessError):
        return None


def to_argv(ea, overrides):
    d = dict(ea)
    d.update(overrides)
    out = []
    for k in sorted(d):
        if k in SKIP:
            continue
        v = d[k]
        flag = '--' + k.replace('_', '-')
        if k == 'laths':
            # meta 里是 list；CLI 是逗号串
            if isinstance(v, (list, tuple)):
                v = ','.join(str(int(x)) for x in v)
        if isinstance(v, bool):
            if v:
                out.append(flag)
            continue
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            out.append(flag)
            out.extend(str(x) for x in v)
            continue
        out.append(flag)
        out.append(str(v))
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    tag = sys.argv[1]
    overrides, emit, audit = {}, False, True
    i = 2
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == '--set':
            # ★ 修：第一版只吃掉 `--set` 后面的**一个** argv 元素
            #   ⇒ `--set a=1 b=2` 里的 `b=2` 会被当成未知参数。
            #   正确做法：**吃到下一个 `--` 开头的位置参数为止**。
            i += 1
            got = 0
            while i < len(sys.argv) and not sys.argv[i].startswith('--'):
                for kv in sys.argv[i].split():
                    k, _, v = kv.partition('=')
                    if not k or not _:
                        raise SystemExit('--set 需要 k=v 形式，收到 %r' % kv)
                    if v.lower() in ('true', 'false'):
                        v = (v.lower() == 'true')
                    else:
                        try:
                            v = int(v)
                        except ValueError:
                            try:
                                v = float(v)
                            except ValueError:
                                pass
                    overrides[k] = v
                got += 1
                i += 1
            if not got:
                raise SystemExit('--set 后面没有跟 k=v')
        elif a == '--emit':
            emit = True
            i += 1
        elif a == '--no-audit':
            audit = False
            i += 1
        else:
            raise SystemExit('未知参数 %r' % a)
    m, ea = load_exp_args(tag)
    print('=' * 104)
    print('_r178 —— 从 `dry_%s` 的 meta 逐参重建命令行' % tag)
    print('=' * 104)
    print('  归档关键值：N=%s laths=%s gamma0=%s steps=%s nthreads=%s'
          % (m.get('N'), m.get('laths'), m.get('gamma0'), m.get('steps'),
             m.get('nthreads')))
    print('  `exp_args` 共 %d 个键' % len(ea))
    if audit:
        cur = current_parser_keys()
        if cur is None:
            print('  ⚠ 取不到当前 argparse 键集合 ⇒ 跳过"新增键"审计')
        else:
            newk = sorted(cur - set(ea))
            gonek = sorted(set(ea) - cur)
            print('  ⇒ **当前 argparse 有、而该 meta 里没有的键**（%d 个）⇒ '
                  '这些会用**新默认值**，逐位对比时要留意：' % len(newk))
            print('     %s' % (newk if newk else '（无）'))
            if gonek:
                print('  ⇒ **该 meta 里有、而当前 argparse 没有的键**（%d 个）'
                      '⇒ ⚠ 参数被删过：%s' % (len(gonek), gonek))
    if overrides:
        print('  ⇒ 显式覆盖：%s'
              % ', '.join('%s=%r' % kv for kv in sorted(overrides.items())))
    argv = to_argv(ea, overrides)
    cmd = ' '.join([PY, '-u', '_bk_exp.py'] + argv)
    print()
    print('  重建命令（%d 个 token）：' % len(argv))
    print('    %s' % cmd)
    print()
    if emit:
        print('（--emit：不执行）')
        return 0
    env = dict(os.environ)
    env.update(MALLOC_MMAP_THRESHOLD_='65536', MALLOC_TRIM_THRESHOLD_='65536',
               MALLOC_ARENA_MAX='2', PYTHONDONTWRITEBYTECODE='1')
    print('  ⇒ 执行中（workdir=%s）…' % HERE)
    r = subprocess.run([PY, '-u', '_bk_exp.py'] + argv, cwd=HERE, env=env)
    print('  ⇒ 退出码 %d' % r.returncode)
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
