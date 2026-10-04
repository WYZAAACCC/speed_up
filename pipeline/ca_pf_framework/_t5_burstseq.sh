#!/bin/bash
# _t5_burstseq.sh --- ★★★★★★ burst 修复的**每档核数序列**（判据②指数衰减 + ④ ±15%）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
printf '  t5BK1（KM 分数律）：末步 = %s ｜ 事件 = %s ｜ 进程 = %s\n' \
  "$(tail -1 _exp/_bk_t5/dry_t5BK1/series.csv 2>/dev/null | cut -d, -f1)" \
  "$(grep -cE '模式 \*\*' _w2_t5_short_t5BK1.log 2>/dev/null)" \
  "$(ps -eo args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -c -- '--tag t5BK1')"
echo
echo '════ ★ 判据①：每档核数分布（KM 分数律臂）════'
grep -oE 'T=[0-9.]+ K' _w2_t5_short_t5BK1.log 2>/dev/null | sort -t= -k2 -n | uniq -c | sed 's/^/  /'
echo
echo '════ 对照：A 臂（t5N276F，线性律）的每档核数 ════'
grep -oE 'T=[0-9.]+ K' _w2_t5_short_t5N276F.log 2>/dev/null | sort -t= -k2 -n | uniq -c | head -12 | sed 's/^/  /'
echo
echo '════ ★ 理论预期（KM 分数律，N_end = 23 每块，B = 3）════'
$PY - <<'PYEOF'
import numpy as np
alpha = 0.041739
dT = 23.958
Ms = 873.0
N_end = 23.0
B = 3
print('  档 k | αΔT | f(T)   | 累计核数/块 | **增量/块** | **增量全盒(=×B)** | 占比')
prev = 0.0
for k in range(1, 8):
    aDT = alpha * dT * k
    f = 1.0 - np.exp(-aDT)
    n_cum = N_end * f
    d_n = n_cum - prev
    prev = n_cum
    print('   %-3d | %-4.1f | %.4f | %-11.2f | **%-9.2f** | **%-15.1f** | %.1f%%'
          % (k, aDT, f, n_cum, d_n, d_n * B, 100.0 * d_n / N_end))
print()
print('  ⇒ **首档应 ~63%%（每块 ~14.5 根 ⇒ 全盒 ~44 根）**，随后 **23.2%% → 8.5%% → 3.1%% …**')
print('  ⇒ 对照 A 臂（线性律）：**每档恒定 1 个事件**')
PYEOF
echo
echo '════ 判据③：引擎自己的 "burst regime" 记账串 ════'
grep -nE 'burst regime|burst' _w2_t5_short_t5BK1.log 2>/dev/null | head -5 | cut -c1-165 | sed 's/^/  /'
echo '  （对照 A 臂）'
grep -nE 'burst regime' _w2_t5_short_t5N276F.log 2>/dev/null | head -3 | cut -c1-165 | sed 's/^/  /'
free -m | sed -n 2p | sed 's/^/  /'
