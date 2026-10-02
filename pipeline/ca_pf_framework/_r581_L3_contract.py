#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L3_contract.py --- L3 车道：`el.sig.contract`（**15.90% 墙钟**，当前最大单项）候选微基准。

## 被测对象（`windowB_pf3d.py:561`）
```python
sh = -np.einsum('kpq,qk->pk', self.Lam, Eh)      # Eh = self._epsh(idx).reshape(6, -1)
```
探针（`_r581_probe.py`）实测的真实布局：
* `Lam`  **(N³, 6, 6) float64**（288 B/模式）
* `Eh`   **(6, N³) complex128**（96 B/模式）
* `sh`   **(6, N³) complex128**
契约：`sh[p,k] = Σ_q Lam[k,p,q]·Eh[q,k]` —— 即 **N³ 个 6×6 实矩阵 × 6 复矢量**。

## 为什么它慢（不是带宽问题）
N=64 时流量 ≈ 100 MB 读 + 25 MB 写 = 125 MB，实测 0.0396 s ⇒ **3.2 GB/s**
⇒ 远低于内存带宽 ⇒ **是 `c_einsum` 的通用逐元素循环在拖**。

## 候选（**先量后改**；逐位是硬判据）
| # | 候选 | 预期 |
|---|---|---|
| C0 | `einsum('kpq,qk->pk')`（归档） | 基准 |
| C1 | 手工 q 循环：`sh = Lam[:,:,0]*Eh[0][:,None]` 然后 `+=` q=1..5，末尾 `.T` | 期望大提速 |
| C2 | 同 C1 但先 `.T` 布局（`(6,K)` 累加） | 可能更快/更慢 |
| C3 | `einsum(..., optimize=True)` | 走 tensordot/BLAS |
| C4 | `np.matmul`（(K,6,6) @ (K,6,1)） | BLAS，**大概率不逐位** |
| C5 | 拆实虚 + 两次实 matmul | BLAS |
| NC-1 | q 顺序倒过来 | 必须非零（否则判据没分辨力） |
| NC-2 | 把 `Lam[:,:,q]` 写成 `Lam[:,q,:]`（转置错） | 必须非零 |

⚠ **记账**：本脚本的 `Lam`/`Eh` 用 `default_rng` **合成**（形状/dtype 与真值一致）——
契约的代价只取决于形状与 dtype，逐位判据对任意数据都成立。
另用探针存下的 **N=32 真实数据**（`_r581_probe_Lam.npy`，若存在）做一次交叉确认。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

REPS = 9


def c0(Lam, Eh):
    return -np.einsum('kpq,qk->pk', Lam, Eh)


def c1(Lam, Eh):
    """手工 q 循环（(K,6) 累加，末置转置）。"""
    sh = Lam[:, :, 0] * Eh[0][:, None]
    for q in range(1, 6):
        sh += Lam[:, :, q] * Eh[q][:, None]
    return -sh.T


def c2(Lam, Eh):
    """手工 q 循环（先把 Lam 转成 (6,6,K)，在 (6,K) 布局上累加）。"""
    Lt = np.ascontiguousarray(Lam.transpose(2, 1, 0))      # (q,p,k)
    sh = Lt[0] * Eh[0]
    for q in range(1, 6):
        sh += Lt[q] * Eh[q]
    return -sh


def c3(Lam, Eh):
    return -np.einsum('kpq,qk->pk', Lam, Eh, optimize=True)


def c4(Lam, Eh):
    return -np.matmul(Lam, Eh.T[:, :, None])[..., 0].T


def c5(Lam, Eh):
    Er = np.ascontiguousarray(Eh.real)
    Ei = np.ascontiguousarray(Eh.imag)
    def mv(E):
        s = Lam[:, :, 0] * E[0][:, None]
        for q in range(1, 6):
            s += Lam[:, :, q] * E[q][:, None]
        return s
    return -(mv(Er) + 1j * mv(Ei)).T


def nc1(Lam, Eh):
    sh = Lam[:, :, 5] * Eh[5][:, None]
    for q in range(4, -1, -1):
        sh += Lam[:, :, q] * Eh[q][:, None]
    return -sh.T


