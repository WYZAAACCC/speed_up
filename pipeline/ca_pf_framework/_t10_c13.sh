#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== t10B9 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10B9 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo -n "  形核事件行 = "; grep -ac 'athermal 形核' _w2_t5_short_t10B9.log 2>/dev/null
echo -n "  块数 = "; grep -ao '共 [0-9]* 块' _w2_t5_short_t10B9.log 2>/dev/null | tail -1
echo -n "  ★ protected 含 0 = "; grep -a '\[SEEDCARVED\]' _w2_t5_short_t10B9.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_blockcount_derive.py pipeline/ca_pf_framework/_t10_rac_derive.py
git commit -q -F - <<'MSG'
★ goal② 推导推进：自催化范围 r_ac 与「自然块数」的可复现推导（_t10_rac_derive.py）

(1) **先排除错阈值**：热涨落密度 k_BT/V_l = 4.60e-2 J/m³ vs 弹性能密度 μ‖devε⁰‖² = 5.33e8 J/m³ ⇒ 差 **10 个数量级** ⇒ 马氏体是 athermal，热激活不是此处的门槛（D1 PASS）。故阈值取形核门槛本身 f_crit = 2γ/t_nuc = 1.28e6 J/m³（与引擎同口径）。
(2) **r_ac = (μ‖devε⁰‖²·V_l / f_crit)^(1/3) = 4.734 µm**（D2 PASS；r_ac/L = 0.473，L=10 µm）。
(3) **自然块数 = V_box/((4/3)π r_ac³) = 2.25 个**；仿真实测（B=3 那跑）nblk = 16、B=9 规定值 9 ⇒ **仿真/自然 = 7.1 倍 ⇒ 不一致 ⇒ 定量证据支持用户的质疑「块数是规定值、不是涌现」**（D3 的 FAIL 正是期望的证据方向）。
(4) 反解表（供 goal③ 判据）：自然块数 2/9/16/200 分别需 r_ac = 4.92/2.98/2.46/1.06 µm ⇒ 要让块数涌现成 9–16 个，需要有效 r_ac ≈ 2.5–3 µm，即**近场/结构化应力把远场 r_ac 压小约 2 倍** —— 这是可检验的目标。

★ 自查记账：第一版脚本有单位 bug —— `L = 1000e-6` 把盒边长写成 1 mm（实为 10 µm = 1e-5 m），使 n_nat 虚高 1e6 倍（报 2.25e6）。已修（第 15 次自查）。
★ 另记账：windowB_closure 提供 G_TI64 = 4.254e10 Pa（有出处），而我用了立方 C 的 Voigt 平均 μ=2.64e10；改用 G_TI64 会使 r_ac 大 1.17×（≈5.55 µm）⇒ 自然块数更少（≈1.4）⇒ **结论方向稳健**。
⚠ γ=0.20 J/m² 为占位值（待核出处），r_ac ∝ γ^(−1/3) ⇒ 本结论是量级判断。

另：C2 判据（由 ε⁰ 主拉伸方向聚类成 6×2）**设计错误已撤回** —— 12 变体由立方对称相联系、特征值与最大主拉伸方向相同 ⇒ 代理量退化；惯习面法向须由 {011}_β 直接构造，且**从 ε⁰ 无法唯一反解惯习面** ⇒ 该判据在当前数据下不可算（C1 的 6×2=12 代数计数已覆盖）。
MSG
git log --oneline -1
