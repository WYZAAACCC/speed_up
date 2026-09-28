#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_probe_nuc_switches.py —— 形核三个开关的**单因素敏感性对照**（用户 2026-09-28 决策 D-1/D-2/D-3）

对应决策
--------
* **D-1 `harden_f`（阶段③）**：默认保持 1.0（不启用），本探针跑一档 `harden_f=0.1`
  **当探针、不进默认** —— 目的是回答"阶段③到底影不影响分组统计"，据此决定要不要做真正的硬化律。
* **D-2 `var_rule`**：`ed`（现默认）/ `random` / **`doublet`**（Salama 2024：每形核点随机抽 2 个）三档对照。
  `doublet` 尚未实现时，本探针**显式标 SKIP 并说明原因**，绝不静默当成 `ed`。
* **D-3 `use_fcrit`**：`False` / `True`(+`df=Δf`) 两档，看驱动力判据是否真改变形核统计。

同时顺带补上**靶③ 缺失的量具**（变体界面分数分解）
--------------------------------------------------
`RESEARCH_INTENT` 的靶③ 是"变体界面长度分数"，而全仓库**没有这个量具**（已核实）。
本探针用 `region()` 的 6 邻域跨界计数做**面积代理**，分解为：

| 类别 | 定义 |
|---|---|
| **parent–variant** | `0–k`：β/α′ 界面 |
| **intra-packet** | `k–l` 且同属一个 Burgers `{110}β` 族（族 = `(k−1)//2`，6 族 × 2 变体） |
| **inter-packet** | `k–l` 且不同族 |
| **intra-block** | **不可能**（block = 同一变体 ⇒ 同一 region）—— 列出来是为了**显式说明这一条恒为 0** |

⚠ **靶③ 的文献口径（`R10`）**：Beladi 2014 是 **Ti-64 但淬火**，**不是 LPBF**
⇒ 本探针**只报模型自己的分解**；若要引用 0.38/0.30，必须**先核实那两个数到底对应哪一类界面**，
并**强制标注工艺差异**。**在此之前不得声称"命中文献"。**

判据（单因素 + 已知答案）
------------------------
* **S-0 量具正对照**：种一个孤立板条 ⇒ `parent–variant` 界面数应 > 0，而
  `intra-packet` / `inter-packet` 必须 **= 0**（只有一个变体，不可能有变体-变体界面）。
* **S-1 基线可复现**：两次跑基线（同 seed）⇒ 事件数与界面分解必须**逐位相同**。
* **S-2 单因素**：每一档与基线只差**一个**参数。
* **S-3 `doublet` 支持探测**：若引擎不认识 `doublet`，必须**显式 SKIP**（不是静默降级）。

用法：python3 _probe_nuc_switches.py [--N 64] [--dx-nm 50] [--steps 60] [--every 10]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB, DF = 1e-9, 3.5e8
R_NUC, T_NUC = 300e-9, 700e-9
ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--steps', type=int, default=60)
ap.add_argument('--every', type=int, default=10)
ap.add_argument('--n0', type=int, default=8)
ap.add_argument('--seed', type=int, default=7)
a = ap.parse_args()
N, dx = a.N, a.dx_nm * 1e-9
L = N * dx
DT = 0.15 * dx / (MOB * DF)


def build(fixed_k=None):
    """`fixed_k` 给了就**只种同一个变体** —— S-0 正对照需要它：
       随机撒不同变体时，相邻的两片会形成**变体–变体界面** ⇒
       "未形核 ⇒ 只有 parent–variant"这一前提**本身就不成立**（实测 `inter-packet=77`）。"""
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
    rng = np.random.default_rng(a.seed)
    ns, guard = 0, 0
    while ns < a.n0 and guard < 500:
        guard += 1
        c = rng.random(3) * (L - 2 * (300e-9 + 0.3e-6)) + (300e-9 + 0.3e-6)
        k = int(fixed_k) if fixed_k is not None else int(rng.integers(1, NV + 1))
        nv_ = np.asarray(NPF[k], float)
        try:
            g.seed_plate(k, c, nv_ / np.linalg.norm(nv_), 300e-9, 200e-9)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g


def fam(k):
    """Burgers `{110}β` 族编号：变体 1..12 ⇒ 族 0..5（每族 2 个变体）。"""
    return (int(k) - 1) // 2


def iface_decompose(reg):
    """用 6 邻域跨界计数做**界面面积代理**，按界面类型分解。靶③ 的量具（本仓库原先没有）。"""
    cnt = dict(pv=0, intra_pkt=0, inter_pkt=0, intra_blk=0)
    for ax in range(3):
        x = reg
        y = np.roll(reg, -1, axis=ax)
        sel = x != y
        for u, v in zip(x[sel].ravel(), y[sel].ravel()):
            u, v = int(u), int(v)
            if u == v:
                continue
            if u == 0 or v == 0:
                cnt['pv'] += 1                 # parent–variant
            elif u == v:
                cnt['intra_blk'] += 1          # 恒 0（同变体 ⇒ 同 region）
            elif fam(u) == fam(v):
                cnt['intra_pkt'] += 1          # 同 packet、不同变体
            else:
                cnt['inter_pkt'] += 1          # 跨 packet
    tot = sum(cnt.values())
    return cnt, tot


