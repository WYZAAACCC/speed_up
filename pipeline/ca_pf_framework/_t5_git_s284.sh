#!/bin/bash
# _t5_git_s284.sh --- ★★★★★★ burst 修复已实施（KM 分数律；门控 --burst-km，默认档逐位不变）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_patch_burstkm.py pipeline/ca_pf_framework/_t5_fix_burstkm.py \
        pipeline/ca_pf_framework/_t5_burstcode.sh pipeline/ca_pf_framework/_t5_git_s283.sh 2>/dev/null
git add -u pipeline/ca_pf_framework/_bk_exp.py 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s284 ★★★★★★ **burst 修复已实施**：线性律 → **KM 分数律**（门控 `--burst-km`，默认档逐位不变）

## 一、用户要求（总目标第 4 项）
> 「**当前的 burst 不是物理正确的**，请你将其修复至物理正确」

## 二、★ 改动内容（`_bk_exp.py:2576` 附近）
```python
# 原文（**线性于 ΔT ⇒ 恒定速率 ⇒ 无 burst**）：
_n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))

# 现改为（由 `--burst-km` 门控，**默认 0**）：
if bool(int(getattr(a, 'burst_km', 0) or 0)):
    _N_end = float(CL.alpha_km_n_lath(float(getattr(a, 'T_end', 298.0) or 298.0), _alpha))
    _f_km  = 1.0 - np.exp(-_alpha * max(M_S_TI64 - _Tnow, 0.0))      # ← **KM 分数律**
    _n_blk = int(round(_N_end * _f_km))
else:
    _n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))  # ← **原式逐字**
```
★ 依据：`windowB_km.py:232` 的 `koistinen(T, Ms, alpha) = 1 - exp(-alpha*(Ms - T))`
  —— **模块里已有**这个函数，只是**没被用于形核调度**。
★ `M_S_TI64` **已导入**（`_bk_exp.py:49`）⇒ 无需新 import。
★ `N_end = alpha_km_n_lath(T_end, α)` = **23**（每块）。

## 三、★ 预期效果（**修前已算好**）
```
温度档 | αΔT | f(T)  | **每档增量**      | 现状（线性）
 第 1  | 1.0 | 0.632 | **63.2%** ← **爆发** | 4.3%
 第 2  | 2.0 | 0.865 | **23.2%**            | 4.3%
 第 3  | 3.0 | 0.950 | **8.5%**             | 4.3%
 第 4  | 4.0 | 0.982 | **3.1%**             | 4.3%
 …     | …   | →1    | **指数衰减 ⇒ 饱和**  | 恒定
```
⇒ **Ms 处爆发 + 随后饱和 = athermal 马氏体的物理正确行为** ✓

## 四、★ 安全性（**逐条**）
```
① **默认档（`--burst-km 0`）逐字走原式** ⇒ 归档与**在跑的 `t5B6np`（未传该参数）
   逐位不变** ✓
② 语法编译通过 ✓ ｜ 已备份 `_bk_exp.py.bak_burstkm` ✓ ｜ 四道自检全过 ✓
③ 文件已写盘：sha256 `496a9892…` → **`6c564ad6…`**（210749 → 212291 字节）
```

## 五、⚠ 记账：**第一次尝试失败并被自检拦住**
```
★ 第一版 `_t5_patch_burstkm.py` 用**单行正则**匹配 `--nuc-block-target` 的 `add_argument`，
  而它**跨多行** ⇒ 新选项被插到**调用中间** ⇒ `SyntaxError (line 3688)`
  ⇒ **patcher 在写盘前退出** ⇒ **`_bk_exp.py` 未被改动** ✓（**自检起作用**）
★ 第二版 `_t5_fix_burstkm.py` 改用**括号配平**定位调用结尾 ⇒ **成功** ✓
★ **新纪律（第十四次记账）**：`add_argument(...)`（及任何可能跨行的调用）
  **一律用括号配平定位，不用单行正则** —— 与本仓"改 MOOSE 输入块必须行首锚定"同族。
```

## 六、预登记判据（**s282 已写死，此处复述**）
```
① **首档核数应占总量 ~63%**（现状 `1/23 = 4.3%`）;
② **每档核数应指数衰减**（现状**恒定 3 个**）;
③ 复用引擎**已有**的 "burst regime" 记账串做正对照（`_bk_exp.py:1174`）;
④ 核数序列与 `N_end·Δf(T_k)` 在 **±15%** 内一致。
```

## 七、➡ 下一步
```
① 给 `_t5_short.py` 加 **`--burst-km` 透传**（同本会话已验证的三个 patcher 法）;
② **两臂对照**（`--burst-km 0` vs `1`）⇒ 按第六节四条判据验收;
③ **复核 `t5B6np` 到 step 400/600**（`pwsh-3715` 自动报）⇒ 确认自协调假说否证;
④ 查**线索 B**（弹性罚能标定：实测 `df(Ms)/(|ed|+2γ/t) = **0.379**`；
   物理约束锁死修法为"**降低弹性罚能**"，因 `Ms = 873 K` 是 CALPHAD 事实）
   ⇒ ★ 用**引擎内形状对照**（同 `ε⁰`/`C`，只改薄板 vs 球体）判"是否实现有问题"
     （**新纪律 s275**：不用外部解析模型）;
⑤ 全部修完 ⇒ **按原条件起重跑 + 七项监控 + 三维视觉图**。
```

## 八、当前代码状态（**交接必读**）
```
★ `_bk_exp.py`     = **含 burst 修复**（门控 `--burst-km`，**默认 0 ⇒ 逐位不变**）
★ `windowB_surface.py` = **无补丁版**（`t5B6np` 正在用）
   · `.bak_bothpatches` = 含两处 `supercrit` 补丁 ｜ `.bak_attachsc` = 只有 stack 补丁
   ⇒ **接手第一步先数 `sc_stack_pass`/`sc_att_pass` 确认版本**;
★ `t5B6np`（无补丁版 · --B 6）：末步 **200** ⇒ 到 400/600 复核需 ~20–40 分钟。
```
MSGEOF
git log --oneline -1
