# 总工作图说明（FIG_OVERALL_STATUS.png）

生成脚本：make_overview_fig.py（matplotlib，中文用 SimHei）

四个面板：
1. 总体路线与当前状态：热层 -> Window A(CA) -> Window B(局部 PF) -> Window C(Gibbs 面) -> 神经算子层；
   以及两级接口（Π 已完成 / PF<->LKT 进行中）与 L0 状态调度。
2. 验证账本：累计 142 项判据（PASS/WARN/FAIL/RULE 分解）。
3. P1.1 关键路径与当前位置：P1-a 通过 -> 根因钉死 -> 非零效应 -> ALPHA 可调 -> ALPHA* 未定（卡在 W/dc=0.16）。
4. 本轮查出的问题与状态：4 项已修 + 1 项待确认 + 1 项开放 + 1 项阻塞。

颜色：绿 = 通过/已修，黄 = 开放，红 = 未开始/阻塞，橙 = 进行中/待确认，蓝 = 步骤框，灰 = 未开始。
