#!/bin/bash
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R608_NUC_CHANNEL_DEFECTS.md \
        pipeline/ca_pf_framework/_t10_argdiff.sh \
        pipeline/ca_pf_framework/_t10_r481chk.sh
git commit -q -F - <<'MSG'
★★★ R608：形核通道三处缺陷 ── t10B9 停机真因已定位到代码行；并更正「平行建块从未生效」

【决定性结论】两行代码合起来给出答案（均【已核实】）：
  _bk_exp.py:3649  ap.add_argument('--nuc-init', type=int, default=0, ...)   ← 默认 0
  _bk_exp.py:2746  if _Bpar2 and int(_Bt) > 0 and a.nuc_init > 0:          ← 第三个条件
                       _fresh_now = (n_fresh_ok < int(_Bt))    （s293 新规）
                   else:
                       _fresh_now = ((n_ath_tgt % _K) == 0)    （F1 旧规）
我的启动器都没传 --nuc-init ⇒ a.nuc_init = 0 ⇒ 门为假 ⇒ ** _Bpar 分支从未进入**。⇒ 三条结论：
(1) **--nuc-block-parallel 1 在我所有算例里从未生效**；
(2) **t10B9 停机真因 = R481 记的、明确写"本轮未修"的 F1 死锁**（_fresh_now=((n_ath_tgt%K)==0)，n_ath_tgt 从 1 起 ⇒ stack 全失败时永远到不了 K ⇒ fresh 永不被调用；日志 att=184 attach_ok=31 正是此情形）；
(3) 我 s293 的 n_fresh_ok 计数缺陷**不是本次的因**（分支没进），但**仍是真的**（:2792-2793 自己写着"退回的那次也被记进 n_fresh_ok ⇒ 3 次失败后 n_fresh_ok==B ⇒ _fresh_now 永久为假"）。

【⚠⚠ 连带更正（必须随结论一起报）】既然 _Bpar 没生效，「前 B 个成功事件各建一个新块」**从未发生**。「共 9 块」/「本档目标 135 根」只来自 :2648 `_tgt = min(_Bt*_n_blk, nv)`（只定"投几根"的目标数，不影响通道派遣）；通道派遣一直走旧规则。⇒ 我此前"平行建块（前 B 个事件各建新块）"是**对未执行代码的描述，撤回**；nblk/blk_laths 的量本身没错（量具独立），但"为什么是 16/9 块"的**解释不成立，必须重做**。

【第二处静默风险】超临界探针回滚**不覆盖变体指派**：:2760-2795 的 _seed_undo_note/_seed_undo_apply **只记/只还原 phi[k] 与 phi[j]**。现状不炸（seed_plate 目前只写 phi），但 natural 模式必须把 eps0[p]/npref[p] 写进槽位 ⇒ 被拒候选会**静默留下变体指派**。⇒ 实现 natural 的硬前提：扩展回滚覆盖变体指派 + 打独有成功串（如 [NUCASSIGN]）。

【三处修法 + 可 FAIL 判据（缺一不可）】
1) 去掉 `a.nuc_init > 0` 这个门（_Bpar 不该依赖 --nuc-init）或启动器显式传 --nuc-init；判据：开 --nuc-block-parallel 1 后**日志必须出现"平行建块已生效"的独有成功串**（现在没有任何串能证明它生效）。
2) F1 本体：「stack 连续失败 N 次 ⇒ 必须允许 fresh」而非死等 %K==0；判据：构造"stack 全失败"算例 ⇒ 形核不停止。
3) 我引入的 n_fresh_ok 只计**成功**新建块；判据：故意让 fresh 失败若干次 ⇒ _fresh_now 不得永久变假。
⇒ 按 R606 分步计划：**先做第 3 条**（只动我加的那行计数、默认关、归档逐位不变），再做 1、2。

【记账 21–22 + 共同根因】21：**--nuc-block-parallel 1 从未生效而我一直以为它在起作用** —— 根因是**我一直在"看参数"而不是"看独有成功串"**（AGENTS.md P44）；这是本会话最贵的一次，整条"块如何建立"的解释建在未执行的代码上。22：上一轮"启动器缺 --nuc-sites-refill"结论也错（该开关**硬编码在 _t5_short.py:101**）—— 只查一层就下结论（R481 教训② 同型）。另：教训 23 第三次（R502 在 goal 里点名，我却先自己重推）。⇒ 写成纪律：**新开关上手三件事 —— ①打独有成功串；②先问"它凭什么生效"（有无前置门/环境变量）；③卡住时往下一层量。**

危害排序：1) _Bpar 未生效门 + F1 死锁 + n_fresh_ok 计数（t10B9 真因、也是 natural 前置障碍）2) ①(c) 回滚不覆盖变体指派 3) nblk/blk_laths 解释作废 4) γ/mob 出处 + ②(c) β_h/β_w 错标 + ③(d) F2 通道 5) ⑦(b) D4′ 偏离 / ④(b) vmap / ②(b) npref（待用户裁定）。
MSG
git log --oneline -1
