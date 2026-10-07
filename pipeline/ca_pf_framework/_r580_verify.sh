#!/bin/bash
# _r580_verify.sh --- ★ 回答"现在的代码还和优化前一样能正确运行吗？"
#
# 四步，全部留档：
#   A. 语法（py_compile 7 个文件）
#   B. 快照（`_r580_snapshot.sh`）+ SHA256 校验
#   C. **全量逐位回归**（`_r576_regress.sh`，与归档产物逐位对照）
#   D. **真实路径冒烟**（`_r578_smoke.sh`，`_bk_exp.py` 真算例，30 步）
#   E. 所有开关**显式打开**时也能跑通（真实路径冒烟，全开档）
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG="${1:-baseline_R579}"
LOG="_w2_r580_verify.log"
: > "$LOG"
say() { echo "$@" | tee -a "$LOG"; }

say "=============================================================="
say "R580 验证：当前代码能否像优化前一样正确运行"
say "时间：$(date '+%F %T')   快照 tag：$TAG"
say "=============================================================="

# ---------------- A. 语法 ----------------
say ""
say "── A. 语法检查（py_compile）──"
AFILES=(windowB_surface.py windowB_pf3d.py windowB_par.py windowB_lath.py
        windowB_acct.py windowB_pf.py _bk_exp.py)
AOK=0
for f in "${AFILES[@]}"; do
  if "$PY" -m py_compile "$f" 2>>"$LOG"; then
    say "  ✅ $f"
  else
    say "  ❌ $f  语法错！"
    AOK=1
  fi
done
say "  A 判定：$([ $AOK -eq 0 ] && echo '全部通过' || echo '有语法错')"

# ---------------- B. 快照 ----------------
say ""
say "── B. 快照 + SHA256 ──"
bash _r580_snapshot.sh "$TAG" "R580 验证前的当前代码（含 pf_phi onfly / grad_mode）" 2>&1 | tee -a "$LOG"
SNAPDIR=$(ls -dt _r580_backup/${TAG}_* 2>/dev/null | head -1)
BOK=1
if [ -n "$SNAPDIR" ]; then
  if ( cd "$SNAPDIR" && sha256sum -c SHA256SUMS >/dev/null 2>&1 ); then
    say "  ✅ SHA256 校验通过：$SNAPDIR"
    BOK=0
  else
    say "  ❌ SHA256 校验失败：$SNAPDIR"
  fi
else
  say "  ❌ 没找到快照目录"
fi

# ---------------- C. 全量逐位回归 ----------------
say ""
say "── C. 全量逐位回归（_r576_regress.sh，与**归档产物**逐位对照）──"
bash _r576_regress.sh > _w2_r580_regress.log 2>&1
CRC=$?
say "  rc=$CRC"
grep -E '共有列|逐位一致|差异字段数|FAIL *=|总判定|自检' _w2_r580_regress.log \
  | tail -12 | sed 's/^/    /' | tee -a "$LOG"
COK=0
grep -q 'ALL PASS' _w2_r580_regress.log || COK=1
if grep -qE 'FAIL *= *0' _w2_r580_regress.log; then :; else COK=1; fi
say "  C 判定：$([ $COK -eq 0 ] && echo '✅ 逐位回归全绿' || echo '❌ 回归未全绿（见 _w2_r580_regress.log）')"

# ---------------- D. 真实路径冒烟（默认档）----------------
say ""
say "── D. 真实路径冒烟（_r578_smoke.sh，全默认 = 归档旧路）──"
bash _r578_smoke.sh > _w2_r580_smoke_default.log 2>&1
DRC=$?
say "  rc=$DRC"
tail -14 _w2_r580_smoke_default.log | sed 's/^/    /' | tee -a "$LOG"
DOK=0
grep -qiE 'Traceback|Error' _w2_r580_smoke_default.log && DOK=1
[ "$DRC" -eq 0 ] || DOK=1
say "  D 判定：$([ $DOK -eq 0 ] && echo '✅ 真实路径跑通' || echo '❌ 真实路径有问题')"

# ---------------- E. 真实路径冒烟（开关全开）----------------
say ""
say "── E. 真实路径冒烟（**所有新开关全开**）──"
# ⚠ 只开"逐位相同"的档；`fft=rfft` 非逐位，单列一档
env R561_EPS0=einsum R561_EDPAIR=gather R561_KLOOP=act R561_ACT=bincount \
    R561_ARG2=copyto R571_GRAD=sliced R571_PFPHI=onfly \
    bash _r578_smoke.sh > _w2_r580_smoke_allon.log 2>&1
ERC=$?
say "  rc=$ERC"
tail -10 _w2_r580_smoke_allon.log | sed 's/^/    /' | tee -a "$LOG"
EOK=0
grep -qiE 'Traceback|Error' _w2_r580_smoke_allon.log && EOK=1
[ "$ERC" -eq 0 ] || EOK=1
say "  E 判定：$([ $EOK -eq 0 ] && echo '✅ 开关全开也能跑通' || echo '❌ 开关全开有问题')"
say "  ⚠ 记账：`R561_*`/`R571_*` 这些环境变量只有 `_r576_prof.py` 那条路认；"
say "     `_r578_smoke.sh` 走的是 `_bk_exp.py` 的 CLI 参数 ⇒ 本档实际仍是默认档。"
say "     真正的"开关全开"走 D 的 CLI 版本（见下面 F）。"

# ---------------- F. 真实路径冒烟（CLI 开关全开）----------------
say ""
say "── F. 真实路径冒烟（`_bk_exp.py` 的 **CLI 开关**全开）──"
if [ -f _r580_smoke_cli.sh ]; then
  bash _r580_smoke_cli.sh > _w2_r580_smoke_cli.log 2>&1
  FRC=$?
  say "  rc=$FRC"
  tail -12 _w2_r580_smoke_cli.log | sed 's/^/    /' | tee -a "$LOG"
  FOK=0
  grep -qiE 'Traceback|Error' _w2_r580_smoke_cli.log && FOK=1
  [ "$FRC" -eq 0 ] || FOK=1
  say "  F 判定：$([ $FOK -eq 0 ] && echo '✅ CLI 全开跑通' || echo '❌ CLI 全开有问题')"
else
  say "  （缺 _r580_smoke_cli.sh，跳过）"
  FOK=1
fi

# ---------------- 汇总 ----------------
say ""
say "=============================================================="
say "汇总：A 语法=$([ $AOK -eq 0 ] && echo PASS || echo FAIL)"\
"  B 快照=$([ $BOK -eq 0 ] && echo PASS || echo FAIL)"\
"  C 逐位回归=$([ $COK -eq 0 ] && echo PASS || echo FAIL)"\
"  D 真实路径=$([ $DOK -eq 0 ] && echo PASS || echo FAIL)"\
"  F CLI全开=$([ $FOK -eq 0 ] && echo PASS || echo FAIL)"
TOT=$((AOK+BOK+COK+DOK+FOK))
say "★ 总判定：$([ $TOT -eq 0 ] && echo '**全部通过 —— 当前代码与优化前一致可正确运行**' || echo "**有 $TOT 项未通过**")"
say "=============================================================="
exit $TOT
