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
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10PRT2.log 2>/dev/null | tail -2 | cut -c1-105
echo -n "  周期清理 = "; grep -ac '\[SEEDCLEAN-STEP\]' _w2_t5_short_t10PRT2.log 2>/dev/null
grep -a '\[SEEDCLEAN-STEP\]' _w2_t5_short_t10PRT2.log 2>/dev/null | tail -3 | sed 's/^/    /'
echo -n "  ★ protected 含 0 = "; grep -a '\[SEEDCARVED\]' _w2_t5_short_t10PRT2.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
ls _exp/_bk_t5/dry_t10PRT2/snap_*.npz 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null

cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_nvar_derive.py pipeline/ca_pf_framework/_t10_c5.sh \
        pipeline/ca_pf_framework/_t10_c6.sh
git commit -q -F - <<'MSG'
新规则「推导」分支：nvar（变体数）出处由「文献」升级为「**推导 + 文献**」。推导：Burgers OR ⇒ 6 个 {011}_β 惯习面 × 每面 2 个独立 ⟨1̄11⟩_β = **12**。数值自检 5/5 PASS（_t10_nvar_derive.py）：N1 variants() 恰给 12；N2 66/66 对两两不同；N3 ‖dev ε⁰_k‖ 全等（跨度 1.11e-16 ⇒ 变体等价、无偏好）；**N4 Σ_k dev(ε⁰_k) = 2.914e-16，信号 0.1420 ⇒ 低 15 个数量级 ⇒ 12 变体构成封闭的自协调组（C4 群封闭性）**；N5 Σ ε⁰_k 为纯静水（静水分量 −0.100671、偏量 2.9e-16）。

★ 同时自查出判据缺陷（第 12 次）：N4/N5 首轮"FAIL"是容差写成 1e-15×max|ε⁰| = 1.1e-16、比机器精度还紧 ⇒ 把纯浮点噪声判成物理失败。已改为相对信号标定（1e-12×‖dev ε⁰‖），同 AGENTS.md §3 教训 22。

参数出处总账现状：22 个物理参数中 sigma_y 无出处（文献工具受限⇒升级到推导，R601 已证不敏感⇒无需标定）；ed-eta 与 nvar 有推导出处；其余 19 个有文献/DOI 线索（v1/v2 分歧的 DS_REF/mob/nvar/B 中 nvar 已解决，余 3 个仍需读原文）。
MSG
git log --oneline -1
