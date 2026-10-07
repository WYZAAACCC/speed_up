#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r528_n8dtcheck.py —— **N8 与「ΔT = 1/α_KM」两处新校验的量具**
（用户 2026-10-04 拍板：ΔT 取**方案 A**；N8 修法取**自动推导 + 硬校验**）。

## 被测的两条
* **ΔT（方案 A）**：`--qs-clock 1` 时若**显式**传了 `--qs-dT ≠ 1/α_KM` ⇒ **拒绝启动**。
  不传 ⇒ 自动取 `1/α_KM`（`_bk_exp.py` 的 `_qs_dT_auto`）。
* **N8**：`--nuc-block-target B > 0` 时，`--nuc-fresh-every K` 必须 `= n(T_end)`：
  * **不传**（`K=0`）⇒ **自动推导**为 `n(T_end)`；
  * **传了但不等于** `n(T_end)` ⇒ **拒绝启动**；
  * **传了且等于** ⇒ 打印"校验通过"。
  闭式：实际块数 `= ceil(B·n/K)`，要 `= B` ⇒ `K = n(T_end)`（**与 B 无关**）。

## 判据（**先写死，再跑**）
| # | 用例 | 期望 |
|---|---|---|
| T1 | `--qs-clock 1`，不传 `--qs-dT` | 日志含 `自动取默认`；**不**退出 |
| T2 | `--qs-dT 90.90909090909091`（= 1/0.011） | 日志含 `显式传入且已通过断言`；**不**退出 |
| T3 | `--qs-dT 50`（**负对照**） | **退出**且提示含 `与已拍板的方案 A 不符` |
| T4 | `--nuc-block-target 8 --nuc-init 6`，不传 `K` | 日志含 `N8 自动推导` 且 **K = 5**；**不**退出 |
| T5 | 同上但 `--nuc-fresh-every 6`（**负对照**） | **退出**且提示含 `不自洽` 与 `K 必须取 5` |
| T6 | 同上但 `--nuc-fresh-every 5`（正好） | 日志含 `N8 校验通过`；**不**退出 |
| T7 | **默认路径**：不传 `--nuc-block-target`（=0） | 日志**不含** `N8 自动推导`（惰性 ⇒ 归档不变） |
| T8 | 归档惰性：`--qs-clock`/`--nuc-block-target` 都不开 | 上面两条校验**一条都不触发** |

⚠ `T2` 的容差是 `1e-9·max(ref,1)`（≈9.1e-8 K）⇒ 必须传**足够精确**的 `1/0.011`。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = '_exp/_bk_n8'
BASE = ['--N', '32', '--dx-nm', '62.5', '--every', '1',
        # ⚠ `--snap-every 0` **会除零崩**（`it % a.snap_every`）——
        #   本量具第一版就是栽在这上面（8 个用例**全部** rc=1，
        #   而"日志里有没有那句话"全是对的 ⇒ 看着像校验坏了，其实是**测试自己的配置非法**）。
        #   ⇒ 用 200（大于本测试的 `--steps 2` ⇒ 实际不落快照）。
        '--snap-every', '200', '--phi-band-every', '200',
        '--pair-every', '0', '--norm-smooth', '0', '--nthreads', '2',
        '--laths', '1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8',
        '--plate-L', '1000', '--plate-W', '500', '--plate-T', '510',
        '--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
        '--nuc-law', 'athermal', '--nuc-init', '6',
        '--alpha-km', '0.011', '--T-end', '350.0', '--cool-rate', '2.3524e6',
        '--steps', '2', '--out', OUT]


def run(tag, extra, timeout=1800):
    cmd = [PY, '-u', os.path.join(HERE, '_bk_exp.py')] + BASE + \
          ['--tag', tag] + extra
    lp = os.path.join(HERE, '_w2_r528_%s.log' % tag)
    with open(lp, 'w') as fh:
        p = subprocess.run(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                           timeout=timeout)
    with open(lp, errors='replace') as fh:
        return p.returncode, fh.read(), lp


