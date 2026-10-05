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
echo -n "  ★ protected 含 0 = "; grep -a '\[SEEDCARVED\]' _w2_t5_short_t10B9.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
echo -n "  步 = "; grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10B9.log 2>/dev/null | tail -1 | cut -c1-90
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R604_BLOCKCOUNT_AND_PERIODIC.md \
        pipeline/ca_pf_framework/_t10_wrapchk2.py pipeline/ca_pf_framework/_t10_c13.sh
git commit -q -F - <<'MSG'
★ R604 留档：块数律 / 周期边界 / 配置偏差 / 流程失误。

(1) **真缺口 = 没有取向自由度**（项目文档两处独立记录）：BLOCK_DERIVATION.md §6.8「防自欺表」（自注"本文件最重要的一张表"）记 —— 块内根数 **规定**（无分裂/合并机制）；**变体分组/block–colony–packet 本身 规定**，因为「LevelSetMulti 只存 df/eps0/npref/atab/wtab，**没有任何取向自由度**」；M(n) 的 β_h/β_w、核形状位置取向、n_ref 退化 均为规定。而 RESEARCH_INTENT.md §2.2（权威）要求板条「**自发**按 Burgers 取向分组」⇒ **冲突成立**，且文档自己就点明了。⇒ 正确提法从"找块数律"改为"**补取向自由度**"。

(2) **周期边界：D4′ 已满足**。证据：windowB_surface.py 梯度/曲率全用 np.roll 周期差分(:36/542/573)、注释明说「动力学是周期的（np.roll，全场各处都用）」(:1678/:2875)、周期可分离卷积 np.pad('wrap')+(:2746)。★ 且框架**自带**「板条长出盒子」守卫 wrap_axes/wrap_axes_any/check_wrap(:3354/:3407/:3427)，设计理由即「长过 L/2 的板条会绕盒、长度读数会超过 L」。⚠ 我**先自造了 P1–P4** 才撞见它 ⇒ 本 goal 内**第 2 次违反教训 23**（先搜文档）。框架自记账两坑：并集口径过触发(T13_recheck_wrap, f=0.05–0.17 即误判)、z=0 wrap 层被误判成界面(:6160)。另 AUDIT-#5 的溶质再分配是**刻意非周期**（设计非缺陷）。

(3) **实测 step100 尚无绕盒**（_t10_wrapchk2.py，框架口径 span>L/2）：正对照（合成直线 37 胞 ⇒ span 2.3125 µm 精确）✅；两种口径均 0；各场最大轴跨度 中位 3.03 / max 3.44 µm vs L/2=5.00 µm ⇒ 判据已建、量具已自检，但**该监控项尚未进入可判状态**。

(4) **口径区分（第 16 次自查）**：我曾误判「实测长度 4843–5017 nm 已跨过 L/2=5000 nm」——那是拿 **PCA 主轴延伸**（_t10_seven 的长nm，斜置板条偏大）去比只对**轴跨度**有意义的阈值。斜置板条 PCA 长度本大于任何单轴跨度（对角线>边长），故 4918 nm 与 span 3.44 µm 不矛盾；绕盒判据必须用轴跨度 ⇒ 不绕盒。（同 AGENTS.md P30）

(5) **配置偏差记账**：相对 RESEARCH_INTENT D4′（L=3.2 µm 可选 4.0、Δx=25 nm、N=128 可选 160、周期边界），在跑的是 L=10 µm、Δx=62.5 nm、N=160 ⇒ **L 与 Δx 偏离**（D4′ 称集束/变体群尺度 5–50 µm，10 µm 有理由但仍是偏离；Δx 粗 2.5×，板条厚 0.24–0.30 µm 下 62.5 nm 为 4–5 胞仍可解析）；N 与周期边界 ✓。
MSG
git log --oneline -1
