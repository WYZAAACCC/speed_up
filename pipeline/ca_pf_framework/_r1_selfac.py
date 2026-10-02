#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_selfac.py --- ★★★ 实验 7 的判据 S-1：**块/组织是否真的"自协调"**

科学问题
--------
"自协调（self-accommodation）"的操作性定义只有一条：**这套变体搭配让弹性能更低**。
⇒ 判据必须是**对照实验**，不能只看"看起来对称"：

    E_el(观测构型)  vs  E_el(同体积分数的**随机**变体指派)

判据（**先写死**，见 `R1_HANDOFF.md`）
------------------------------------
  S-1  `E_el_obs` 必须**显著低于**随机指派的分布（用 z 分数与分位数报出，
       不以"低一点点"当通过）。
  S-2  各组体积分数是否向**自协调配比**靠拢（Burgers 下同一 packet 内两变体 ≈ 等分；
       判据用 `|f_i − f̄|/f̄`）。
  S-3  **正对照**：把观测构型本身当作"随机"的一个样本喂进去 ⇒ z 分数必须在 0 附近
       （证明量具能分辨"没差别"）。
  ⛔ 若 S-3 不过，S-1 的任何结论都作废。

做法（便宜：只用 `PF3D`，不用重建 `LevelSetMulti` 的 12 个 `argmin_normal`）
----------------------------------------------------------------------------
  从快照 `snap_*.npz` 读 `region()`（int8）⇒ 直接喂给 `PF3D` 的指示场 ⇒ `E_el()`。
  随机对照 = 对**非母相**胞的变体号做随机置换（**保持各变体体积分数不变**）。

用法：
  python3 _r1_selfac.py --snap _exp/e7_selfac/snap_00300.npz --nrand 24
  python3 _r1_selfac.py --selftest          # 量具正对照（随机对随机的 z 分布）
