#!/usr/bin/env python3
"""R68: **面片投影算子**（`BLOCK_SELFAC.md §8 C` 的可调用实现 + 自检）。

## 算子（先写死）
对每个场 `k`：
1. 界面点 = `|phi_k| <= 0.5*dx`；
2. 三个轴的**支撑半宽**：`h_j = (max(x·n_j) - min(x·n_j))/2`，中心 `c_j = 中点`；
   `n_j ∈ {a_k, w_k, n*_k}`；
3. **保体积标定**：`s = (V_target / V_proj)^(1/3)`，`h_j ← s·h_j`；
4. 新 `phi_k = max_j (| (x - c0) · n_j | - s·h_j)`（把中心平移到该场的支撑中心）。

⚠ **不保证** `phi` 仍是符号距离（只保证零集正确）⇒ 调用方必须记账。
"""
import numpy as np


def facet_project_one(phi_k, dx, ax, target_vox=None, band=0.5,
                      q_lo=0.005, q_hi=0.995, excl=None):
    """对一个场做投影。`ax = (n_star, a, w)`（单位向量）。返回 `(phi_new, info)`。

    `target_vox`：目标体积（体素数）；`None` ⇒ 用当前 `phi_k < 0` 的体素数。
    """
    N = phi_k.shape[0]
    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    P = np.stack([X, Y, Z], -1)
    # ★★★ R68 修（**正对照抓出来的**）：半宽必须取自**体**（`phi_k < 0`），
    #   而**不是**界面带（`|phi_k| <= 0.5dx`）。
    #   为什么：带是**双侧**的（含体外 +0.5dx 的胞）⇒ 各轴的"最外胞"是否落在带内
    #   取决于胞心格点与真实面的相对相位 ⇒ 实测在解析长方体上
    #   `a` 半宽偏 **−18.8 nm**（漏了最外胞）、`n*` 半宽偏 **+26.2 nm**（多算了外侧胞）。
    #   取自**体**则各轴一致地"格点化向下" ⇒ 投影**幂等**（正对照才会过）。
    body = np.isfinite(phi_k) & (phi_k < 0)
    # ★★★★★ R73（**用户裁定 = 优先保根数**）：**只让外表面决定盒子**。
    #   `excl` = "与**同变体的另一个场**相邻"的胞（+ 一层余量）⇒ 从**取跨度用的点云**里排除。
    #   为什么：场-场界面是**低角晶界（F3）**，它的几何由 `γ_RS` 与两场取向差决定，
    #   **不该被"盒子表示"**；而外表面（面向母相）才是"零厚度 Gibbs 面"要刻面的对象。
    #   ⚠ 只用 `excl` 决定**盒子**（跨度与中心）；**体积标定仍按整体体积**，
    #     所以 `phi_new` 是"按外表面定形状、按总体积定大小"的盒子。
    if excl is not None:
        _pts_mask = body & (~np.asarray(excl, bool))
        if int(_pts_mask.sum()) < 50:
            _pts_mask = body                      # 排除后点太少 ⇒ 退回整体（明示）
    else:
        _pts_mask = body
    if int(body.sum()) < 50:
        return phi_k, dict(ok=False, why='体内胞不足')
    pts = P[_pts_mask]
    v0 = int(body.sum())
    tgt = v0 if target_vox is None else int(target_vox)
    lo, hi = [], []
    # ★★★★★ R70 修（**棘轮伪影**）：min/max **对长指敏感** ⇒ 只要某次推进在某个
    #   方向甩出一根指头，`hi_j` 就被顶大；再经**统一体积缩放**，宽度方向被压得更小
    #   ⇒ **每投影一次，长径比就被"棘轮"抬高一档**。
    #   【实测】`facet_proj=10` 给 `d(a)=3.818`，而**面推进**只有约 0.86 nm/步
    #   （`d(a)` 应是 ≈2×面推进 = 1.7）；多出来的那一倍**就是棘轮加的**。
    #   ⇒ 改用**分位数**（对长指稳健）+ 保留 `0.5Δx` 外扩。
    #   ⚠ `q` 默认 0.005/0.995：对**解析长方体**退化为 min/max ⇒ 自检仍应过。
    pr_all = None
    for u in ax:
        u = np.asarray(u, float)
        u = u / (np.linalg.norm(u) + 1e-300)
        pr = pts @ u
        lo.append(float(np.quantile(pr, q_lo)))
        hi.append(float(np.quantile(pr, q_hi)))
    # ★★★★ R68 修（**第四层，真正的根因**）：`(lo, hi)` 必须**外扩半个胞**。
    #   为什么：`max(lo_j − p, p − hi_j) < 0` 是**开区间** ⇒ 极端胞心落在边界上时
    #   `φ = 0`，**不算体内** ⇒ 两端各丢一个胞：`a` 25 → **23**、`w`/`n` 11 → **9**
    #   ⇒ 体积 `25×11×11 = 3025` → `23×9×9 = 1863`（实测 `vp = 1920`，吻合）。
    #   外扩 `0.5Δx` 后极端胞心严格在盒内 ⇒ 对"本身是胞对齐长方体"的体**幂等**。
    lo = np.array(lo) - 0.5 * dx
    hi = np.array(hi) + 0.5 * dx
    # ★★★ R68 修（**第三层，也是真正的根因**）：用体的 **min/max 盒**，
    #   **不是**"中心 + 半宽"。为什么：
    #   体（`φ<0` 的胞心）在 `a` 方向跨 25 个胞、`max−min = 1500 nm`；
    #   若取 `h = (max−min)/2` 并把盒子建在中心上，两个极端胞心**恰好落在边界上**
    #   ⇒ `φ = 0` 不算"体内" ⇒ **两头各丢一个胞** ⇒ 25 → 23（`w`/`n` 各 11 → 9）
    #   ⇒ 体积 `3025 → 1863`，正是实测的 `vp = 1920`。
    #   ⇒ 改用 `max(lo_j − x·n_j, x·n_j − hi_j)` ⇒ 盒子**按构造包含**体
    #   ⇒ 正对照（幂等）才有机会过。
    _U = np.stack([np.asarray(u, float) / (np.linalg.norm(u) + 1e-300) for u in ax], 0)
    _pr = P @ _U.T                                   # (..., 3)
    phi_proj = np.max(np.maximum(lo[None, None, None, :] - _pr,
                                 _pr - hi[None, None, None, :]), -1)
    vp = max(int((phi_proj < 0).sum()), 1)
    s = (tgt / float(vp)) ** (1.0 / 3.0)
    # 保体积标定：把 `[lo, hi]` **绕其中点**缩放 `s`
    mid = 0.5 * (lo + hi)
    hw = 0.5 * (hi - lo)
    lo2, hi2 = mid - hw * s, mid + hw * s
    phi_new = np.max(np.maximum(lo2[None, None, None, :] - _pr,
                                _pr - hi2[None, None, None, :]), -1)
    v1 = int((phi_new < 0).sum())
    return phi_new, dict(ok=True, v0=v0, vp=vp, s=float(s), v1=v1,
                         lo=lo.tolist(), hi=hi.tolist(),
                         rel=(v1 - tgt) / max(tgt, 1))


