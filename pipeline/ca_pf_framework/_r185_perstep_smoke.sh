#!/bin/bash
# _r185_perstep_smoke.sh —— `--omega-mode perstep` 的**端到端接线**冒烟测试。
#
# ## 为什么 `_r182` 不够
# `_r182_omega_check.py` 直接调 `WL.default_omega` ⇒ 只证了**那一层**。
# 用户的要求是「该有的模块是否正常接线」⇒ 必须**穿过 `_bk_exp.py` 的 CLI**
# 再走一遍，确认 argparse 的 `choices`、诊断打印、以及 `build_table` 的透传都对。
#
# ## 判据（先写死）
# * **S-1** `--omega-mode perstep` 能**正常解析并跑完**（退出码 0）。
# * **S-2** 日志里出现 **`★★★ R182`** 的诊断行，且**明说**"不是总张角"。
# * **S-3** 同时出现 `ladder` vs `perstep` 的步长对比行。
# * **S-4** 负对照：同样命令把 `--omega-mode` 去掉（默认 ladder）时，
#   **不得**出现 `★★★ R182` 那行（否则打印没有门控 ⇒ 会误导读数的人）。
# * **S-5** 两种模式下 `gtab` 的 F3 条目数应一致（`n_f3` 只由变体表定，与 ω 无关）。
#
# 规模：N=32 / Δx=125 nm / 2 步 —— **秒级**，只为验证接线。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
COMMON="--arm dry --N 32 --dx-nm 125 --laths 1,1,2,2 --gap-nm 0 \
        --steps 2 --every 1 --snap-every 1 --pair-every 0 --nthreads 2"

echo "=== S-1/S-2/S-3：perstep 臂 $(date '+%T') ==="
"$PY" -u _bk_exp.py $COMMON --omega-mode perstep --omega-max-deg 0.4545 \
      --tag pssmoke --out _exp/_bk_ps 2>&1 | tee _w2_r185_ps.log | tail -25
RC1=${PIPESTATUS[0]}
echo "--- 退出码 $RC1 ---"

echo
echo "=== S-4：ladder 负对照 $(date '+%T') ==="
"$PY" -u _bk_exp.py $COMMON --omega-mode ladder --omega-max-deg 5.0 \
      --tag ldsmoke --out _exp/_bk_ps 2>&1 | tee _w2_r185_ld.log | tail -12
RC2=${PIPESTATUS[0]}
echo "--- 退出码 $RC2 ---"

echo
echo "=== 判据汇总 ==="
# ★ 修（**本轮第 6 个自查假阳性**）：原来写 `$(grep -c X f || echo 0)` ——
#   但 `grep -c` 在**无匹配**时**自己就打印 `0` 并返回 1** ⇒ `|| echo 0` 又补一个
#   ⇒ 变量变成 "0\n0" ⇒ `[ "$X" = "0" ]` 判假 ⇒ 误报"打印没门控"。
#   ⇒ 正确写法：`grep -c` 后面接 `|| true`（**不要**再 echo），或统一用 awk 计数。
cnt() { grep -c "$2" "$1" 2>/dev/null || true; }
HIT_PS=$(cnt _w2_r185_ps.log '★★★ R182')
HIT_LD=$(cnt _w2_r185_ld.log '★★★ R182')
HIT_NOTMAX=$(cnt _w2_r185_ps.log '不是.*总张角')
HIT_CMP=$(cnt _w2_r185_ps.log 'ladder.*的相邻步长会是')
# 兜底：万一还是空串，按 0 处理
HIT_PS=${HIT_PS:-0}; HIT_LD=${HIT_LD:-0}
HIT_NOTMAX=${HIT_NOTMAX:-0}; HIT_CMP=${HIT_CMP:-0}
echo "  S-1 perstep 退出码 = $RC1            $([ "$RC1" = "0" ] && echo ✅ || echo ❌)"
echo "  S-1 ladder  退出码 = $RC2            $([ "$RC2" = "0" ] && echo ✅ || echo ❌)"
echo "  S-2 perstep 日志里 '★★★ R182' 行数 = $HIT_PS   $([ "$HIT_PS" -ge 1 ] && echo ✅ || echo ❌)"
echo "  S-2 其中明说'不是总张角'的行数      = $HIT_NOTMAX   $([ "$HIT_NOTMAX" -ge 1 ] && echo ✅ || echo ❌)"
echo "  S-3 出现 ladder/perstep 步长对比     = $HIT_CMP   $([ "$HIT_CMP" -ge 1 ] && echo ✅ || echo ❌)"
echo "  S-4 ladder 日志里 '★★★ R182' 行数   = $HIT_LD   $([ "$HIT_LD" = "0" ] && echo ✅ 门控正确 || echo ❌ 打印没门控)"
echo
echo "=== S-5：两臂的 F3 面片对数（应一致，由变体表定、与 ω 无关）==="
for t in pssmoke ldsmoke; do
  f="_exp/_bk_ps/dry_$t/meta.json"
  if [ -f "$f" ]; then
    printf '  %-10s ' "$t"
    "$PY" -c 'import json,sys; m=json.load(open(sys.argv[1]));
g=m.get("gamma_RS") or {};
fin=[k for k,v in g.items() if v is not None];
print("`gamma_RS` 有限条目 = %d ；omega_mode = %s ；omega_max_deg = %s"
      % (len(fin), m.get("omega_mode"), m.get("omega_max_deg")))' "$f"
  else
    echo "  $t: (无 meta)"
  fi
done
echo
echo "=== 结束 $(date '+%T') ==="
