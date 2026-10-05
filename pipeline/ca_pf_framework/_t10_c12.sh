#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== t10B9 状态 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10B9 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在（exit: $([ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo 无)）"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo -n "  形核事件行 = "; grep -ac 'athermal 形核' _w2_t5_short_t10B9.log 2>/dev/null
echo -n "  块数 = "; grep -ao '共 [0-9]* 块' _w2_t5_short_t10B9.log 2>/dev/null | tail -1
grep -a 's292 补投轮' _w2_t5_short_t10B9.log 2>/dev/null | tail -2 | tr -d '\r' | sed 's/^/    /'
echo -n "  ★ protected 含 0 = "; grep -a '\[SEEDCARVED\]' _w2_t5_short_t10B9.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
echo -n "  快照 = "; ls _exp/_bk_t5/dry_t10B9/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null

cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R603_BLOCKCOUNT_LITERATURE.md
git commit -q -F - <<'MSG'
★ 块数律：**文献分支命中**（R603 留档）。方法：按用户建议改走 **HTML 页面**（PDF 被 fetch 工具拒收 ⇒ 此前两次判"文献拿不到"是方法用错，不是文献不存在）。

命中：Galindo-Nava & Rivera-Díaz-del-Castillo, *A model for the microstructure behaviour and strength evolution in lath martensite*, **Acta Materialia 98 (2015)**, DOI 10.1016/j.actamat.2015.07.018（accepted version: Cambridge Apollo, DOI 10.17863/CAM.38443）。摘要原文（自仓储 HTML 条目页取得）："**The packet and block size were found to linearly depend on the prior-austenite grain size** when introducing relevant crystallographic and geometric relationships of their hierarchical arrangements."

⇒ **正好可用**：Window B 的设定就是"单个 prior-β 晶粒内部的三维盒子" ⇒ **原晶粒尺寸 D 是物理输入**（来自 Window A 晶粒骨架），不是可调参数 ⇒ 块数由 d_block ≈ k_b·D + 盒子体积 + 层级几何导出 ⇒ **块数成为 D 的导出量，而非外部指定** —— 正面回应用户质疑。

参数出处总账更新：块数 B 由「标定」⬆️**升为「文献」**（DOI 已登记）；sigma_y ❌无出处（已走完升级次序：文献工具受限→推导 R601 且证不敏感→无需标定）；mob ⚠️仅"实测/来源"待找文献；ed-eta/nvar/DS_REF 各有推导出处。

尚缺：系数 k_b 的具体形式（摘要有律的形式、无系数；accepted PDF 被工具拒收）⇒ 下一步继续 HTML 路线找全文镜像或引用该式子的 HTML 页面。
MSG
git log --oneline -1