def selftest():
    """自检：对一个**已知长方体**的 φ 做投影 ⇒ 应**几乎不变**（幂等）。"""
    print('=' * 84)
    print('facet_project 自检：对解析长方体应**幂等**（投影前后几乎相同）')
    N, L = 64, 4.0e-6
    dx = L / N
    a = np.array([1.0, 0.0, 0.0])
    w = np.array([0.0, 1.0, 0.0])
    nh = np.array([0.0, 0.0, 1.0])
    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    d = np.stack([X - L / 2, Y - L / 2, Z - L / 2], -1)
    Lb, Wb, Tb = 1600e-9, 700e-9, 635e-9
    phi = np.maximum.reduce([np.abs(d @ a) - Lb / 2, np.abs(d @ w) - Wb / 2,
                             np.abs(d @ nh) - Tb / 2])
    phin, info = facet_project_one(phi, dx, (nh, a, w))
    print('  info =', {k: (round(v, 6) if isinstance(v, float) else v)
                       for k, v in info.items() if k not in ('lo', 'hi')})
    print('  零集体素：%d → %d（应几乎相同）' % (info['v0'], info['v1']))
    ok = abs(info['v1'] - info['v0']) / max(info['v0'], 1) <= 0.02
    print('  体积变化 ≤2%% : %s' % ('✅ PASS' if ok else '❌ FAIL'))
    print('SELFTEST =', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(selftest())
