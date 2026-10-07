#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r538_n12check.py —— **N12 量具**：诊断落盘的"一个键毁掉整份文件"。

## 缺陷（实测，`_r535_diagrun.sh`）
`_bk_exp.py` 落盘 `nuc_dbg.json` 时写的是
    `dbg={k: int(v) for k, v in g._nuc.get('dbg', {}).items()}`
—— **对每个值无条件 `int()`**。只要有一个键不是标量（我新加的
`nfsv_diag_occ_sizes` 是 `list`）就抛异常，被 `except` 吞掉
⇒ **`nuc_dbg.json` = 0 字节**（而 `closure.json` 13 KB、`series.csv` 49 KB 正常）
⇒ **整份形核诊断全丢**，而用户硬要求是「全过程数据留盘，量具/判据有 bug 也能事后重测」。

日志原话：
```
⚠ nuc_dbg.json 落盘失败（不影响仿真结果）: int() argument must be a string,
  a bytes-like object or a real number, not 'list'
```

## 判据（**先写死，再跑**；全部用**解析已知答案**，不跑引擎）
| # | 输入 | 期望输出 |
|---|---|---|
| T1 | `np.int64(7)` | `7`，且 `type` 是 **`int`**（不是 `np.int64`） |
| T2 | `np.float64(0.5)` | `0.5`，`type` 是 **`float`** |
| T3 | **`np.bool_(True)`** | **`True`**（`type` 是 `bool`）—— ⚠ **必须不是 `1`**：若先判 `int` 就会把布尔吞成整数，这是本仓"**类型顺序**"类坑 |
| T4 | **`[3, 1, 2]`（list）** | **`[3, 1, 2]`** —— **这就是当初炸掉整份文件的那个形状** |
| T5 | `np.array([1, 2])`（ndarray） | `[1, 2]` |
| T6 | 嵌套 `{'a': np.array([1]), 'b': (2, np.int64(3))}` | `{'a': [1], 'b': [2, 3]}` |
| T7 | `float('inf')` / `float('nan')` | **`str`**（`'inf'`/`'nan'`）—— 保证 JSON 合法（`NaN`/`Infinity` 不是合法 JSON） |
| T8 | 一个**故意转不动的对象**（`__int__`/`__float__` 都抛） | `_js_diag_key` **不抛**，返回 `str`，且 `notes` **记下这个键名** |
| **T9 正对照（必须能失败）** | 用**旧写法** `int(v)` 处理 `[3,1,2]` | **必须抛异常** —— 证明 T4 那条真能分辨新旧 |
| **T10 端到端** | 把含 list 的 `dbg` 走一遍新落盘逻辑（`json.dump`） | **写出非空且可 `json.load` 回来**，且 `dbg['nfsv_diag_occ_sizes'] == [3,1,2]` |

