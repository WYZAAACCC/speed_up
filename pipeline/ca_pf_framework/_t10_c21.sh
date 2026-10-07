#!/bin/bash
cd /mnt/f/speed_up || exit 1
# ★ 顺带核：我的启动器有没有配 --nuc-fresh-every / --cool-rate
cd pipeline/ca_pf_framework || exit 1
echo "=== 启动器参数核查 ==="
for f in _t10_b9run2.sh _t10_prtrun.sh _t10_cl2run.sh _t10_fix_run.sh _t10_eta253.sh; do
  [ -f "$f" ] || continue
  echo "  $f: fresh-every=$(grep -c 'nuc-fresh-every' $f)  cool-rate=$(grep -c 'cool-rate' $f)  gamma0=$(grep -c 'gamma0' $f)  nuc-fresh-every 默认值=$(grep -o "add_argument('--nuc-fresh-every', type=int, default=[0-9]*" _bk_exp.py | head -1)"
done
echo
echo "=== _bk_exp.py 里相关默认值 ==="
grep -nE "add_argument\('--(nuc-fresh-every|cool-rate|gamma0|beta-h|beta-w|T-end)'" _bk_exp.py | cut -c1-140 | sed 's/^/  /'
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R611_N8_AND_TEMPHISTORY.md pipeline/ca_pf_framework/_t10_c20.sh
git commit -q -F - <<'MSG'
★★★ R611：③块形成层 + ⑥输入层 ── **N8 双旋钮缺陷** 与 **S14/N2 温度历史占位**（两条都是项目早已登记、我此前完全不知道的"因简化/数值硬设定"实例）

【★★ N8（R2_PARAM_VERDICTS.md:49，已登记为真缺陷，修法有闭式解）】原文：
「`--nuc-block-target`（目标块数）与 `--nuc-fresh-every K`（实际块数）是**两个独立旋钮，无人校验** ⇒ `_r520c` 目标 8 块、**实际只建 4 块**，39 次尝试里 **22 次（56%）被引擎拒**；🔴 **真缺陷（守卫缺口）**；**修法有闭式解：`K = n(T_end)`**（banner 自己写了这句建议，但**不强制、不告警**）。推导：fired 事件数 N=B·n，fresh 出现于自增前 `% K == 0` ⇒ 块数 = ceil(N/K)，要 = B 需 **K = n**。实测 `_r520c`：K=6 ⇒ fresh 事件号 [13,19,25,31] = 4 块」
⇒ 这解释了 t10B9 的「本步第 8/8 次被拒」（fresh 只在 %K==0 触发，K 没配对 ⇒ 大量拒绝），**与 F1 同族**；闭式解 `K = n(T_end)` = **23**（R581_T5_RESTART:2163）。
⇒ **对 goal ③(a)(b) 的意义**：B（目标块数）与 K（决定实际块数）**本来就该是一个量**（B = ceil(N/K)，配 K=n 才自洽），**但代码不强制、不告警** ⇒ 「块数是规定值」的具体机制，而且连"规定得自洽"都没保证 ⇒ **用户指示的"取消 B、让块数由物理给"不但更物理，还能消掉这个守卫缺口**。

【★★ S14/N2（R581_T5_RESTART.md:180）：温度历史本身是"线性降温占位"】原文：
「那**真正的**驱动力侧简化是什么 ⇒ **⚠ 温度历史本身是线性降温占位**：`_T_of_t = KM.linear_cool(T_start, T_end, (T_start−T_end)/q)`（`_bk_exp.py:1040`）；**代码自陈"占位"（S14/N2）**。**驱动力忠实地跟着 T 走，但 T(t) 不是真实 LPFA 热史**」
⇒ 驱动力 ΔG_v(T)=DS_REF·(T0−T) 忠实地跟着 T ✓（这部分物理），**但 T(t) 本身是线性占位** ⇒ 形核速率、burst 档位划分、α_KM 有效值、乃至"最终板条数"**全部依赖 T(t)**。
⇒ **冷速有文献带**：T_RESULTS_T1_T5.md:1101 —— windowB_km 新增 `from_cooling_rate(q)`「把**文献冷速 10³–10⁸ K/s** 直接变成时间表」⇒ 待核我们的 `--cool-rate` 是否落在带内。

【顺带】BLOCK_PARAM_TABLE.md:17：`C-2 n = α_KM(M_s−T_end) = floor(6.3250) = 6` 与归档"规定的 6"**独立地一致** ✓（另一组 α_KM 下）。**`mob` 出处本轮仍未查到**：命中全是 R603/R607/R608/R609 里我自己写的"待找文献" ⇒ 确实缺失、且没有像 β_h/γ 那样的专门表 ⇒ 需走 HTML/机构仓储继续找；找不到则按规则升级到"推导"，其次"标定 + 不确定度"。

【危害排序】1) N8 双旋钮 + 56% 拒绝率（t10B9 停机家族；修法现成 K=n(T_end)=23）2) S14/N2 T(t) 线性占位（驱动力侧最根本简化）3) γ0 在文献带外 4) β_h/β_w 不受支持+退化+算力下界耦合 5) _Bpar 门 + F1 死锁 + n_fresh_ok 计数 6) ①(c) 回滚不覆盖变体指派 7) ③(d) F2 从值到通道都没起作用 + mob 出处缺 8) ⑦(b) D4′ 偏离 / ④(b) vmap / ②(b) npref（待用户裁定）。

【记账】硬步骤第三次见效：`grep <参数名> + 出处|锚点|不受支持|退化|占位|文献` 一次挖出 N8 与 S14/N2 —— 两条都是项目早已登记、而我此前完全不知道的实例。按老办法（只看 goal 里列的词）这两条会继续漏掉。
MSG
git log --oneline -1