def main():
    rows = []

    def chk(n, ok, d):
        rows.append((n, bool(ok), d))

    # ---- T1 ΔT 自动 ----
    rc, t, lp = run('dt_auto', ['--qs-clock', '1'])
    chk('T1 ΔT 不传 ⇒ **自动取 1/α_KM** 且不退出',
        (rc == 0) and ('自动取默认' in t),
        'rc=%d；含"自动取默认"=%s' % (rc, '自动取默认' in t))

    # ---- T2 ΔT 显式且正确 ----
    rc, t, lp = run('dt_ok', ['--qs-clock', '1', '--qs-dT', '90.90909090909091'])
    chk('T2 ΔT 显式传 1/α_KM ⇒ 通过断言',
        (rc == 0) and ('显式传入且已通过断言' in t),
        'rc=%d；含"显式传入且已通过断言"=%s' % (rc, '显式传入且已通过断言' in t))

    # ---- T3 ΔT 负对照 ----
    rc, t, lp = run('dt_bad', ['--qs-clock', '1', '--qs-dT', '50'])
    chk('T3 ΔT=50（负对照）⇒ **必须退出**且给方案 A 的理由',
        (rc != 0) and ('与已拍板的方案 A 不符' in t),
        'rc=%d；含"与已拍板的方案 A 不符"=%s' % (rc, '与已拍板的方案 A 不符' in t))

    # ---- T4 N8 自动推导 ----
    rc, t, lp = run('n8_auto', ['--qs-clock', '1',
                                '--nuc-block-target', '8'])
    chk('T4 K 不传 ⇒ **自动推导为 n(T_end)=5**',
        (rc == 0) and ('N8 自动推导' in t) and ('K = n(T_end) = 5' in t),
        'rc=%d；含"N8 自动推导"=%s；含"K = n(T_end) = 5"=%s'
        % (rc, 'N8 自动推导' in t, 'K = n(T_end) = 5' in t))

    # ---- T5 N8 负对照 ----
    rc, t, lp = run('n8_bad', ['--qs-clock', '1', '--nuc-block-target', '8',
                               '--nuc-fresh-every', '6'])
    chk('T5 K=6 ≠ n=5（负对照）⇒ **必须退出**且指出 K 应取 5',
        (rc != 0) and ('不自洽' in t) and ('`K` 必须取 5' in t),
        'rc=%d；含"不自洽"=%s；含"K 必须取 5"=%s'
        % (rc, '不自洽' in t, '`K` 必须取 5' in t))

    # ---- T6 N8 正好 ----
    rc, t, lp = run('n8_ok', ['--qs-clock', '1', '--nuc-block-target', '8',
                              '--nuc-fresh-every', '5'])
    chk('T6 K=5 == n(T_end) ⇒ 打印"校验通过"',
        (rc == 0) and ('N8 校验通过' in t),
        'rc=%d；含"N8 校验通过"=%s' % (rc, 'N8 校验通过' in t))

    # ---- T7 默认路径惰性 ----
    rc, t, lp = run('n8_off', ['--qs-clock', '1'])          # 不传 block-target
    chk('T7 `--nuc-block-target 0`（默认）⇒ **不触发** N8 推导（归档惰性）',
        (rc == 0) and ('N8 自动推导' not in t) and ('N8 校验通过' not in t),
        'rc=%d；含"N8 自动推导"=%s（应为 False）' % (rc, 'N8 自动推导' in t))

    # ---- T8 qs-clock 关 ⇒ 两条都不进 ----
    rc, t, lp = run('alloff', [])                            # 无 --qs-clock
    chk('T8 无 `--qs-clock` ⇒ ΔT/N8 两条校验**一条都不触发**',
        (rc == 0) and ('自动取默认' not in t) and ('N8 自动推导' not in t),
        'rc=%d；含"自动取默认"=%s；含"N8 自动推导"=%s'
        % (rc, '自动取默认' in t, 'N8 自动推导' in t))

    npass = sum(1 for _, ok, _ in rows if ok)
    L = ['=' * 100,
         'R528 —— N8（K = n(T_end)）与 ΔT（方案 A）两处新校验的量具',
         '=' * 100]
    for n, ok, d in rows:
        L.append('  %-58s %s   %s' % (n, '✅ PASS' if ok else '❌ FAIL', d))
    L.append('')
    L.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    L.append('★ ⇒ %s' % ('**全部通过**（两条校验都会拦、也会放行，且默认路径惰性）'
                         if npass == len(rows) else
                         '**未全部通过**，照实记。'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r528_n8dt.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
