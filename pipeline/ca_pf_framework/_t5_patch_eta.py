#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_eta.py --- ★★★★★★ 实施**修法 A**：弹性罚能折减因子 `η`（塑性弛豫 / TRIP）

## 依据（本会话已逐层排除后锁定，见 `s289` 提交）
```
【实测】薄板弹性罚能 `|ed|` = **2.96e8 J/m³**（**dx 对照已证是物理量**，非欠解析）
【对比】Ms 处化学驱动力 `df(Ms = 873 K)` = **1.128e8 J/m³**
        ⇒ **罚能是驱动力的 2.6 倍** ⇒ **核放下即溶解** ⇒
          **体积流失 −40~87% · "一场多根板条" · 长宽比退化** ✓
【物理】真实马氏体靠**塑性弛豫（TRIP）**把相变应变能耗散掉 ⇒ 储存的弹性能 ≲1.1e8;
        而**本模型是纯线弹性**（无塑性）⇒ 应变能**全部储存** ⇒ 高估 ~3 倍。
【用户选择】（本会话 s25 轮）「**先算薄板理论罚能，再定改 `Ms` 还是改弹性**」
        ⇒ 算完了 ⇒ 结论：**改弹性**（`Ms = 873 K` 是 CALPHAD 事实，**不能改**）。
```

## 本 patch 做什么（**最小、可门控、默认逐位不变**）
在速度律那一行引入折减因子 `η`：
```python
dG_cell = (df_k − df_l) + **η**·(ed_k − ed_l) − stk·κ
```
* **`η = 1.0`（默认）⇒ 与原文**逐字等价** ⇒ 归档与在跑的臂**逐位不变** ✓
* **`η < 1`（如 0.35–0.45）** ⇒ 只保留一部分弹性储存能，其余视为**塑性耗散**
  ⇒ **物理对应**：TRIP / 位错滑移吸收的份额

## 理论标定（**预先算好，用于验收**）
```
目标：`df(Ms) / (η·|ed|_plate + 2γ/t) ∈ [0.8, 1.3]`
  ⇒ `η·2.96e8 + 1.6e6 ≈ 1.128e8` ⇒ **η ≈ (1.128e8 − 1.6e6)/2.96e8 ≈ 0.375**
  ⇒ 取 **η ≈ 0.35–0.45**（预期使板条在 Ms 处站得住）
```

## 四道自检
1. 锚点唯一；2. `compile()` 通过；3. 新配置键存在且默认 1.0；
4. **默认档逐字等价**（`η = 1.0` 时表达式与原文相同）。
"""
import hashlib
import os
import shutil
import sys

P = 'windowB_surface.py'
BAK = P + '.bak_eta'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = """            dG_cell = (self.df[karr] - self.df[larr]) + (edk - edl) - stk * kap_cell"""
NEW = """            # ★★★★★★ s290（**修法 A：弹性罚能折减因子 η**，物理对应**塑性弛豫 / TRIP**）
            #   依据：薄板 `|ed|` = **2.96e8**（dx 对照已证是**物理量**）而
            #         `df(Ms = 873 K)` = **1.128e8** ⇒ 罚能是驱动力的 **2.6 倍**
            #         ⇒ 核放下即溶解。真实马氏体靠**塑性弛豫**耗散应变能 ⇒ 储存 ≲1.1e8;
            #         本模型**纯线弹性（无塑性）** ⇒ 应变能全部储存 ⇒ **高估 ~3 倍**。
            #   ⇒ 本行引入 `η`：`dG = Δdf + η·Δed − γκ`
            #     · `η = 1.0`（**默认**）⇒ **与原文逐字等价** ⇒ 归档与在跑的臂**逐位不变** ✓
            #     · `η < 1` ⇒ 只保留 η 份弹性储存能，其余视为**塑性耗散**（TRIP）
            #   ★ 理论标定：`df(Ms) ≈ η·2.96e8 + 2γ/t` ⇒ **η ≈ 0.375**（取 0.35–0.45）
            #   ★ 验收判据：**`df(Ms)/(η·|ed|_plate + 2γ/t) ∈ [0.8, 1.3]`**
            #     且 `|ed|` 的**变体间差异必须保留**（否则失去取向选择的物理）
            dG_cell = ((self.df[karr] - self.df[larr])
                       + float(getattr(self, 'ed_eta', 1.0) or 1.0) * (edk - edl)
                       - stk * kap_cell)"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)

# 类属性默认（在 __init__ 里，`self.df` 那一带）
ANCH = "        self.df = np.zeros(self.nreg) if df is None else np.asarray(df, float)"
if ANCH not in out:
    print('  ❌ 找不到 `self.df` 锚点 ⇒ 拒绝修改'); sys.exit(1)
out = out.replace(ANCH, ANCH + "\n"
                  "        # ★ s290：弹性罚能折减因子 η（**塑性弛豫/TRIP**）；默认 **1.0** ⇒ 逐位不变\n"
                  "        self.ed_eta = 1.0", 1)

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ("getattr(self, 'ed_eta', 1.0)", "self.ed_eta = 1.0"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print()
print('  ── 复核 ──')
print('     * `ed_eta = 1.0`（默认）⇒ `1.0 * (edk - edl)` ⇒ **与原文逐字等价** ✓')
print('     * 设定方式：引擎侧需把 `g.ed_eta` 设为 η（下一步加透传）')
print('     * 理论标定：**η ≈ 0.375**（使 `df(Ms) ≥ η·|ed| + 2γ/t`）')
