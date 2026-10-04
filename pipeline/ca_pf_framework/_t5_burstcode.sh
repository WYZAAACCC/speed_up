#!/bin/bash
# _t5_burstcode.sh --- ★★★★★★ 读 burst/形核速率律的实现（为"修 burst 至物理正确"定位改动点）
#
# ## 你的要求（第 4 项）
# 「如果找到问题所在并且确认修复之后就开始修复 burst，**当前的 burst 不是物理正确的**，
#   请你将其修复至物理正确」
#
# ## 我已有的分析（待与代码核对）
# * 现状：`n(T) = floor(α_KM·(M_s − T))` ⇒ 与 ΔT **线性** ⇒ 每个温度档增量恒定
#   （`α·ΔT_step = 0.041739 × 23.958 = 1.0` ⇒ n 每档 +1 ⇒ `_tgt = B·n` 每档 +B=3）
#   ⇒ **没有 burst**（恒定速率）。
# * 物理正确：KM **分数律** `f(T) = 1 − exp(−α(M_s − T))`
#   ⇒ 核数 `N(T) = N_total · f(T)` ⇒ **每档增量 ΔN 在 Ms 处最大、随后指数衰减**
#   ⇒ 首档：`f = 1 − exp(−1) = 0.632` ⇒ **63% 的核在**第一档**爆发** ✓
#     次档：`f = 1 − exp(−2) = 0.865` ⇒ 增量 23% ｜ 再次 8.5% ｜ 再 3.1% …
#   ⇒ **这才是 athermal 马氏体的 burst（Ms 处爆发 + 随后饱和）**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `n(T)` / `n_ath_tgt` / `_tgt` 的计算处 ════'
grep -nE 'n_ath_tgt|_tgt *=|n_target|alpha_km|ALPHA_KM' _bk_exp.py 2>/dev/null | head -20 | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ② `athermal` 形核律的定义（`windowB_km.py`）════'
grep -nE 'def .*athermal|def n_of_T|def frac|def f_of_T|alpha' windowB_km.py 2>/dev/null | head -16 | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ③ burst 相关（`burst`/`nuc-law`/`--B`）的实现处 ════'
grep -nE 'burst|nuc_law|nuc-law|每档|B \* |\* n\(' _bk_exp.py 2>/dev/null | head -16 | cut -c1-170 | sed 's/^/  /'
echo
echo '════ ④ 实测：`t5N276F` 的形核事件随温度档的分布（看是否"恒定 3 个/档"）════'
grep -oE '@ step [0-9]+：T=[0-9.]+ K' _w2_t5_short_t5N276F.log 2>/dev/null | head -20 | sed 's/^/  /'
echo '  ── 每档事件数统计 ──'
grep -oE 'T=[0-9.]+ K' _w2_t5_short_t5N276F.log 2>/dev/null | sort | uniq -c | head -12 | sed 's/^/  /'