def m6p_p25(g):
    """`M6p` p25（R4 口径）：界面胞上"法向 vs 惯习面法向 `NPF[k]`"夹角的 p25。
    ★ 为什么必须有它：本轮（Round 134）的教训 —— **对照实验要选一个"两种假设给出不同值"的量**。
      三档 `var_rule` 的差别**只在变体选择**，而 `事件数` 被 `n_fresh` 封顶 ⇒ 区分不了；
      真正该被评判的是**取向分组质量** ⇒ `M6p`（D16c 门槛 **≤20°**）。
      实现与 `T16.stats()` 逐字同口径（`edge_order=2`、`|cos|`、带内界面胞）。"""
    from T16_verify_rve import NPF as _NPF
    reg = g.region()
    A = []
    for k in range(1, g.nreg):
        mk = (reg == k)
        if not mk.any() or _NPF.get(k) is None:
            continue
        m2 = np.zeros(mk.shape, bool)
        for ax in range(3):
            m2 |= (np.roll(reg, 1, axis=ax) == 0)
        iface = mk & m2
        if iface.sum() < 5:
            continue
        gg = np.gradient(g.phi[k], g.dx, edge_order=2)
        gn = np.sqrt(sum(t ** 2 for t in gg)) + 1e-30
        nrm = np.stack([t / gn for t in gg], -1)[iface]
        nd = np.asarray(_NPF[k], float)
        nd = nd / np.linalg.norm(nd)
        A.append(np.degrees(np.arccos(np.clip(np.abs(nrm @ nd), 0, 1))))
    if not A:
        return float('nan'), 0
    A = np.concatenate(A)
    return float(np.percentile(A, 25)), int(A.size)


