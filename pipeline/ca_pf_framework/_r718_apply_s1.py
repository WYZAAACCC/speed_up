#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r718_apply_s1.py —— **S1 的一次性插入器**（把 `cfl_used` 接成环境变量门控守卫）。

## 设计依据（`R712_REPAIR_SPEC.md` §10.3，**已冻结，不重新决策**）
* (a) 门控用**环境变量** `CFL_GUARD = off|warn|abort`（默认 off）、`CFL_GUARD_MAX`（默认 1.0）
      —— 与仓里既有的 `SEED_CLEAN_EVERY`（`_bk_exp.py:2654`）同一套做法，**不改参数集**。
* (b) 口径 `cfl_used = dt·MOB·dG_max/dx`（与 `series.csv` 同名列 `:3589` 同一口径），上限 1.0。
* (c) 位置：主循环内 `g.advance(dt, **kw)`（`:2647`）**之后**、**任何 `continue` 之前**
      （循环体的两个 `continue` 在 `:3404/:3406`）。
* (d) **不写 `meta.json`**（那份在运行开始时已 dump，见 `:2263`）⇒ 守卫**自己落盘**
      `cfl_guard_<tag>.txt`（与 `series.csv` 同目录），四行。
* (e) 只在**首次越限**或**峰值再涨 ≥25%** 时打印；`abort` 档超限即 `raise SystemExit(2)`。
* (f) **零副作用**：不设 `CFL_GUARD` ⇒ 整段不进 ⇒ 与改动前逐位相同（不写文件、不改 dt、不打印）。

## 与规范的**唯一偏离**（已记账）
规范说"守卫自己落盘"，未指定时机。本实现取 **"峰值更新时立即重写文件"**
（而不是在循环结束后写一次）——
* 理由：**`continue` 在 `:3404/:3406`**，若把落盘放循环尾，需在 `main()` 里另找一处
  "保证每步都到"的位置；放在 `advance` 之后则**天然满足**，且崩溃/被中断时数据不丢。
* 代价：`abort` 档下是"**首次**越限即退出"，而非"跑完再报峰值" —— 与规范 (e) 的
  "峰值 > `CFL_GUARD_MAX` 时打印拒绝理由并 `raise SystemExit(2)`"一致。

## 用法
    python3 _r718_apply_s1.py --dry-run    # 只打印将插入的文本与锚点命中情况
    python3 _r718_apply_s1.py              # 就地插入（先自动备份 .s1orig）
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, '_bk_exp.py')

ANCHOR = '            g.advance(dt, **kw)\n'

