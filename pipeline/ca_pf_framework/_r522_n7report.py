#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r522_n7report.py —— **N7 量具**（`athermal 形核` 打印里 `T_k 理论` 的口径）。

## N7 是什么（判定见 `R2_PARAM_VERDICTS.md §0 N7`）
`_bk_exp.py` 的 athermal 打印原本写
    `T_of_k(n_ath_tgt)`                    ← **错**
而
  * `CL.T_of_k(k) = M_s − k/α_KM`（`windowB_closure.py:166`），它反演的是
    `alpha_km_n_lath`（`:142`），后者的 docstring 明写
    **「本条只对"堆叠型块"成立…平面上并列的块…本轮不做」**
    ⇒ **`k` 是「块内序号」。**
  * 传进去的 `n_ath_tgt` 是**全盒累计事件数**（判据 `while n_ath_tgt < _tgt`，
    `_tgt = B·n(T)`，`_bk_exp.py:1807/1810`）
    ⇒ **大了整整 `B` 倍。**

正确：全盒第 `k` 个、共 `B` 块 ⇒ 块内第 `ceil(k/B)` 根 ⇒ `T_of_k(ceil(k/B))`。

## 判据（**先写死，再跑**；全部用**归档日志里已有的实测温度**当已知答案）
* **T1 真模块可导入**：用的是 `windowB_closure` 的**真函数**，不是我重写的。
* **T2 正对照 —— 事件 #25**：`B=8` ⇒ `ceil(25/8)=4` ⇒ `T_of_k(4)`
  **必须等于 509.4 K ±0.1**（`_w2_r520_param.log:2636` 实测 `T=509.4 K`）。
* **T3 正对照 —— 事件 #34**：`ceil(34/8)=5` ⇒ `T_of_k(5)`
  **必须等于 418.5 K ±0.1**（同日志 `:2651` 实测 `T=418.5 K`）。
* **T4 负对照 —— 旧式必须给出"物理不可能值"**：
  `T_of_k(25) = −1399.7 K`、`T_of_k(34) = −2217.9 K`
  ⇒ **必须 < 0**（负绝对温度）。这一条是"tell"：一个物理上不可能的数被印在日志里。
* **T5 正对照必须**能失败**：把 `B` 误设成 1（= 旧行为）时，`ceil(k/1)=k`
  ⇒ 必须**复现**旧式的负温度。若这一步不失败，说明我的 `ceil(k/B)` 什么都没改。
* **T6 归档惰性**：`_bk_exp.py` 的改动**只在打印与 `T_hist` 增列**里；
  `dry_*` 的 CSV **不含** `T_%d 理论` 这一列 ⇒ 旧数据不受影响
  （用 grep 归档 CSV 的表头验证，不靠推理）。