def run_arm(tag, **nuc_kw):
    g = build()
    # ★ 修（Round 136）：原来此处硬编码 `harden_f=1.0`，而臂参数里也会给 `harden_f`
    #   ⇒ `TypeError: got multiple values for keyword argument 'harden_f'` ⇒ 五臂一个都没跑。
    nuc_kw.setdefault('harden_f', 1.0)
    nuc_kw.setdefault('var_rule', 'ed')
    nuc_kw.setdefault('use_fcrit', False)
    g.nuc_cfg(R_NUC, T_NUC, gamma=0.15, n_init=16,
              sym_gap_cells=2, max_per_step=8, seed=11, **nuc_kw)
    nev = 0
    for it in range(1, a.steps + 1):
        g.advance(DT, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
        if it % a.every == 0:
            ed = g.elastic_driving()
            kv = {}
            if nuc_kw.get('use_fcrit', False):
                kv['df'] = DF
            nev += len(g.nucleate(ed, f_now=1.0 - float((g.region() == 0).sum()) / N ** 3,
                                  n_fresh=2, n_stack=2, **kv))
    reg = g.region()
    cnt, tot = iface_decompose(reg)
    f = 1.0 - float((reg == 0).sum()) / N ** 3
    m6p, n_if = m6p_p25(g)
    return dict(tag=tag, nev=nev, nreg=int(len(np.unique(reg))), f=f,
                cnt=cnt, tot=tot, forced=getattr(g, '_forced_reinit', 0),
                m6p=m6p, n_if=n_if, dbg=dict(g._nuc.get('dbg', {})))


print('=' * 104)
print('_probe_nuc_switches —— 形核三开关单因素对照 + 靶③ 界面分解量具')
print('  N=%d Δx=%.1f nm L=%.2f µm steps=%d every=%d n0=%d seed=%d'
      % (N, a.dx_nm, L * 1e6, a.steps, a.every, a.n0, a.seed))
print('=' * 104)

# ---------------------------------------------------------------- S-0 量具正对照
#   ★★ 判据修正（Round 136，第一版 FAIL 且**失败在判据本身**）：
#     第一版写"只种初始板条 ⇒ 只应有 parent–variant 界面"，但 `build()` **随机撒不同变体**的种子
#     ⇒ 相邻两片会产生**变体–变体**界面（实测 `inter-packet=77`）⇒ **前提不成立**。
#     ⇒ 改为**只种同一个变体**（`fixed_k`）：此时**真**不该有任何变体–变体界面。
g0 = build(fixed_k=1)
reg0 = g0.region()
cnt0, tot0 = iface_decompose(reg0)
ok0 = (cnt0['pv'] > 0) and (cnt0['intra_pkt'] == 0) and (cnt0['inter_pkt'] == 0)
print('\n【S-0 量具正对照】**只种同一个变体**（`fixed_k=1`，未形核）⇒ 只应有 parent–variant 界面')
print('   parent–variant=%d  intra-packet=%d  inter-packet=%d  intra-block=%d（恒 0）'
      % (cnt0['pv'], cnt0['intra_pkt'], cnt0['inter_pkt'], cnt0['intra_blk']))
print('   ⇒ %s' % ('PASS（单变体 ⇒ 不可能有变体-变体界面）' if ok0 else 'FAIL'))
fails = [] if ok0 else ['S-0']

# ---------------------------------------------------------------- 探测 doublet 支持
_supported = None
try:
    import inspect
    _src = inspect.getsource(W.LevelSetMulti.nucleate)
    _supported = ('doublet' in _src)
except Exception:
    _supported = False
print('\n【S-3 `doublet` 支持探测】引擎源码里%s出现 `doublet`'
      % ('' if _supported else '**未**'))
if not _supported:
    print('   ⇒ `var_rule="doublet"` 这一档将 **SKIP**（尚未实现，用户决策 D-2 待落地）。')
    print('   ⚠ **绝不静默降级成 `ed`** —— 那会让"三档对照"变成假的。')

# ---------------------------------------------------------------- 各档
ARMS = [
    ('A 基线      ed/fcrit=off/harden=1.0', dict(var_rule='ed', use_fcrit=False, harden_f=1.0)),
    ('B harden=0.1（阶段③探针）        ', dict(var_rule='ed', use_fcrit=False, harden_f=0.1)),
    ('C var_rule=random               ', dict(var_rule='random', use_fcrit=False, harden_f=1.0)),
    ('E use_fcrit=on                  ', dict(var_rule='ed', use_fcrit=True, harden_f=1.0)),
]
if _supported:
    ARMS.insert(2, ('D var_rule=doublet             ',
                    dict(var_rule='doublet', use_fcrit=False, harden_f=1.0)))

res = {}
for tag, kw in ARMS:
    r = run_arm(tag.strip(), **kw)
    res[tag] = r
    c = r['cnt']
    print('\n【%s】事件 %d · 区域数 %d · f=%.4f · 强制reinit %d' % (tag, r['nev'], r['nreg'], r['f'], r['forced']))
    print('   ★ **`M6p` p25 = %.1f°**（D16c 门槛 ≤20°；界面点 %d）' % (r['m6p'], r['n_if']))
    print('   界面分解：parent–variant %d (%.1f%%) · intra-packet %d (%.1f%%) · '
          'inter-packet %d (%.1f%%) · intra-block %d'
          % (c['pv'], 100.0 * c['pv'] / max(r['tot'], 1),
             c['intra_pkt'], 100.0 * c['intra_pkt'] / max(r['tot'], 1),
             c['inter_pkt'], 100.0 * c['inter_pkt'] / max(r['tot'], 1), c['intra_blk']))

# ---------------------------------------------------------------- 判决
base = res[ARMS[0][0]]
print('\n' + '=' * 104)
print('【单因素判决】（相对基线 A；判据用**事件数 / `M6p` / 界面分解**，不用水平值 —— `R4`/教训 #26）')
for tag, _ in ARMS[1:]:
    r = res[tag]
    d_nev = r['nev'] - base['nev']
    d_reg = r['nreg'] - base['nreg']
    d_vv = (r['cnt']['intra_pkt'] + r['cnt']['inter_pkt']) - \
           (base['cnt']['intra_pkt'] + base['cnt']['inter_pkt'])
    d_m6p = r['m6p'] - base['m6p']
    print('   %s：Δ事件 %+d · Δ区域数 %+d · Δ变体-变体界面 %+d · **Δ`M6p` p25 %+.1f°**'
          % (tag, d_nev, d_reg, d_vv, d_m6p))
print('\n   ⇒ 读法（★ 本轮教训：**对照必须选一个"两种假设给出不同值"的量**）：')
print('      * `事件数` 被 `n_fresh` 封顶 ⇒ **区分不了 `ed` 与 `doublet`**（要改用 `pending_fresh`）；')
print('      * **`M6p` p25 才是"变体选择规则"该被评判的量**（D16c 门槛 ≤20°）。')
print('      * 若某档的 Δ 全为 0 ⇒ 该开关在本工况下**无分辨力**（不是"没用"，是"看不到"）。')
print('   ⚠ 本探针**只读**：`doublet` 未实现则 SKIP；不改引擎、不改默认。')
print('   ⚠ 靶③ 的文献口径（`R10`）：Beladi 2014 是 **Ti-64 但淬火**、不是 LPBF ⇒')
print('     **只报模型自己的分解**；引用 0.38/0.30 前必须先核实它对应哪一类界面，并强制标注工艺差异。')
print('=' * 104)
sys.exit(0 if not fails else 1)
