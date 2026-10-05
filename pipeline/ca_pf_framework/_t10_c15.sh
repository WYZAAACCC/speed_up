#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== t10B9 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10B9 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在（exit: $([ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo 无)）"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo -n "  形核事件行 = "; grep -ac 'athermal 形核' _w2_t5_short_t10B9.log 2>/dev/null
echo -n "  块数 = "; grep -ao '共 [0-9]* 块' _w2_t5_short_t10B9.log 2>/dev/null | tail -1
grep -a 's292 补投轮' _w2_t5_short_t10B9.log 2>/dev/null | tail -2 | tr -d '\r' | sed 's/^/    /'
echo -n "  ★ protected 含 0 = "; grep -a '\[SEEDCARVED\]' _w2_t5_short_t10B9.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
echo -n "  步 = "; grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10B9.log 2>/dev/null | tail -1 | cut -c1-85
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R605_BLOCKCOUNT_CONCLUSIONS.md \
        pipeline/ca_pf_framework/_t10_c2_redo.py \
        pipeline/ca_pf_framework/_t10_npref_vs_habit.py \
        pipeline/ca_pf_framework/_t10_param_audit.py \
        pipeline/ca_pf_framework/_t10_prov_ctx.py \
        pipeline/ca_pf_framework/_t10_wrapchk2.py
git commit -q -F - <<'MSG'
★ R605 留档：块数/分组自发性的三条结论 + C2 撤回 + 两条实现事实。

结论 1（真缺口）：**`vmap`（场↔变体分配表）是外部输入** ⇒ 分组的规模与配比不可能自发。三方证据：BLOCK_DERIVATION §6.8/A8（变体分组=规定；LevelSetMulti 只存 df/eps0/npref/atab/wtab，无取向自由度）、BLOCK_DERIVATION_REVIEW:296-299（"缺项比错项更危险"，并点名这正是 RESEARCH_INTENT §2.2 要"自发"的那件事）、RESEARCH_INTENT:81/:101-102（权威：同变体⇒block；同一惯习面族的不同变体⇒packet；要求"自发"）；代码事实：:4568「self.vmap（场→变体，_bk_exp.py:883/1129 挂上）」+ 启动器 --laths 手写 22 场一组。实现方案 (a)=把场↔变体改为形核时动态赋值（应力择优+自催化+占用约束）；方案 (b) 连续取向 DOF 物理上不对（变体是 12 个离散取向）。

结论 2：块数 B 是规定值。推导（_t10_rac_derive.py）D1 PASS（热涨落密度比弹性能密度小 10 个数量级 ⇒ 马氏体 athermal，阈值取 f_crit=2γ/t）、D2 PASS（r_ac=4.734 µm）、D3 自然块数=2.25 vs 仿真 16/9 ⇒ 差 7.1 倍（FAIL 正是期望的证据方向）。反解：要让块数涌现成 9–16 需有效 r_ac≈2.5–3 µm。记账：γ=0.20 是占位值（待出处）；用有出处的 G_TI64 会使 r_ac 大 1.17×⇒自然块数≈1.4，结论方向稳健；"207 根"须标注"在 B=9 规定值下"。

结论 3（新）：**`npref` 是弹性代理量、不是晶体学惯习面**。_t10_npref_vs_habit.py 正对照 PASS（6 个 {011} 各自 max|cos|=1.0），12 个 _argmin_normal 输出对 {011} 的 max|cos|=0.8560–0.8644 ⇒ **0/12 命中**（cos⁻¹0.856=31.1°）。依据 :947 最小化 ½ε⁰:Λ(C,n):ε⁰、:5787 npref=_argmin_normal(C,eps0)。而 RESEARCH_INTENT 用**晶体学**惯习面族定义 packet ⇒ 口径差成立，该判据不能用 npref 实现。✅ 对已报结果无影响（我用 band_fld/region，不用 npref；且从未报过 packet）。

附：C2 撤回（第一版判据退化；"不可算"是过度撤回；重做得 12 组而非 6 组，原因即结论 3）——但 C1 的 {011} 6×2=12 计数仍成立。
附：实现事实两条 —— _argmin_normal 单次 ~10s、__init__ 调用 12+66 次 ⇒ 构造 ~780s，故有 argmin_normal_cached；其 docstring 称"同变体 eps0 逐位相同"与我的 N2 实测（66/66 两两不同）冲突 ⇒ 登记口径差异，不推翻 N2。
MSG
git log --oneline -1
