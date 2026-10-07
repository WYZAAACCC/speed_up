#!/usr/bin/env bash
# _bk_commit_r9.sh —— 提交 Round 9 的工作
set -eu
cd /mnt/f/speed_up || exit 1
git add -A pipeline/ca_pf_framework/_bk_exp.py \
           pipeline/ca_pf_framework/_bk_pair.py \
           pipeline/ca_pf_framework/_bk_comp.py \
           pipeline/ca_pf_framework/_bk_perlath.py \
           pipeline/ca_pf_framework/_bk_verdict.py \
           pipeline/ca_pf_framework/_bk_meta.py \
           pipeline/ca_pf_framework/_bk_v7.sh \
           pipeline/ca_pf_framework/_bk_pair_all.sh \
           pipeline/ca_pf_framework/_bk_gs_prog.sh \
           pipeline/ca_pf_framework/_bk_gs_eval.sh \
           pipeline/ca_pf_framework/_bk_meta.sh \
           pipeline/ca_pf_framework/BLOCK_STATUS.md
git status --short | head -30
echo "---------------- commit ----------------"
git commit -q -F - <<'MSG'
Round 9: 长出来的块拓扑对/几何有缺陷 + 新判据 V-7/V-7b + 量具自伤修复

## 结论
dry_gs2（N=96, 200 步, 生长堆叠）终态 nslab_n=6 / nf3_col=5 / f3_faces=1787。
新增成对界面记账（_bk_pair.py）挖出三件事：

(a) 拓扑对且被几何顺序独立交叉验证：沿 n* 的片序实测 5-3-1-2-4-6，
    与 _seed_next 的 side=±1 交替规则**逐对预测一致**，其余 10 对 F3 面积严格为 0。

(b) **+n* 侧三张界面只有约 1/3 贴合，其余是 1 胞厚的母相 β 膜**：
    1|2: F3 0.4601 + β 0.9492；2|4: 0.4081 + 0.9102；4|6: 0.5136 + 0.7617
    （−侧 5|3、3|1 是满的 1.48/1.55，β 仅 0.25/0.26）。
    "F3 + β = 整片足迹" ⇒ 同一张界面被劈成两半，不是少了一块。
    判为**阶梯错位伪影**：M_s 以下无留 β 膜的驱动力；C-1 已判不润湿；
    β 膜恰好 1 胞厚且是几何配分。机理见 windowB_surface.py:1705-1719
    （seed_plate 写真 SDF 并把其它场抬到 -sdf ⇒ argmin 把界面定在两零集**中面**
     ⇒ 有重叠就是满接触，恰好相切时中面退化 + edge 是格心投影 ⇒ 阶梯错开）。

(c) **单变量对照证实**：新臂 dry_pa（N=96, 同 Δx, 同 n*，唯一差别是不加 --grow-stack）
    在 t=0 给 0.955、50/100 步给 0.884/0.851；dry_p2(N=192) 同读数（排除盒子大小）。
    生长臂 0.616 ⇒ 差别只能来自放置方式。

(d) **我自己的 V-1 判据太弱**（gs2 通过了它，却缺 38% 界面面积）。
    新增预登记判据（阈值由对照校准，不拍脑袋）：
      V-7  界面完整性：f3_area/[Σ单根宽面·(M-1)/M] ≥ 0.85（天花板实测 0.85~0.96）
      V-7b 无多余 β 夹层：每对 β/(F3+β) ≤ 0.25（对照底噪 0.14~0.16，缺陷 0.60~0.69）

(e) 新发现（独立待办）：预摆臂自己的界面也在退化 0.955→0.884→0.851，
    β 占比恒定 ⇒ 板条变长而 F3 面积没同步增长。成因未定，不得与 (b) 混淆。

## 代码
- _bk_exp.py: 修 np.genfromtxt 读 series.csv 崩溃（runs 列是 '5/3/1/2/4/6' 字符串，
  类型升级到 longdouble 后抛 ValueError ⇒ **主判决一个字都没打出来**）；
  新增 read_series()；新增 --nuc-overlap-nm（默认 0=旧行为）；
  meta.json 补 reinit_dt/grow_stack/nuc_every/nuc_gap_nm/phi_every + 整份 dump vars(a)
  （原先缺这些 ⇒ 违反"事后可重测"要求：光看 meta 分不清预摆还是长出来的）。
- _bk_pair.py（新）：成对 F3 面积（Cauchy 无偏估计）、逐根朝 β 面积、
  沿 n* 一维堆叠剖面（去 <32 体素孤儿）、β 夹层计数、V-7/V-7b 判决。
- _bk_comp.py（新）：分量级诊断（每个场的每个连通分量在哪/多大/邻居是什么场）。
  **正是它把"场1 4 分量、沿 a 5722 nm"还原成 1 根完整板条 + 3 个 1-2 体素孤儿**，
  排除了"板条碎裂"误判 ⇒ V-5 的 ncomp_max=4 不是物理碎裂。
- _bk_perlath.py: 未出生场 ZeroDivisionError 修掉（改为相对该板条自己首次出现）；
  加 ncomp 列与"生于 step N"。
- _bk_verdict.py: 新增 V-1g（长出来的块专用：末态同构 + 单调 +1 阶梯 + 级数 M-1）、
  chain arm_report 记 series.csv mtime（防读错旧臂）。

## 已知未修
- V-7/V-7b 目前只在 _bk_pair.py 里判，_bk_verdict.py 还没接。
- ncomp 判据应改为"显著碎裂(≥32 体素)"并同时报原始值 —— 需改 _bk_measure。
MSG
echo "---------------- done ----------------"
git log --oneline -1