⚠ 本量具**只用解析已知答案**（本仓用户硬要求："凡最小化/最优化得到的量，
必须先用解析已知答案验证……正对照必须预先写死、必须能失败"）。
"""
import json
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_exp as E                                           # noqa: E402


class _Uncoercible:
    """**故意转不动**的对象：连 `str()` 之外的路都堵死（用于 T8a）。

    ⚠ T8 第一版我**预期错了**：我要求 `_js_diag_key` 在这里**记账**（`notes` 非空），
      实测 `notes=[]` ⇒ 判 FAIL。**但那是我的判据错，不是代码错**：
      `_js_diag` **有一条兜底 `return str(v)`** ⇒ 对任何有 `__str__` 的对象
      **根本不会抛** ⇒ 降级路径**用不上** ⇒ `notes` 当然为空。
      ⇒ **设计比我的预期更强**（"不可能失败"优于"失败了能降级"）。
      ⇒ 按纪律**改推导**（补一个 `__str__` 也抛的对象 T8b），**不放宽阈值**。
    """

    def __int__(self):
        raise TypeError('故意不可 int')

    def __float__(self):
        raise TypeError('故意不可 float')

    def __str__(self):
        return '<uncoercible>'


class _Unstringable:
    """**连 `str()` 都抛**的对象 ⇒ 逼出 `_js_diag` 的异常路径（用于 T8b）。"""

    def __int__(self):
        raise TypeError('故意不可 int')

    def __float__(self):
        raise TypeError('故意不可 float')

    def __str__(self):
        raise TypeError('故意不可 str')

    def __repr__(self):
        return '<unstringable>'


def main():
    rows = []

    def chk(n, ok, d):
        rows.append((n, bool(ok), d))

    f = E._js_diag

    # ---- T1/T2/T3 标量类型 ----
    v1 = f(np.int64(7))
    chk('T1 `np.int64(7)` → 原生 `int`',
        (v1 == 7) and (type(v1) is int), '值=%r 类型=%s' % (v1, type(v1).__name__))
    v2 = f(np.float64(0.5))
    chk('T2 `np.float64(0.5)` → 原生 `float`',
        (v2 == 0.5) and (type(v2) is float), '值=%r 类型=%s' % (v2, type(v2).__name__))
    v3 = f(np.bool_(True))
    chk('T3 `np.bool_(True)` → **`True`（不是 1）**',
        (v3 is True), '值=%r 类型=%s（**若先判 int 会变成 1**）'
        % (v3, type(v3).__name__))
    v3b = f(np.bool_(False))
    chk('T3b `np.bool_(False)` → `False`（不是 0）',
        (v3b is False), '值=%r' % (v3b,))

    # ---- T4 **当年炸掉整份文件的形状** ----
    v4 = f([3, 1, 2])
    chk('T4 **`list` 必须能转**（就是当初炸掉整份文件的形状）',
        v4 == [3, 1, 2], '值=%r 类型=%s' % (v4, type(v4).__name__))

    # ---- T5/T6 嵌套 ----
    v5 = f(np.array([1, 2]))
    chk('T5 `ndarray` → `list`', v5 == [1, 2], '值=%r' % (v5,))
    v6 = f({'a': np.array([1]), 'b': (2, np.int64(3))})
    chk('T6 嵌套 dict/list/tuple/ndarray 递归',
        v6 == {'a': [1], 'b': [2, 3]}, '值=%r' % (v6,))

    # ---- T7 非有限值 ----
    v7a, v7b = f(float('inf')), f(float('nan'))
    chk('T7 `inf`/`nan` → `str`（保证 JSON 合法）',
        isinstance(v7a, str) and isinstance(v7b, str),
        'inf→%r nan→%r' % (v7a, v7b))

    # ---- T8 两级：兜底 vs 降级 ----
    #   T8a：`str()` 能用 ⇒ `_js_diag` **自己就兜住了**，**不需要**降级
    #        ⇒ 正确期望是"**不抛、返回 str、notes 为空**"
    #        （⚠ 我第一版期望 notes 非空 ⇒ **假 FAIL**，见 `_Uncoercible` 的 docstring）
    notes = []
    v8a = E._js_diag_key('bad_key', _Uncoercible(), notes)
    chk('T8a `str()` 可用 ⇒ **兜底成功**、`notes` 应为**空**（不需要降级）',
        isinstance(v8a, str) and (notes == []),
        '值=%r notes=%r ⇒ **兜底比降级更优先**，这是更强的设计' % (v8a, notes))
    #   T8b：连 `str()` 都抛 ⇒ 这才真正走到降级路径
    notes2 = []
    v8b = E._js_diag_key('bad_key2', _Unstringable(), notes2)
    chk('T8b **连 `str()` 都抛** ⇒ 降级：不抛、返回 `str`、且记下键名',
        isinstance(v8b, str) and (len(notes2) == 1) and ('bad_key2' in notes2[0]),
        '值=%r notes=%r' % (v8b, notes2))

    # ---- T9 正对照：旧写法必须失败 ----
    _old_failed = False
    try:
        int([3, 1, 2])                                          # noqa: PLC2401
    except Exception:                                           # noqa: BLE001
        _old_failed = True
    chk('**T9 正对照：旧写法 `int([3,1,2])` 必须抛**（证明 T4 能分辨新旧）',
        _old_failed,
        '旧写法抛异常=%s ⇒ 这就是 `nuc_dbg.json` 变 0 字节的原因' % _old_failed)

    # ---- T10 端到端：含 list 的 dbg 走一遍落盘 ----
    dbg = {'nfsv_nofield': np.int64(21), 'nfsv_diag_occ_sizes': [3, 1, 2],
           'nfsv_diag_v': np.int64(1), 'flag': np.bool_(True)}
    notes2 = []
    payload = dict(dbg={k: E._js_diag_key(k, v, notes2) for k, v in dbg.items()},
                   dbg_coercion_notes=notes2)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, 'nuc_dbg.json')
        ok10 = False
        detail = ''
        try:
            with open(p, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=1,
                          default=lambda o: (o.tolist()
                                             if isinstance(o, np.ndarray) else str(o)))
            back = json.load(open(p, encoding='utf-8'))
            ok10 = (back['dbg']['nfsv_diag_occ_sizes'] == [3, 1, 2]
                    and back['dbg']['nfsv_nofield'] == 21
                    and back['dbg']['flag'] is True
                    and os.path.getsize(p) > 0)
            detail = '写盘 %d 字节，读回 dbg=%s' % (os.path.getsize(p), back['dbg'])
        except Exception as exc:                                # noqa: BLE001
            detail = '抛异常：%s' % exc
        chk('T10 端到端：含 `list` 的 `dbg` **写出非空且能读回**', ok10, detail)

    npass = sum(1 for _, ok, _ in rows if ok)
    L = ['=' * 100,
         'R538 —— **N12 量具**（诊断落盘：一个键不得毁掉整份文件）',
         '=' * 100,
         '  被测：`_bk_exp._js_diag` / `_js_diag_key`（2026-10-04 提取到模块级，可单测）',
         '']
    for n, ok, d in rows:
        L.append('  %-58s %s   %s' % (n, '✅ PASS' if ok else '❌ FAIL', d))
    L.append('')
    L.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    L.append('★ ⇒ %s' % ('**全部通过**（类型感知 + 逐键降级都成立，且正对照能失败）'
                         if npass == len(rows) else '**未全部通过**，照实记。'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r538_n12.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
