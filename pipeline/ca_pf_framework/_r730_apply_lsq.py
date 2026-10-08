#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r730_apply_lsq.py —— **R730：把 LSQ 平面拟合法向接进 `M(n)` 的输入**（默认关）。

## 依据
* `R712_REPAIR_SPEC.md §9.20b` —— "唯一剩下的杠杆"：**局部最小二乘平面拟合**，
  **只用于 `M(n)` 的输入**，**不回灌水平集**。
* `R727_F1_REPAIR_CRITERIA.md` —— 判据 `J-1…J-10`（**动手前已登记**）。
* `R728` —— 箱和 ≠ LSQ（差 2800 倍）⇒ **必须用真 LSQ**。
* `R729` —— 常数 **1/18** 已用**暴力 27 点参考 + `pinv` 参考**双重验证（逐点一致）；
  代价 **+30.3 ms/步 = 单步 +1.05%**。

## 插入点
`windowB_surface.py:4671-4699` 的 `ndir_` 构造（**只读 `pha − phb`、只写 `ndir_`**）。

## 门控（**与 `SEED_CLEAN_EVERY`（`:2654`）同一套做法**）
```
NDIR_LSQ = off | 1       默认 off
```
* **off** ⇒ 整段不进 ⇒ `ndir_` 逐位不变 ⇒ **归档路径零影响**（`J-1`）
* 用**环境变量**而非 CLI ⇒ **不改参数集** ⇒ 不产生 argv diff

## 为什么是"只喂 M(n)"（`J-4` 的机理保证）
`ndir_` 的消费者**仅三处**：`:5252`（`c2b_`）、`:5262`（`c2w_`）、`:5278`（`c2r_`），
全部只进 `M(n)` 的调制因子。**`φ` 在整个 `advance()` 里不被 `ndir_` 写回。**
⇒ 本改动**结构上**不可能回灌水平集。

## 用法
    python3 _r730_apply_lsq.py --dry-run
    python3 _r730_apply_lsq.py
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'windowB_surface.py')

ANCHOR = (
    "            ndir_ = np.stack([g_ / gdn_ for g_ in gd_], -1)\n"
    "            ndir_ = ndir_ / (np.linalg.norm(ndir_, axis=-1, keepdims=True) + 1e-300)\n"
)

BLOCK = '''            # ═══════════════════════════════════════════════════════════════════
            # ★★★★★★ R730 / F-1 修复：**LSQ 平面拟合法向**（`R712 §9.20b` 的"唯一剩下的杠杆"）
            #   ## 症状（本文件 `:4676-4677` 自记）
            #     带内 `|∇d|` 中位只有 **0.70–0.93**（应 ≈1）⇒ 法向有散布
            #     ⇒ 噪声把慢方向的迁移率抬高、压缩各向异性对比。
            #   ## 本改动：把 `ndir_` 从"`∇d` 归一"换成"**27 点最小二乘平面拟合的法向**"
            #     在 `(pha − phb)` 的 **3×3×3 周期窗**内做一阶平面拟合：
            #       `g = c·Σ_x r·(pha−phb)(x)`，`r` = 相对坐标，**c = 1/18**
            #     ⚠ `1/18` 是 `R729` 用**暴力 27 点构造**与 **`pinv` 参考**双重验证的常数
            #       （逐点一致；`R728` 记了我在这条代数上连续四次错，故此处不再手推）。
            #   ## 为什么**不是**箱和（`norm_smooth` 那一路）
            #     `R728 §3`：箱和 ≠ LSQ —— 周期正弦场实测差 **2800 倍**；
            #     球面偏差随 `dx/R` 单调增 ⇒ 是 `O((dx/R)²)` 的**曲率偏置**。
            #   ## 边界：**周期**（`np.roll`）
            #     既有 `par.gradient` 用**盒边界截断**的单边差分，而物理是**周期**的
            #     ⇒ 本路径的边界更自洽。
            #   ## ★ 只喂 `M(n)`、**不回灌 `φ`**（`R712 §9.20b` 明令）
            #     `ndir_` 的消费者仅 `:5252` / `:5262` / `:5278` 三处，全部只进 `M(n)`；
            #     `φ` 在本函数里**不被 `ndir_` 写回** ⇒ **结构上不可能回灌**。
            #   ## 代价（`R729` 实测，N=96 单线程）：**+30.3 ms/步** =
            #     真实单步（`B2P_q0` @100 = 2.89 s/步）的 **+1.05%**
            #   ## 门控（与 `SEED_CLEAN_EVERY`（`:2654`）同一套做法）
            #     `NDIR_LSQ=1` 才进；**不设 ⇒ 整段不进 ⇒ `ndir_` 逐位不变**（归档零影响）
            if os.environ.get('NDIR_LSQ', '').strip() not in ('', '0', 'off'):
                try:
                    _d = np.asarray(pha, float) - np.asarray(phb, float)
                    _c18 = 1.0 / 18.0
                    _axes = []
                    for _tg in range(3):
                        _acc = None
                        for _s in (-1, 1):
                            _a = np.roll(_d, -_s, _tg) * (_s * self.dx)
                            for _ot in range(3):
                                if _ot == _tg:
                                    continue
                                _a = _a + np.roll(_a, 1, _ot) + np.roll(_a, -1, _ot)
                            _acc = _a if _acc is None else _acc + _a
                        _axes.append(_c18 * _acc)
                    _nd = np.stack(_axes, -1)
                    _nn = np.sqrt(np.einsum('...i,...i->...', _nd, _nd)) + 1e-300
                    ndir_ = _nd / _nn[..., None]
                except Exception as _e:                      # noqa: BLE001
                    # ⚠ 记账：失败**不得影响仿真**（N12 教训）——退回原法向并告警一次
                    if not globals().get('_NDIR_LSQ_WARNED', False):
                        globals()['_NDIR_LSQ_WARNED'] = True
                        try:
                            print('  ⚠ NDIR_LSQ 失败，退回原法向（不影响仿真）: %s' % _e,
                                  flush=True)
                        except Exception:
                            pass
            # ═══════════════════════════════════════════════════════════════════
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    src = open(TARGET, encoding='utf-8').read()
    n = src.count(ANCHOR)
    print('锚点命中 = %d 处（应为 1）' % n)
    if n != 1:
        print('⛔ 锚点不唯一 ⇒ 中止（不猜）')
        return 3
    if 'NDIR_LSQ' in src:
        print('⛔ 文件里已有 NDIR_LSQ ⇒ 可能已插入过 ⇒ 中止')
        return 4
    out = src.replace(ANCHOR, ANCHOR + BLOCK, 1)
    print('插入后 +%d 字符（%d → %d）' % (len(out) - len(src), len(src), len(out)))
    if a.dry_run:
        print('--- dry-run：未写盘 ---')
        return 0
    bak = TARGET + '.lsqorig'
    if not os.path.exists(bak):
        shutil.copy2(TARGET, bak)
        print('已备份 → %s' % os.path.basename(bak))
    with open(TARGET, 'w', encoding='utf-8', newline='') as f:
        f.write(out)
    print('✅ 已写入 %s' % os.path.basename(TARGET))
    return 0


if __name__ == '__main__':
    sys.exit(main())