"""
import os
import sys
import glob
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                              # noqa: E402
from T16_verify_rve import C, EPS0, NV, DF, MOB                 # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--snap', default=None)
ap.add_argument('--N', type=int, default=192)
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--nrand', type=int, default=24)
ap.add_argument('--workers', type=int, default=8)
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--selftest', action='store_true')
a = ap.parse_args()

L = a.L_um * 1e-6
N = a.N
print('=' * 100)
print('_r1_selfac   N=%d  L=%.1f µm  Δx=%.1f nm  随机对照 n=%d'
      % (N, a.L_um, L / N * 1e9, a.nrand))
print('=' * 100, flush=True)

from windowB_pf3d import PF3D                                   # noqa: E402

t0 = time.time()
pf = PF3D(N, L, C, EPS0, gamma=0.0, w90=1e-8, Lmob=0.0,
          workers=a.workers, k0_mode='clamped', phi_dtype=bool, lam_prec='f64')
print('PF3D 构造 %.1f s' % (time.time() - t0), flush=True)


def eel_of(reg):
    """把 `region()`（0=母相，k=变体 k）喂给 PF3D 并返回 `E_el()`（J/m³）。"""
    pf.phi[:] = False
    for v in range(NV):
        pf.phi[v] = (reg == v + 1)
    return float(pf.E_el())


def rand_perm(reg, rng):
    """**保持各变体体积分数**的随机指派：只在"非母相"胞之间置换变体号。"""
    out = reg.copy()
    m = reg > 0
    out[m] = rng.permutation(reg[m])
    return out


if a.selftest:
    # ---- S-3 量具正对照：随机对随机，z 必须在 0 附近 ----
    rng = np.random.default_rng(1)
    print('\n【S-3 正对照】随机构型 vs 随机构型：z 分布必须**以 0 为中心**')
    zs = []
    for _ in range(6):
        r0 = rng.integers(0, NV + 1, size=(N, N, N)).astype(np.int8)
        r0[r0 > NV] = 0
        e0 = eel_of(r0)
        er = [eel_of(rand_perm(r0, rng)) for _ in range(6)]
        er = np.array(er)
        z = (e0 - er.mean()) / max(er.std(), 1e-30)
        zs.append(z)
        print('   一次试验：E_obs=%.4e  随机 mean=%.4e  sd=%.3e  **z=%+.2f**'
              % (e0, er.mean(), er.std(), z))
    print('   ⇒ z 的均值 = %+.2f（应 ≈0）、|z| 最大 = %.2f（6 次里不该有 >3）'
          % (float(np.mean(zs)), float(np.max(np.abs(zs)))))
    print('=' * 100)
    sys.exit(0)

if not a.snap:
    cand = sorted(glob.glob(os.path.join(HERE, '_exp', '*', 'snap_*.npz')))
    if not cand:
        print('✗ 找不到快照'); sys.exit(2)
    a.snap = cand[-1]
    print('（未给 --snap ⇒ 取最新的 %s）' % a.snap)

z = np.load(a.snap if os.path.isabs(a.snap) else os.path.join(HERE, a.snap))
reg = z['region'].astype(np.int8)
step = int(z['step']) if 'step' in z else -1
print('快照 %s  step=%s' % (a.snap, step), flush=True)

frac = {k: float((reg == k).mean()) for k in range(NV + 1)}
nz = {k: v for k, v in frac.items() if v > 1e-6}
print('体积分数：%s' % '  '.join('V%d=%.4f' % (k, v) for k, v in sorted(nz.items())))
if len([k for k in nz if k > 0]) < 2:
    print('⚠ 只有 1 个变体 ⇒ **实验 7 的 S-1 无意义**（自协调需要 ≥2 个变体）')

e_obs = eel_of(reg)
rng = np.random.default_rng(a.seed)
er = np.array([eel_of(rand_perm(reg, rng)) for _ in range(a.nrand)])
zsc = (e_obs - er.mean()) / max(er.std(), 1e-30)
pct = float((er < e_obs).mean())

print('\n' + '=' * 100)
print('S-1 弹性能对照（同一体积分数，随机指派变体）')
print('   E_el(观测)      = %.6e J/m³' % e_obs)
print('   E_el(随机) 均值 = %.6e J/m³   标准差 = %.3e   min = %.6e   max = %.6e'
      % (er.mean(), er.std(), er.min(), er.max()))
print('   **z = %+.2f**   （观测在随机分布中的分位 = %.2f）' % (zsc, pct))
eff = e_obs / er.mean() - 1.0
print('   能量降低 = **%+.2f%%**' % (100 * eff))
# ★★ 记账（第 14 轮，**验证跑抓到的判据不一致**）：
#   预注册的 S-1 写的是「用 z 分数**与分位数**报出，**不以"低一点点"当通过**」，
#   但脚本原来**只看 z** ⇒ 在"体积极小、涨落也极小"的早期快照上会给出
#   `z = −17` 却只有 **−2.00%** 的能量差 —— 那是**统计显著但物理可忽略**。
#   ⇒ 判据改成**两条都要**：`z ≤ −2` **且** `|ΔE|/E ≥ 1%`。
# ★★★★ 硬守卫（本轮，独立审计 8df9eefa 的结论）：
#   下面这套 `z` 判据在**两变体臂**（`e7_selfac` / `e7c_badpair`）上**结构性失效**，
#   三条**已核实**的理由（每条都有穷举/实测证据）：
#     ① **`z ≤ −2` 数学上不可达**：6 核 3+3 分给 2 个变体只有 **C(6,3)=20** 个划分；
#        穷举这 20 个的能量 ⇒ `z` 可达范围 **[−1.326, +1.792]**，上界 1.792 **< 2**。
#        这是"构型数只有 20"的样本量上限，**与物理无关**。
#        最小可达单侧 p = 1/20 = 0.050 > 0.0228（`z=−2` 对应值）⇒ p 空间同样不可达。
#     ② **置换在体素级，测的不是自协调**：`rand_perm` 对 `reg>0` 的**体素**打乱标签
#        ⇒ 把**紧凑的核打碎成散斑**。同一物理构型只改置换粒度：
#          核级（整核换标签）：`z = −0.03`、`|ΔE|/E = 0.000%`
#          体素级（本脚本的做法）：`z = −5.98`、`|ΔE|/E = −0.957%`
#        ⇒ 脚本的 z **几乎全部来自"紧凑 vs 散斑"**。**任何**紧凑排布都能拿到大负 z
#        ⇒ 预注册的"坏对"对照臂（`e7c_badpair`）**无法证伪**本量具。
#     ③ **判决随分辨率变号**：同一快照 `E_obs/E_rand−1` 在 N=192 是 **−2.00%（过）**、
#        在 N=96 是 **−0.957%（不过）** ⇒ 1% 门槛落在分辨率噪声量级上。
#   另：`k0_mode='clamped'` 的平均场项在置换下**逐位不变**却抬高分母
#   （引擎 `windowB_pf3d.py:113-115` 自己写明对自协调研究"标准且物理的选择是 `'free'`"）。
#
#   ⇒ **在量具改对之前，本脚本拒绝输出任何 `z` 判决**（硬失败，不静默给数）。
#      正确做法见 `_r1_selfac2.py`：**核级**零分布 + **穷举全部划分**报排名与精确 p，
#      并**先做负对照**（预注册的"坏对"必须拿到高排名，否则量具作废）。
_nv_act = len([k for k in nz if k > 0])
print('\n' + '!' * 100)
print('⛔ **S-1 的 z 判据已被判定结构性失效 —— 本脚本拒绝给出判决**')
print('   活跃变体数 = %d ；已核实的三条理由：' % _nv_act)
print('   ① `z ≤ −2` 在 6 核 2 变体下**不可达**（只有 C(6,3)=20 个划分，穷举上界 1.792）')
print('   ② 置换是**体素级** ⇒ 测的是"紧凑 vs 散斑"，不是自协调（核级置换给 z=−0.03）')
print('   ③ 同一快照的判决**随分辨率变号**（N=192 −2.00% 过 / N=96 −0.957% 不过）')
print('   ⇒ 上面打印的 `z` 与"能量降低 %%" **仅作原始数字保留，不得作为实验 7 的判决**。')
print('   ⇒ 请用 `_r1_selfac2.py`（核级穷举 + 排名 + 精确 p + 负对照）。')
print('!' * 100)

# ★ 自动改道：把本次调用**转交**给修正量具，让队列（`_r1_drive4.sh` 的 `s1()`）
#   不必改脚本就能拿到**正确**的判决。`_r1_selfac2.py` 接受同名的
#   `--snap/--N/--L-um/--nrand/--workers`，所以直接透传 argv 即可。
#   ⚠ 用 `execv` **替换进程**（不留两个 PF3D 实例，避免 4.6 GB ×2 爆内存）。
#   ⚠ 加 `--no-delegate` 可关掉改道，只看本脚本的原始数字。
if '--no-delegate' not in sys.argv:
    _alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_r1_selfac2.py')
    if os.path.exists(_alt):
        print('\n▶ 自动改道到修正量具：`_r1_selfac2.py`（同参数）')
        sys.stdout.flush()
        os.execv(sys.executable, [sys.executable, '-u', _alt] + sys.argv[1:])
    else:
        print('\n⚠ 找不到 `_r1_selfac2.py` ⇒ 不改道，仅上面这些原始数字')

Z_OK = False
EFF_OK = False
if True:
    print('   ⇒ ⏸ **S-1 判决：暂缓**（量具失效，须先修）')
    print('   参考（**不作判决**）：z = %+.2f ；能量差 = %+.2f%%'
          % (zsc, 100 * eff))

# ---- 以下为**旧判据**，已停用（保留以便溯源），不再执行 ----
if False:
    Z_OK = zsc <= -2.0
    EFF_OK = abs(eff) >= 0.01
    if Z_OK and EFF_OK:
        print('   ⇒ ✅ **S-1 通过**（z ≤ −2 **且** 能量差 ≥1%）：有可测的自协调')
    elif zsc >= 2.0 and EFF_OK:
        print('   ⇒ ❌ **S-1 反向**：观测构型**高于**随机 ⇒ 不是自协调')
    elif Z_OK and not EFF_OK:
        print('   ⇒ ⚠ **统计显著但物理可忽略**：|z| 大（%.1f）而能量差只有 %.2f%%'
              '（<1%%）⇒ **不算通过**。多半是活跃体积太小或变体间还没相互作用。'
              % (zsc, 100 * eff))
    else:
        print('   ⇒ ⚠ **S-1 不显著**（z=%.2f ⇒ |z|<2）：观测与随机指派**分不开**'
              ' ⇒ 没有可测的自协调' % zsc)
    print('   判据明细：z ≤ −2 → %s ； |ΔE|/E ≥ 1%% → %s'
          % ('满足' if Z_OK else '不满足', '满足' if EFF_OK else '不满足'))

# ---- S-2：体积分数是否向等分靠拢 ----
vs = np.array([frac[k] for k in range(1, NV + 1) if frac[k] > 1e-6])
if vs.size >= 2:
    fbar = vs.mean()
    dev = np.abs(vs - fbar) / max(fbar, 1e-30)
    print('\nS-2 各变体体积分数：%s' % '  '.join('%.4f' % v for v in vs))
    print('   相对均值 %.4f 的偏差：%s   ⇒ 中位 **%.3f**'
          % (fbar, '  '.join('%.3f' % d for d in dev), float(np.median(dev))))
    print('   （判据：自协调的组织应让活跃变体**大致等分** ⇒ 中位偏差小）')
print('=' * 100)
