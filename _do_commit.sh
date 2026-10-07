#!/bin/bash
cd /mnt/f/speed_up || exit 1
cat > /tmp/_cm.txt <<'EOF'
T1.1/T1.2 收口 + T2.1a 变体选择判据 + T4.1 求解器选型判决

T1.1/T1.2（1D 生产公式仪器）
- 修三个"静默给错答案"的仪器缺陷：非法 dtmin（MOOSE 未使用参数检查在
  executeExecutioner 开头 ⇒ 算例 6 s 内全灭）；自适应 dt 是精度回退
  （c_int 从 -14.0% 变 -49.1%（dt ~1e-6 s ≫ 边界层弛豫时间的 1/3））；
  目录复用读到旧剖面 ⇒ 一度得出"行程已收敛、逐位相同"的假结论。
- A0/A2 逐位复现 README §8.2；A4 现在收敛（固定 dt + nl_max_its=120）；
  ALPHA* ≈ 2.58（两点夹住，实测）。
- ★ ALPHA 与 W_F 只有乘积是物理量：A2/W4µm 与 A4/W2µm 逐位相同；
  生产 2×2µm = 4µm = η 界面宽 ⇒ 已等价于"系数 1 × 界面宽"。
- 判据 3（解析剖面对账）FAIL 且失败方式有信息量：c_int 对上时液相侧有
  +143% 溶质尖峰 ⇒ 不存在能同时满足 c_int 与剖面形状的 ALPHA。
- ⚠ 界面成分在 dx=1µm 上有 ±半格（≈22%）歧义 ⇒ 该 dx 上标定不了 ALPHA。

T2.1a 变体选择判据（新增 _chk_t21a.py，8 条）
- LevelSetMulti 新增 sigma_ext（默认 None ⇒ 行为逐位不变）。
- ★ 解析：单轴应力把 12 变体精确分成 8 优/4 劣，类内 w_v 完全简并 ⇒ 外载
  只能选出"族"（集束），选不出单个变体；spearman 在此不是有效判据。
- PF 实测：top8 == {w_v>0}（x/z 两个载向）、完美分离、差分响应 gap 2.96%
  ≫ 组内 0.27%；σ=0 本底 ±0.6% 且换位置不变 ⇒ 有限体积分数堆积效应。

T4.1 求解器选型
- 代码事实：Window B 生产引擎是显式 + FFT，无隐式稀疏系统 ⇒ AMG 不在关键路径。
- 实测剖析：FFT 仅占 1.5%；40% 在 np.gradient/upwind_grad 等全域有限差分；
  真正的 3D 门槛是内存 O(nv·N³)（Δx=0.25µm/L=50µm ≈ 18 GB）。
- ⇒ 修法是窄带数据结构 + 批量模板，不是换线性求解器。
EOF
git commit -q -F /tmp/_cm.txt && git log --oneline -3
EOF