GUARD = '''            # ═══════════════════════════════════════════════════════════════════════
            # ★★★★★★ R718 / S1：**有效 CFL 守卫**（`R712_REPAIR_SPEC.md §10.3`，设计已冻结）
            #   症状（F8 / P1-7）：`advance` 把**总驱动**（Δf + Δed − γκ）的最大值写在
            #     `g.dG_max`，而本驱动层定 dt 用的是**化学驱动力** `Δf`（见 `:2630/:2639`）
            #     ⇒ 实际每步位移 `cfl_used = dt·MOB·dG_max/dx` **可能远大于设计值 0.15**。
            #   实测基线（`R716`，扫 131 个归档）：全库峰值 **4.881**、越限 **2/131**；
            #     **当前世代 `dG_max/Δf ≈ 1.0–1.24`（不越限）**，旧世代（`t5AB_C/D`）26–33。
            #   ## 门控（**环境变量**，与 `SEED_CLEAN_EVERY`（`:2654`）同一套做法 ⇒ 不改参数集）
            #     CFL_GUARD      = off | warn | abort      默认 off
            #     CFL_GUARD_MAX  = <float>                 默认 1.0（仅 abort 档用）
            #   ## 位置（`R712 §10.3c`）：`g.advance` **之后**、**任何 `continue` 之前**
            #     —— 循环体的两个 `continue` 在 `:3404`（独立快照档）与 `:3406`（非测量档）
            #   ## 口径（`R712 §10.3b`，写死不许事后挪）
            #     cfl_used = dt·MOB·dG_max/dx   ← 与 `series.csv` 同名列（`:88`/`:3589`）同一口径
            #   ## ⚠ 记账（`R712 §10.3d`）：**不能写 `meta.json`** —— 那份在运行开始时
            #     已 dump（`:2263`），此时守卫还没跑。⇒ 守卫**自己落盘** `cfl_guard_<tag>.txt`。
            #   ## ⚠ 与规范的唯一偏离：落盘时机取"**峰值更新时**"而非"循环结束后"
            #     —— 理由：`continue` 在 `:3404/:3406`，放循环尾要另找位置；
            #        放这里天然满足"每步都到"，且被中断时数据不丢。
            #   ## 零副作用：不设 `CFL_GUARD` ⇒ 整段不进（不写文件、不改 dt、不打印）
            if (os.environ.get('CFL_GUARD') or 'off').strip().lower() in ('warn', 'abort'):
                try:
                    _cfl_guard_mode = (os.environ.get('CFL_GUARD') or 'off').strip().lower()
                    _cfl_guard_max = float(os.environ.get('CFL_GUARD_MAX') or 1.0)
                    _cfl_now = (float(dt) * MOB
                                * float(getattr(g, 'dG_max', float('nan'))) / dx)
                    if _cfl_now == _cfl_now:                    # NaN 感知
                        if _cfl_now > _cfl_peak + 1e-15:
                            _cfl_peak = _cfl_now
                        if _cfl_now > _cfl_guard_max:
                            _cfl_n_over += 1
                            if _cfl_first_over < 0:
                                _cfl_first_over = it
                    # 打印策略 (e)：**首次越限**时必报；之后峰值再涨 ≥25% 才报（避免刷屏）
                    # ⚠ 更正（2026-10-08，V1–V5 验收抓到）：第一版写成
                    #   `_cfl_guard_max < _cfl_now and not _cfl_told` —— 条件**反了**
                    #   ⇒ 在**没越限**的算例上也会报"cfl_used=0.1528 > 上限 1.0000"（自相矛盾）。
                    #   且 `_cfl_last_report` 从 0 起 ⇒ 首次必然触发 +25% 分支 ⇒ 每个算例都误报。
                    #   正解：越限判断一律用 `_cfl_now > _cfl_guard_max`。
                    _cfl_over = (_cfl_now == _cfl_now) and (_cfl_now > _cfl_guard_max)
                    if _cfl_over and not _cfl_told:
                        _cfl_told = True
                        _cfl_last_report = _cfl_peak
                        P('  ⚠ **CFL 守卫**（CFL_GUARD=%s）：step %d 出现 '
                          'cfl_used=%.4f > 上限 %.4f ⇒ 界面每步位移超过一个 dx，'
                          '**本算例的界面剖面不可信**'
                          % (_cfl_guard_mode, it, _cfl_now, _cfl_guard_max))
                    elif _cfl_told and _cfl_peak > _cfl_last_report * 1.25:
                        _cfl_last_report = _cfl_peak
                        P('  ⚠ CFL 守卫：峰值升到 %.4f（step %d）' % (_cfl_peak, it))
                    # 落盘 (d)：峰值更新时重写；写失败**不得影响仿真**（N12 教训）
                    if _cfl_peak > _cfl_written + 1e-15:
                        _cfl_written = _cfl_peak
                        _cfl_txt = ('cfl_used_max=%.8g\\nn_steps_over_%g=%d\\n'
                                    'first_over_step=%d\\nmode=%s\\n'
                                    % (_cfl_peak, _cfl_guard_max, _cfl_n_over,
                                       _cfl_first_over, _cfl_guard_mode))
                        try:
                            with open(os.path.join(outdir,
                                      'cfl_guard_%s.txt' % tag), 'w') as _fh:
                                _fh.write(_cfl_txt)
                        except Exception as _e:
                            P('  ⚠ cfl_guard 落盘失败（不影响仿真）: %s' % _e)
                    # abort 档：峰值超限 ⇒ 非零退出
                    if _cfl_guard_mode == 'abort' and _cfl_peak > _cfl_guard_max:
                        P('  ⛔ **CFL 守卫 abort**：峰值 cfl_used=%.4f > CFL_GUARD_MAX=%.4f '
                          '⇒ 拒绝继续（step %d）' % (_cfl_peak, _cfl_guard_max, it))
                        raise SystemExit(2)
                except SystemExit:
                    raise
                except Exception as _e:                        # noqa: BLE001
                    P('  ⚠ CFL 守卫异常（忽略，不影响仿真）: %s' % _e)
            # ═══════════════════════════════════════════════════════════════════════
'''

INIT_ANCHOR = '    for it in range(_it0, a.steps + 1):\n'

INIT = '''    # ★★★★★★ R718 / S1：CFL 守卫状态（`R712 §10.3`）。**只在 CFL_GUARD 设了才用**。
    #   ⚠ 前置条件（`R712 §10.3c`）：`_df_now` 原先**只在 `it > 0` 的 athermal 分支里赋值**
    #     （`:2627/:2638`）⇒ 守卫**不得**依赖它；本守卫只用 `dt` 与 `g.dG_max`，两者每步都有。
    _cfl_peak, _cfl_written, _cfl_last_report = 0.0, 0.0, 0.0
    _cfl_n_over, _cfl_first_over, _cfl_told = 0, -1, False
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    src = open(TARGET, encoding='utf-8').read()
    n_adv = src.count(ANCHOR)
    n_init = src.count(INIT_ANCHOR)
    print('锚点命中：g.advance 行 = %d 处（应为 1）；主循环头 = %d 处（应为 1）'
          % (n_adv, n_init))
    if n_adv != 1 or n_init != 1:
        print('⛔ 锚点不唯一 ⇒ 中止（不猜）')
        return 3
    if 'CFL_GUARD' in src:
        print('⛔ 文件里已有 CFL_GUARD ⇒ 可能已插入过 ⇒ 中止')
        return 4

    out = src.replace(INIT_ANCHOR, INIT + INIT_ANCHOR, 1)
    out = out.replace(ANCHOR, ANCHOR + GUARD, 1)
    print('插入后：+%d 字符（%d → %d）' % (len(out) - len(src), len(src), len(out)))
    if a.dry_run:
        print('--- dry-run：未写盘 ---')
        return 0

    bak = TARGET + '.s1orig'
    if not os.path.exists(bak):
        shutil.copy2(TARGET, bak)
        print('已备份 → %s' % os.path.basename(bak))
    with open(TARGET, 'w', encoding='utf-8', newline='') as f:
        f.write(out)
    print('✅ 已写入 %s' % os.path.basename(TARGET))
    return 0


if __name__ == '__main__':
    sys.exit(main())