def nc2(Lam, Eh):
    """NC-2：把 `Lam[k,p,q]` 误写成 `Lam[k,q,p]`（p/q 弄反）—— 形状对、语义错。"""
    sh = Lam[:, 0, :] * Eh[0][:, None]
    for q in range(1, 6):
        sh += Lam[:, q, :] * Eh[q][:, None]
    return -sh.T


ARMS = [('C0 einsum(归档)', c0), ('C1 手工q循环', c1), ('C2 手工q(转置布局)', c2),
        ('C3 einsum optimize', c3), ('C4 matmul', c4), ('C5 拆实虚', c5)]
NEG = [('NC-1 q 顺序倒过来', nc1), ('NC-2 Lam 转置错', nc2)]


def mk(K, seed=0):
    rng = np.random.default_rng(seed)
    Lam = rng.normal(size=(K, 6, 6))
    Eh = rng.normal(size=(6, K)) + 1j * rng.normal(size=(6, K))
    return Lam, Eh


def main():
    L = ['=' * 100,
         'R581-L3 —— `el.sig.contract`（15.90% 墙）候选微基准',
         '=' * 100]
    fails = []
    for tag, Lam, Eh in [('合成 N=64 (K=%d)' % 64 ** 3, *mk(64 ** 3)),
                         ('合成 N=128 (K=%d)' % 128 ** 3, *mk(128 ** 3))]:
        ref = c0(Lam, Eh)
        L.append('')
        L.append('── %s ──' % tag)
        L.append('  ── P1 逐位（`array_equal`，max|Δ| 必须 == 0.0）──')
        for nm, fn in ARMS:
            try:
                got = fn(Lam, Eh)
            except Exception as e:
                L.append('    %-22s ⚠ 抛异常 %s: %s' % (nm, type(e).__name__, str(e)[:50]))
                continue
            neq = int(np.count_nonzero(got != ref))
            md = float(np.max(np.abs(got - ref))) if neq else 0.0
            sc = float(np.max(np.abs(ref))) or 1.0
            L.append('    %-22s max|Δ|=%.3e (相对 %.1e)  不等=%d  %s'
                     % (nm, md, md / sc, neq, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
        L.append('  ── P2 负对照（**必须非零**）──')
        for nm, fn in NEG:
            got = fn(Lam, Eh)
            neq = int(np.count_nonzero(got != ref))
            L.append('    %-22s 不等=%d  %s'
                     % (nm, neq, '✅ 有分辨力' if neq else '❌ **判据失效**'))
            if neq == 0:
                fails.append('%s/%s 恒 0' % (tag, nm))
        # 计时：交错、臂序轮换
        ts = {nm: [] for nm, _ in ARMS}
        for r in range(REPS):
            order = ARMS[r % len(ARMS):] + ARMS[:r % len(ARMS)]
            for nm, fn in order:
                t0 = time.perf_counter(); fn(Lam, Eh)
                ts[nm].append(time.perf_counter() - t0)
        tb = sorted(ts['C0 einsum(归档)'])[REPS // 2]
        L.append('  ── P4 计时（%d 轮，交错、轮换；中位）──' % REPS)
        for nm, _ in ARMS:
            v = sorted(ts[nm]); m = v[REPS // 2]
            L.append('    %-22s 中位 %7.4f s  区间 [%.4f, %.4f]  提速 **%6.3f×**'
                     % (nm, m, v[0], v[-1], tb / m))

    # ---- 真实数据交叉确认 --------------------------------------------------
    if os.path.exists('_r581_probe_Lam.npy'):
        Lam = np.load('_r581_probe_Lam.npy'); Eh = np.load('_r581_probe_Eh.npy')
        ref = c0(Lam, Eh)
        L.append('')
        L.append('── 交叉确认：N=32 **真实** Lam/Eh（探针存下）──')
        for nm, fn in ARMS[:3]:
            got = fn(Lam, Eh)
            neq = int(np.count_nonzero(got != ref))
            L.append('    %-22s 不等=%d  %s'
                     % (nm, neq, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
            if neq:
                fails.append('真实数据 %s' % nm)
    L.append('')
    L.append('=' * 100)
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 判据全部通过（见上逐项）')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L3_contract.log', 'w').write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
