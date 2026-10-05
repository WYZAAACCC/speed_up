#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 算例状态 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10PRT2 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在（exit: $([ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt || echo 无)）"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10PRT2.log 2>/dev/null | tail -3 | cut -c1-100
echo -n "  周期清理 = "; grep -ac '\[SEEDCLEAN-STEP\]' _w2_t5_short_t10PRT2.log 2>/dev/null
grep -a '\[SEEDCLEAN-STEP\]' _w2_t5_short_t10PRT2.log 2>/dev/null | tail -2 | sed 's/^/    /'
echo -n "  ★ protected 含 0 = "; grep -a '\[SEEDCARVED\]' _w2_t5_short_t10PRT2.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
ls _exp/_bk_t5/dry_t10PRT2/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null

cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_param_audit2.py pipeline/ca_pf_framework/_t10_prov_ctx.py
git commit -q -F - <<'MSG'
参数出处总账口径修好（第 13、14 次自查）：(1) **子串假阳性** —— v2 用 re.escape 无词边界，`mob` 命中 `_prodmob_mid60`/`mob_beta`/`mobility` ⇒ 改用词边界 `(?<![A-Za-z0-9_])NAME(?![A-Za-z0-9_])`；(2) **自污染范围比第一版以为的广** —— 只排除 _t10_param_audit*.py 不够，扫描器又在 _t10_prov_ctx.py（含 TARGETS+KEY 表）与 _t10_nvar_derive.py 里"找到" mob/nvar 的出处 ⇒ 改为**排除全部会话工具脚本**（_t10_*）。修正后：sigma_y ❌无出处（★正对照①通过与 R601 §5 独立结论一致）、mob 由假阳性的"文献/DOI"**降级为"实测/来源"**（仅被 R30_AUDIT_LEDGER 一处「来源」字样锚定，无文献/DOI、无推导 ⇒ 按新规则应先找文献）、ed-eta 推导（★正对照②通过）、其余 19 个文献/DOI（未读原文）。新增 _t10_prov_ctx.py：抽出出处关键词附近真实原文供人工判读（因为"命中≠可靠"）。
MSG
git log --oneline -1
