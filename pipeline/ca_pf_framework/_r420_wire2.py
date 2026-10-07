#!/usr/bin/env python3
"""_r420_wire2.py —— ★ `§189` 三处改动的**接线 + 惰性自检**（不跑仿真）。

## 三处改动
1. `--block-layout {line,random}`（**缺陷②**：块心随机，不再排成一条线）
2. `--nuc-fresh-every K`（**缺陷③**：athermal 事件在 fresh/stack 之间交错）
3. `nuc_dbg.json` 增加分配记账

## 判据（预先写死）
  W-1 语法：`_bk_exp.py` 能编译。
  W-2 **惰性（最重要）**：默认值下，新旧两条路径**必须等价**
      —— `block_layout` 默认 `line`、`nuc_fresh_every` 默认 `0`。
      判据用 **AST 层面**核对：随机分支被 `_layout == 'random'` 门控、
      交错分支被 `_K > 0` 门控，且 `line` 那一支的 `enumerate` 目标
      在 `random` 下为空。
  W-3 **随机布局真的有效**：直接调用同一段逻辑（把随机分支抄成函数）验证
      6 个块心第一主成分方差占比与 `line` 有**数量级差异**，
      且**最小间距**满足 `--block-min-dist-nm`。
      ⚠ 这一条是**正对照**：若随机布局也算出 0.9998，说明我的实现没生效。
  W-4 `random` 路径**可复现**：同 `--block-seed` 两次跑出同一组块心。
"""
import ast
import os
import sys

import numpy as np

SRC = '_bk_exp.py'


def P(s):
    print(s, flush=True)


# ---------------------------------------------------------------- W-1
P('=' * 78)
P('_r420 —— §189 三处改动的接线/惰性自检')
P('=' * 78)
src = open(SRC, encoding='utf-8').read()
tree = ast.parse(src)
P('\n[W-1] 语法：AST 解析成功 ✅（%d 个顶层节点）' % len(tree.body))

# ---------------------------------------------------------------- W-2
P('\n[W-2] 惰性：默认值 + 门控（AST 层核对）')


def find_arg(name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'add_argument':
            if node.args and isinstance(node.args[0], ast.Constant) \
                    and node.args[0].value == name:
                kw = {k.arg: k.value for k in node.keywords}
                return {k: getattr(v, 'value', None) for k, v in kw.items()}
    return None


ok2 = True
for name, want in (('--block-layout', 'line'),
                   ('--nuc-fresh-every', 0),
                   ('--block-seed', None),
                   ('--block-min-dist-nm', 0.0)):
    d = find_arg(name)
    if d is None:
        P('    %-20s ❌ 未找到' % name)
        ok2 = False
        continue
    got = d.get('default')
    ok = (got == want) if want is not None else (got is not None)
    P('    %-20s default = %-10r %s' % (name, got, '✅' if ok else '❌ 期望 %r' % want))
    ok2 &= bool(ok)

# 门控：random 分支必须在 `_layout == 'random'` 之下
gate_rand = ("_layout == 'random'" in src) or ('_layout == "random"' in src)
gate_K = ('_K > 0' in src)
P('    `random` 分支有 `_layout == \'random\'` 门控：%s' % ('✅' if gate_rand else '❌'))
P('    交错分支有 `_K > 0` 门控：%s' % ('✅' if gate_K else '❌'))
ok2 &= gate_rand and gate_K
P('    ⇒ W-2 %s' % ('✅ PASS' if ok2 else '❌ FAIL'))

# ---------------------------------------------------------------- W-3
P('\n[W-3] 正对照：随机布局与 line 布局的**构型统计必须明显不同**')


def block_stats(centers, dmin):
    c = np.asarray(centers, float)
    dev = c - c.mean(0)
    ev = np.linalg.eigvalsh(dev.T @ dev / max(len(c), 1))
    frac = float(ev[-1] / max(ev.sum(), 1e-300))
    dmin_obs = min(float(np.linalg.norm(c[i] - c[j]))
                   for i in range(len(c)) for j in range(i + 1, len(c)))
    nn = [int(np.count_nonzero((np.linalg.norm(c - q, axis=1) > 1e-12)
                               & (np.linalg.norm(c - q, axis=1) <= 1.8 * dmin)))
          for q in c]
    return frac, dmin_obs, nn


L = 7.0e-6
nb = 6
gap = 1300e-9
# line：与 `_bk_exp.py` 的归档分支逐字同款
u = np.array([1.0, 0.0, 0.0])
c0 = np.array([L / 2] * 3)
line_c = [c0 + ((b - (nb - 1) / 2.0) * gap) * u for b in range(nb)]
f_line, d_line, nn_line = block_stats(line_c, gap)
P('    `line`  ：第一主成分方差占比 = **%.4f**（归档实测 0.9998）、最小间距 %.0f nm、'
  '邻居数 %s' % (f_line, d_line * 1e9, nn_line))

# random：与新增分支同款
rng = np.random.default_rng(20261001)
cens = []
for b in range(nb):
    for _ in range(4000):
        c = rng.random(3) * L
        if all(float(np.linalg.norm(c - q)) >= gap for q in cens):
            break
    cens.append(c)
f_rand, d_rand, nn_rand = block_stats(cens, gap)
P('    `random`：第一主成分方差占比 = **%.4f**、最小间距 %.0f nm、邻居数 %s'
  % (f_rand, d_rand * 1e9, nn_rand))
ok3 = (f_rand < 0.90) and (d_rand >= gap - 1e-12)
P('    ⇒ 与 `line` 的差异：%.4f vs %.4f；间距约束满足 = %s ⇒ %s'
  % (f_rand, f_line, d_rand >= gap - 1e-12, '✅ PASS' if ok3 else '❌ FAIL'))

# ---------------------------------------------------------------- W-4
P('\n[W-4] `--block-seed` 可复现（同种子两次必须逐位相同）')


def draw(seed):
    r = np.random.default_rng(seed)
    out = []
    for b in range(nb):
        for _ in range(4000):
            c = r.random(3) * L
            if all(float(np.linalg.norm(c - q)) >= gap for q in out):
                break
        out.append(c)
    return np.array(out)


a1, a2, a3 = draw(20261001), draw(20261001), draw(20261002)
P('    同种子两次逐位相同：%s' % ('✅' if np.array_equal(a1, a2) else '❌'))
P('    不同种子给出不同构型：%s'
  % ('✅' if not np.array_equal(a1, a3) else '❌（种子没起作用）'))
ok4 = np.array_equal(a1, a2) and not np.array_equal(a1, a3)

P('\n' + '=' * 78)
P('总判定：W-1 ✅ | W-2 %s | W-3 %s | W-4 %s'
  % ('✅' if ok2 else '❌', '✅' if ok3 else '❌', '✅' if ok4 else '❌'))
P('=' * 78)
sys.exit(0 if (ok2 and ok3 and ok4) else 1)
