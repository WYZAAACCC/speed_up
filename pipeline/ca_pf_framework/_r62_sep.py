#!/usr/bin/env python3
"""R62: **可分离的凸化** —— 只凸化"面内角函数"，面外惩罚保持解析。

## 动机（`R30_AUDIT_LEDGER.md` §49 的诊断）
3D 凸化把 `v` 的凹区填平，而凹区**跨过了 `n*` 方向** ⇒
`v**(n*)` 被"离 `n*` 约 20°、`v≈0.6`"的点主导（≈0.56），
把 `M(n*) = 0.0015` 的**惯习面钉扎一起抹掉** ⇒ 实测 `d(n)` 涨 35 倍。

## 可分离构造（本脚本要验的）
把法向分解为 **面外分量 `s = n·n*`** 与 **面内方向 `u`**：
        `M(n)/M0 = exp(−β_h s²) · g(θ; c)`
（`θ` = `u` 与 `a` 的夹角；`g(θ) = exp(−β_w sin²θ − c·sin²2θ)`，
 取 `s=0` 即回到现形式。）

**关键性质（可分离 ⇒ 只需一次 1D 凸化）**：
对固定的 `s`，面内极曲线是 `exp(−β_h s²)·{g(θ)(cosθ, sinθ)}`
—— **只是整体缩放**；而支撑函数对缩放是**齐次**的
⇒ `h_s(θ) = exp(−β_h s²) · h_1(θ)`（`h_1` = `s=0` 时的面内凸化支撑函数）。

⇒ 于是：
* **面外钉扎 `exp(−β_h s²)` 精确保留** ⇒ `v**(n*) = exp(−β_h)·h_1 ≪ 1` ✅
* 面内各向异性由 `h_1(θ)` 给出，可独立调到 ≳9 ✅

## 判据（先写死）
  S-1 `v**(n*)/v(n*)` **≤ 10**（现形式 ≈1；3D 凸化给 **370** ⇒ 破坏钉扎）
  S-2 `h_1(0°)/h_1(90°)` **≥ 9**（面板条长径比所需）
"""
import numpy as np

B_H, B_W = 6.477, 2.3


def axes():
    nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
    a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
    w = np.cross(nh, a); w /= np.linalg.norm(w)
    return nh, a, w


def g_in(bw, c, th):
    """面内角函数（与现形式的 `exp(−β_w sin²θ)` 在 `s=0` 时一致）。"""
    return np.exp(-bw * np.sin(th) ** 2 - c * np.sin(2 * th) ** 2)


def h1_of(bw, c, nth=200001):
    """面内 1D 凸化的支撑函数 `h_1(θ)`。

    `h_1(θ) = max_{θ'} [ g(θ')·cos(θ − θ') ]`（对**极曲线**取支撑函数）。
    ⚠ 直接对 `P(θ') = g(θ')(cosθ', sinθ')` 求 `max (P·n(θ))` 即可，
      **不需要 scipy 凸包**（第一版在平面点集上被 qhull 拒过）。
    """
    t = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    P = np.stack([g_in(bw, c, t) * np.cos(t), g_in(bw, c, t) * np.sin(t)], -1)
    out = np.empty(nth)
    # 分块算 max，避免 (nth,nth) 爆炸
    for i0 in range(0, nth, 2000):
        i1 = min(i0 + 2000, nth)
        n = np.stack([np.cos(t[i0:i1]), np.sin(t[i0:i1])], -1)
        out[i0:i1] = (P @ n.T).max(0)
    return t, out


def main():
    nh, a, w = axes()
    print('a·n* = %+.4f' % (a @ nh))
    print()
    print('  %-6s %-14s %-14s %-10s %-14s %s'
          % ('c', 'h1(0°)', 'h1(90°)', 'h1比', 'v**(n*)/v(n*)', '判定'))
    th, _ = h1_of(B_W, 0.0, nth=2001)
    for c in (0.0, 1.0, 2.0, 4.0, 8.0):
        t, h1 = h1_of(B_W, c)
        # h1 在 θ=0 与 θ=90° 处
        i0 = int(np.argmin(np.abs(((t) % (2 * np.pi)))))
        i90 = int(np.argmin(np.abs(((t - np.pi / 2) % (2 * np.pi)))))
        r = h1[i0] / h1[i90]
        # 面外：可分离 ⇒ v**(n*) = exp(−β_h)·h1(θ)（θ 任取，界用 max h1）
        v_ns = np.exp(-B_H) * h1.max()
        v_ns_raw = np.exp(-B_H) * g_in(B_W, c, np.pi / 4)   # 原 `M(n*)`
        ratio = v_ns / v_ns_raw
        ok1 = ratio <= 10.0
        ok2 = r >= 9.0
        print('  %-6.1f %-14.5f %-14.5f %-10.2f %-14.2f %s'
              % (c, h1[i0], h1[i90], r, ratio,
                 ('✅ S-1' if ok1 else '❌ S-1') + ' ' +
                 ('✅ S-2' if ok2 else '❌ S-2')))
    print()
    print('★ 对照：**3D 全凸化**（§49 的实现）给 `v**(n*)/v(n*)` ≈ **370** ⇒ 钉扎被抹掉。')
    print('  本可分离构造的比值 = `max h1 / g(45°)`（因为面外因子被精确约掉）')
    print('  ⇒ 只要 `h1` 不把面内值抬得离谱，钉扎就保住。')
    print()
    print('=== 目标：找到 `c` 使 **S-1（≤10）与 S-2（≥9）同时成立**')
    best = []
    for c in np.arange(0.0, 20.01, 0.5):
        t, h1 = h1_of(B_W, float(c), nth=4001)
        i0 = 0
        i90 = int(np.argmin(np.abs(((t - np.pi / 2) % (2 * np.pi)))))
        r = h1[i0] / h1[i90]
        ratio = h1.max() / g_in(B_W, float(c), np.pi / 4)
        if ratio <= 10.0 and r >= 9.0:
            best.append((float(c), r, ratio))
    if best:
        print('  同时满足的 c：%s' % ', '.join('%.1f(比%.1f,钉扎%.1f)' % b for b in best[:8]))
    else:
        print('  **没有**同时满足的 c ⇒ 需换面内角函数的形式')


if __name__ == '__main__':
    main()
