#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_nvmax_calc.py --- 回答「本机最大能承担多少 nv」。

## 依据（**全部来自实测，不是猜**）
`_r579_report.py` 在 **N=160 实测**拟合出（B/胞/nv）：
| 档 | a (B/胞/nv) | c (B/胞) | 来源 |
|---|---|---|---|
| f64 物化 | **16.00017** | 344.00 | `R579` 实测 |
| f32 物化 | **12.00017** | 340.00 | `R579` 实测 |
| f64 onfly | **9.00017** | 392.00 | `R579` 实测（物化 +48 B/胞） |
| f32 onfly | **5.00017** | 388.00 | `R579` 实测 |

`a` **逐项可解释、且与 N 无关**（它是"每胞每场"的字节数）：
* f64 物化 = `g.phi`(nv+1 行 × 8 B) + `g.pf.phi`(nv 行 × 8 B) = **16** ✓ 与实测 16.00017 吻合
* f32 物化 = `g.phi`(×4) + `g.pf.phi`(×8) = **12** ✓
* onfly 去掉 `g.pf.phi`（−8 或 −4），再加约 +1（`ncmp`/`wtab`/`atab`/`df` 随 nv 增长）⇒ 9 / 5 ✓

⇒ `数组字节 = (a·nv + c) · N³`，可**解析外推到任意 N**（外推的是 N，不是别的）。

## ⚠ 但与**实测 RSS** 差一个常数因子（**两处独立一致**，必须记账）
| 数据点 | 数组模型 | 实测 RSS | 比值 |
|---|---|---|---|
| N=80, nv=276, f64 物化 | 176 + 276×7.81 = **2332 MB** | ≈ **5300 MB** | **2.27×** |
| N=160, nv=23, f64 物化 | 1409 + 23×62.5 = **2847 MB** | ≈ **7000 MB** | **2.46×** |

⇒ 差额来自**构造期临时量 + FFT 工作区 + 解释器**（不在数组清单里）。
⇒ **保守回答用 2.4× 因子**；纯数组模型作为**乐观上界**一并给出。

预算取 `_r579_report.py` 自己用的 **22528 MB（22 GB）**。
"""
BUDGET_MB = 22528.0
RSS_OVERHEAD = 2.4          # 实测比值（2.27 / 2.46）

CFG = {
    'f64 物化 (当前生产档)': (16.00017, 344.0),
    'f32 物化':              (12.00017, 340.0),
    'f64 onfly':             (9.00017, 392.0),
    'f32 onfly':             (5.00017, 388.0),
}


def per_nv_mb(n, a):
    return a * (n ** 3) / 2 ** 20


def fixed_mb(n, c):
    return c * (n ** 3) / 2 ** 20


def main():
    print("=" * 96)
    print("本机 nv 上限（预算 %.0f MB = 22 GB；RSS 超配因子 %.1f×）" % (BUDGET_MB, RSS_OVERHEAD))
    print("=" * 96)
    print("  公式：数组 = (a·nv + c)·N³ ；RSS ≈ 数组 × %.1f" % RSS_OVERHEAD)
    print()
    print("  %-22s %8s %10s %10s | %10s %10s" %
          ("档", "每nv(MB)", "固定(MB)", "N=80 nv上限", "N=160", "N=192"))
    print("  " + "-" * 88)
    for name, (a, c) in CFG.items():
        p80, f80 = per_nv_mb(80, a), fixed_mb(80, c)
        row = []
        for n in (80, 160, 192):
            pn, fn = per_nv_mb(n, a), fixed_mb(n, c)
            eff = BUDGET_MB / RSS_OVERHEAD
            row.append(max(0, int((eff - fn) / pn)))
        print("  %-22s %8.4f %10.1f | %10d %10d %10d" %
              (name, p80, f80, row[0], row[1], row[2]))
    print()
    print("  ── 纯数组模型（**乐观上界**，不含构造期临时量）──")
    for name, (a, c) in CFG.items():
        row = []
        for n in (80, 160, 192):
            pn, fn = per_nv_mb(n, a), fixed_mb(n, c)
            row.append(max(0, int((BUDGET_MB - fn) / pn)))
        print("  %-22s N=80: %6d   N=160: %6d   N=192: %6d" % (name, row[0], row[1], row[2]))
    print()
    print("  ══ 对本决策（方案 a：N=160、nv = B·n = 3×23 = 69）的定量回答 ══")
    for name, (a, c) in CFG.items():
        pn, fn = per_nv_mb(160, a), fixed_mb(160, c)
        arr = fn + 69 * pn
        print("  %-22s 数组 %6.0f MB ⇒ RSS ≈ **%5.1f GB**  %s"
              % (name, arr, arr * RSS_OVERHEAD / 1024,
                 "✅ 在 22 GB 内" if arr * RSS_OVERHEAD < BUDGET_MB else "❌ 超"))
    print()
    print("  ── 当前正在跑的档（N=80, nv=276, f64 物化）──")
    a, c = CFG['f64 物化 (当前生产档)']
    arr = fixed_mb(80, c) + 276 * per_nv_mb(80, a)
    print("     数组 %.0f MB ⇒ RSS ≈ %.1f GB（实测 ≈5.3 GB）" % (arr, arr * RSS_OVERHEAD / 1024))


if __name__ == "__main__":
    main()
