#!/bin/bash
# _t5_git_s282.sh --- ★★★★★★ burst 修复设计（改动点已精确定位 + 预期数值 + 预登记判据）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_burstcode.sh pipeline/ca_pf_framework/_t5_q72.sh \
        pipeline/ca_pf_framework/_t5_git_s281.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s282 ★★★★★★ **burst 修复设计**（改动点已定位 · 预期数值已算 · 判据已预登记）

## 一、用户要求（总目标第 4 项）
> 「如果找到问题所在并且确认修复之后就开始修复 burst，
>   **当前的 burst 不是物理正确的**，请你将其修复至物理正确」

## 二、★★★★★ 代码的三条关键事实（逐行核对）
### ① **KM 分数律**已经存在**（`windowB_km.py:232`）
```python
def koistinen(T, Ms=M_S_TI64, alpha=None, f_end=None):
    """Koistinen–Marburger 分数 f(T) = 1 - exp[-alpha (Ms - T)]（T<Ms）。"""
    f = 1.0 - np.exp(-alpha * np.maximum(Ms - T, 0.0))
```

### ② ⚠ **但形核调度用的是**线性**式，不是它**（`_bk_exp.py:2576–2581`）
```python
2576:  _n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))
2578:      _tgt = min(_Bt * _n_blk, nv)
2581:  while n_ath_tgt < _tgt and n_ath_tgt < nv:
```
★ `α·ΔT_step = 0.041739 × 23.958 = 1.0` ⇒ `_n_blk` **每档 +1** ⇒ `_tgt` **每档 +B**
⇒ **恒定速率 ⇒ 没有 burst** ✓（与用户判断一致）

### ③ ★★★ **代码自己写明**了这个缺口（`_bk_exp.py:1781–1782` 逐字）
```
⚠ 所以本开关**不是**在"造 burst 律" —— 它只是把"一次调用能放几个"
  这个**表示上限**暴露成参数。**burst 的定量率律仍然没有**（§改 3 纪律）。
```
⇒ **用户"当前 burst 不物理正确"的判断被代码**逐字确认**** ✓

## 三、★★★★★ 物理正确的形式与**精确改动点**
```
【现状】`_tgt = B · floor(alpha_km_n_lath(T))` —— **线性于 ΔT** ⇒ 恒定速率
【应为】KM **分数律**（模块里已有 `koistinen()`，只是没被用于形核调度）
    `f(T) = 1 − exp(−α(Ms − T))` ⇒ `N(T) = N_total · f(T)`
    ⇒ 每档增量 `ΔN_k = N_total · [f(T_k) − f(T_{k−1})]`
【数值验证（α = 0.041739 /K，ΔT_step = 23.958 K）】
    首档 `α·ΔT = 1.0` ⇒ `f = 0.632` ⇒ 增量 **63.2%**   ← ★ **爆发**
    次档 `α·ΔT = 2.0` ⇒ `f = 0.865` ⇒ 增量 **23.2%**
    三档 `α·ΔT = 3.0` ⇒ `f = 0.950` ⇒ 增量 **8.5%**
    四档 ⇒ **3.1%** …（**指数衰减 ⇒ 饱和**）
  ⇒ **这才是 athermal 马氏体的 burst（Ms 处爆发 + 随后饱和）** ✓
【改动点】**`_bk_exp.py:2576–2578`**（**一处表达式**）
    · 现：`_n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))`
    · 改：`_n_blk = int(round(_N_per_block * KM.koistinen(_Tnow, M_S_TI64, _alpha)))`
      （`_N_per_block = CL.alpha_km_n_lath(T_end, _alpha)` = **23**）
    ⇒ **`_tgt = min(_Bt · _n_blk, nv)` 保持不变**，只换 `_n_blk` 的来源。
★ 改动小、用模块**现成函数**、符合"往真实物理靠拢"与"最小改动"两条纪律。
```

## 四、★ 预登记判据（**修前写死**）
```
① **首档核数应占总量 ~63%**（现状为 `1/23 = 4.3%`）;
② **每档核数应指数衰减**（现状**恒定 3 个**）;
③ 复用引擎**已有**的 "burst regime" 记账串做**正对照**
   （`_bk_exp.py:1174`：`'  ⚠ **违反 ⇒ 本次运行处于 burst regime，必须记账**'`）;
④ 修后验收：**核数序列**（每档）应与 `N_total·Δf(T_k)` 在 **±15%** 内一致。
```

## 五、执行顺序（**按用户总目标**）
```
① **先等 `t5B6np` 到 step ≥400**（`pwsh-3715` 自动报）⇒ 定论"自协调假说"是否成立
   （决定"一场多根"的**主因**归属：线索 A「变体数/自协调」还是
     线索 B「`df(Ms)/|ed| = 0.379` 的量级不匹配」）;
② **然后修 burst**（改动点已定位：`_bk_exp.py:2576`）⇒ 按第四节的四条判据验收;
③ 修完后**按原条件起重跑** ⇒ **七项监控 + 三维视觉图**。
```

## 六、当前运行与代码状态
```
★ `t5B6np`（无补丁版 · --B 6）：末步 **180** · 健康（日志实时写入、CPU 时间增长）·
   最新快照 step 160 ⇒ 到 400 约 **~20 分钟**;
★ `windowB_surface.py` = **无补丁版**（`t5B6np` 在用）
   · `.bak_bothpatches` = 含两处补丁（`sc_stack_pass=2`/`sc_att_pass=2`）
   · `.bak_attachsc`    = 只有 stack 补丁
   ⇒ **接手第一步先数 `sc_stack_pass`/`sc_att_pass` 确认版本**;
★ **十三次口径/纠正提醒已记账**。
```
MSGEOF
git log --oneline -1
