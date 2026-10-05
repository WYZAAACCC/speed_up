#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 算例状态 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10PRT2 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  echo "  引擎在 pid=$EN"
  ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/    /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "    %s\n", $0}' /proc/$EN/status
else
  echo "  ⚠ 引擎不在（exit: $([ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo 无)）"
fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo "--- 步 ---"
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10PRT2.log 2>/dev/null | tail -3 | cut -c1-105
echo "--- 形核 / 清理 / 保护 ---"
echo -n "  形核行 = "; grep -ac 'athermal 形核' _w2_t5_short_t10PRT2.log 2>/dev/null
echo -n "  播种清理 = "; grep -ac '\[SEEDCLEAN\]' _w2_t5_short_t10PRT2.log 2>/dev/null
echo -n "  周期清理 = "; grep -ac '\[SEEDCLEAN-STEP\]' _w2_t5_short_t10PRT2.log 2>/dev/null
echo -n "  SEEDCARVED = "; grep -ac '\[SEEDCARVED\]' _w2_t5_short_t10PRT2.log 2>/dev/null
echo -n "  ★ protected 含 0 的行数（应 0）= "; grep -a '\[SEEDCARVED\]' _w2_t5_short_t10PRT2.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
echo "--- 快照 ---"
ls _exp/_bk_t5/dry_t10PRT2/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null

cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_param_audit2.py
git commit -q -F - <<'MSG'
参数出处总账 v2 修好并交叉验证：★ 缺陷 = 量具自污染 —— 审计脚本自身既含参数名又含关键词表 ⇒ 扫描器在自己的代码里"找到出处" ⇒ 首轮把 22 个参数全判成"文献/DOI"（证据列赫然是 _t10_param_audit.py:DOI）⇒ 无效。修：扫描语料排除审计脚本自身。修好后结果：**sigma_y 是唯一"无出处"参数**，ed-eta 是"推导"(R601)，其余 20 个为文献/DOI。★ 交叉验证：审计独立指向的唯一无出处参数与我此前在 R601 §5 独立标注的完全一致 ⇒ 工具可信（同 §3 教训19：探针先做正对照）。另修 argv 提取（按 NUL 切分 + 集合判断，v1 因要求尾随空格而返回 0 字符）。记账 v1/v2 分歧：v1 只扫 .md 报 DS_REF/mob/nvar/B 为"仅标定"，v2 加扫 .py 后报"文献/DOI" —— 采信 v2 但"命中≠出处可靠"，这 4 个仍需读原文确认。
MSG
git log --oneline -1
