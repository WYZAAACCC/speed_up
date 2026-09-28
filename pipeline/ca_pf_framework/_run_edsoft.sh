#!/usr/bin/env bash
# _run_edsoft.sh --- **M-6 的正对照**：界面胞上的 `ed` 是物理量还是硬阶梯噪声？
#
# 为什么要做
# ----------
# `windowB_surface.py:2097-2102`（AUDIT-#9）自己记着：
#   "原来一律用 **hard region** 指示场 ⇒ 界面胞的 eps0 分布是阶梯状
#    ⇒ FFT 谱法解出的 sigma 在界面处有 O(1) 阶梯噪声 ⇒ 驱动 ed 在界面附近被污染。
#    新增 soft 选项……默认 soft=None ⇒ 沿用 self.elastic_soft（**默认 False**）"
#
# 而本轮 `F-1` 的诊断**恰恰只在界面胞上取 `ed`**（M-6），读出
#   尖端 −2.5e8 / 侧面 −4.2e7 / 宽面 −6.7e7（而 Δf = 3.5e8）
# 并据此说"弹性能把设计上最快的尖端压成驱动力最低的面"。
# ⇒ **若 `elastic_soft` 一开这三个数就大变，则那条诊断是阶梯噪声，必须撤回。**
#   （`AGENTS.md §3.19`：探针必须先做正对照；§3.27：两个机制重合时分不开。）
#
# 设计（**单因素：只改 `elastic_soft`**）
# -------------------------------------
#   两臂其余逐字相同：N=64 Δx=166.7 nm R=500 t=700 β=3.5/2.3 norm_smooth=0 proj2 150 步
#
# ★★ 2026-09-28 Round 137 第二次跑（`F-2` 修好之后）：
#   第一次跑（`_w2_edhard.log` / `_w2_edsoft.log`）两臂**逐位相同** —— 因为当时
#   `elastic_soft` 是**死开关**（见 `WINDOWB_ROADMAP_TO_CORRECT.md §9.10c`、`_chk_edsoft.py`）。
#   修好之后（引擎 `a1eb151f`）本次才**第一次真正能做这个分离**。
#   ⇒ 旧的两份日志**保留**作为"修前"记录；本次写到 `*2.log`。
set -u
cd "$(dirname "$0")"

echo "########## elastic_soft 单因素对照（F-2 两处都修后）  start=$(date -Is) ##########"
echo "  引擎 SHA 见每个 RUN MANIFEST（须 = b9565f69…，即 F-2 的两处都修完）。"
echo "  前两轮的结论：第 1 轮两臂逐位相同（死开关）；第 2 轮 M-6 变了但**形状仍逐位相同**"
echo "  （因为 advance 走 elastic_driving_pair，那里是第二处硬编码）⇒ 两轮都作废，本轮才算。"

bash _run_arm.sh _w2_edhard3.log W2-EDHARD3 _probe_shape.py \
    --N 64 --dx-nm 166.7 --steps 150 --every 50 --arms aniso
echo "### EDHARD3 rc=$? @ $(date -Is)"

bash _run_arm.sh _w2_edsoft3.log W2-EDSOFT3 _probe_shape.py \
    --N 64 --dx-nm 166.7 --steps 150 --every 50 --arms aniso --elastic-soft
echo "### EDSOFT3 rc=$? @ $(date -Is)"

echo "########## 结束 end=$(date -Is) ##########"