"""
import csv
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_closure as CL      # noqa: E402

ALPHA = 0.011                     # `_r520c` 实测用的 `--alpha-km`
B_BLK = 8                         # `_r520c` 实测用的 `--nuc-block-target`
# 归档日志实测读数（**先写死，再跑**）
OBS = [(25, 509.4, '_w2_r520_param.log:2636'),
       (34, 418.5, '_w2_r520_param.log:2651')]
OLD_PRINT = [(25, -1399.7), (34, -2217.9)]      # 旧式实测打印值


def main():
    rows = []

    def chk(name, ok, detail):
        rows.append((name, bool(ok), detail))

    # ---------- T1 用的是真模块 ----------
    chk('T1 用 `windowB_closure` 的**真函数**（非重写）',
        callable(CL.T_of_k) and callable(CL.alpha_km_n_lath),
        'T_of_k @ %s' % CL.__file__)

    # ---------- T2/T3 正对照：新式必须复现实测温度 ----------
    for k, t_obs, src in OBS:
        kpb = -(-k // B_BLK)                     # ceil(k/B)，整数写法
        t_new = CL.T_of_k(kpb, ALPHA)
        chk('T%s 新式 `T_of_k(ceil(%d/%d)=%d)` 复现实测 %.1f K'
            % ('2' if k == 25 else '3', k, B_BLK, kpb, t_obs),
            abs(t_new - t_obs) <= 0.1,
            '算得 %.2f K；归档 %s 实测 %.1f K ⇒ 差 %+.2f K'
            % (t_new, src, t_obs, t_new - t_obs))

    # ---------- T4 负对照：旧式给物理不可能值 ----------
    ok4 = True
    det4 = []
    for k, t_old_expect in OLD_PRINT:
        t_old = CL.T_of_k(k, ALPHA)
        det4.append('T_of_k(%d)=%+.1f K（日志印 %+.1f）' % (k, t_old, t_old_expect))
        ok4 = ok4 and (t_old < 0) and (abs(t_old - t_old_expect) < 0.2)
    chk('T4 负对照：旧式 `T_of_k(k)` **必须 < 0**（负绝对温度）且复现日志值',
        ok4, '；'.join(det4))

    # ---------- T5 正对照必须能失败：B=1 ⇒ 退化成旧式 ----------
    k = 25
    kpb1 = -(-k // 1)
    t_b1 = CL.T_of_k(kpb1, ALPHA)
    chk('T5 `B=1` 时必须**退化成旧式（负温度）** —— 否则 `ceil(k/B)` 没起作用',
        abs(t_b1 - CL.T_of_k(k, ALPHA)) < 1e-9 and t_b1 < 0,
        'B=1 ⇒ 块内序号 %d ⇒ %.1f K（= 旧式）' % (kpb1, t_b1))

    # ---------- T6 归档惰性：旧 CSV 不含被改的列 ----------
    csvs = sorted(glob.glob(os.path.join(HERE, '_exp', '_bk_mb', 'dry_ab*', '*.csv')))[:4]
    hit = []
    for c in csvs:
        try:
            with open(c, errors='replace') as fh:
                hdr = fh.readline()
        except OSError:
            continue
        if '理论' in hdr or 'k_in_block' in hdr:
            hit.append(os.path.basename(c))
    chk('T6 归档 CSV 表头**不含**被改的列（旧数据不受影响）',
        (len(csvs) > 0) and (not hit),
        '查了 %d 个归档 CSV；含新列的有 %s'
        % (len(csvs), hit if hit else '无'))

    # ---------- T7 语法 ----------
    r = subprocess.run([sys.executable, '-m', 'py_compile',
                        os.path.join(HERE, '_bk_exp.py')],
                       capture_output=True, text=True)
    chk('T7 `_bk_exp.py` 语法', r.returncode == 0,
        (r.stderr or 'OK').strip().splitlines()[-1] if r.stderr else 'OK')

    # ---------- T8 新打印**确实**用 `_kpb`（不是只改了变量名没接线） ----------
    src = open(os.path.join(HERE, '_bk_exp.py'), errors='replace').read()
    has_kpb = bool(re.search(r"CL\.T_of_k\(_kpb, _alpha\)", src))
    no_old = not bool(re.search(r"CL\.T_of_k\(n_ath_tgt, _alpha\)", src))
    has_calc = bool(re.search(r"_kpb = int\(np\.ceil\(n_ath_tgt / _B_eff\)\)", src))
    chk('T8 新打印已接线（`T_of_k(_kpb)` 在、`T_of_k(n_ath_tgt)` 不在、`_kpb` 有定义）',
        has_kpb and no_old and has_calc,
        'T_of_k(_kpb)=%s  旧调用残留=%s  _kpb 定义=%s'
        % (has_kpb, not no_old, has_calc))

    # ---------- 汇总 ----------
    npass = sum(1 for _, ok, _ in rows if ok)
    lines = ['=' * 100,
             'R522 —— **N7 量具**（`T_k 理论` 的块内/全盒口径）',
             '=' * 100]
    for name, ok, detail in rows:
        lines.append('  %-62s %s   %s' % (name, '✅ PASS' if ok else '❌ FAIL', detail))
    lines.append('')
    lines.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    lines.append('★ ⇒ %s' % ('**全部通过**（新式复现实测温度；旧式确为物理不可能值）'
                             if npass == len(rows) else
                             '**未全部通过**，照实记，不得宣称修复成立。'))
    out = '\n'.join(lines)
    sys.stdout.write(out + '\n')
    with open(os.path.join(HERE, '_w2_r522_n7.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
