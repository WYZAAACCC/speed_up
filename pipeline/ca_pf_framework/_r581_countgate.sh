#!/bin/bash
# _r581_countgate.sh --- ★ goal §(10)③：把**计数回归固化为硬断言**（判据④ 的一半）。
#
# ## 为什么必须有它（不是"数值回归全绿就够了"）
# AGENTS **P2**：重构 `_soft_sigma` 时漏删一行 ⇒ 每步把最贵的算子跑**两遍**（占单步 **30%**），
# 而**数值逐位相同**、`_r30_regress.sh` **完全看不见**。
# ⇒ 只有"每步调用次数"能抓这一类**性能回归**。
#
# ## 判据（**预先写死**）
# | 函数 | 每步调用次数 | 为什么必须是 1 |
# |---|---|---|
# | `el.sigma_tensor` | 1 | 多调用方；多跑一次 = 白烧 30% |
# | `el.eps0_fields` | 1 | 同上 |
# | `fe.ed.soft_phi` | 1 | 同上（`onfly` 档下它是 `el.e0.stream`） |
# | `argmin2` | 1 | 同上（L5 的靶子） |
#
# ## ★★ 本脚本与 `_r572_prof_ab.sh` 里的旧版有什么不同
# 1. **独立**（不再埋在 A/B 脚本里）；
# 2. **带负对照**（旧版**没有**）—— 见 §NC；
# 3. 接受**任意日志路径**做单测（不必每次跑仿真）。
#
# ## 用法
#   bash _r581_countgate.sh                  # 跑一个真实短算例 + 判据 + 负对照
#   bash _r581_countgate.sh <日志路径>        # 只对已有日志做判据（单测用）
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAGSUF="${R581CG_NV:-24}x${R581CG_N:-64}_w${R581CG_W:-4}"
BEFORE="env R561_N=${R581CG_N:-64} R561_NV=${R581CG_NV:-24} R561_STEPS=${R581CG_STEPS:-8} R561_WORKERS=${R581CG_W:-4}"
LOGDIR=_w2_r581_cgate
mkdir -p "$LOGDIR"

# ---------------------------------------------------------------- 判据本体
# check <日志> ；返回 0 = PASS，1 = FAIL。**判据写死在这里，负对照也调它。**
check() {
  local f="$1" bad=0
  for pair in "el.sigma_tensor:1" "el.eps0_fields:1" "fe.ed.soft_phi:1" "argmin2:1"; do
    local k="${pair%%:*}" want="${pair##*:}" got
    got=$(grep -E "^    ${k} " "$f" 2>/dev/null | head -1 | awk '{print $2}')
    if [ -z "$got" ]; then
      echo "    ❌ 计数回归：日志里**找不到** '${k}' 的调用次数 ⇒ FAIL"; bad=1; continue
    fi
    if awk "BEGIN{exit !($got == $want)}"; then
      echo "    ✅ ${k} = ${got}/步（应为 ${want}）"
    else
      echo "    ❌ ${k} = ${got}/步（应为 ${want}）**性能回归**"; bad=1
    fi
  done
  return "$bad"
}

# ---------------------------------------------------------------- 只做单测
if [ "$#" -ge 1 ] && [ -f "$1" ]; then
  echo "=== 只对已有日志做判据：$1 ==="
  check "$1"; exit $?
fi

echo "=============================================================================="
echo "R581 计数回归硬断言（goal §(10)③）   $(date '+%F %T')"
echo "=============================================================================="
echo "── 0. 宿主指纹（**跨会话绝对值不可比**，P1）──"
$PY _r576_hostfp.py 2>/dev/null | sed 's/^/   /'

echo
echo "── 1. 跑一个真实短算例并采集剖面（$TAGSUF）──"
$BEFORE "$PY" _r561_opfacct.py > /dev/null 2>&1
LIVE="$LOGDIR/acct_live_${TAGSUF}.log"
cp -f _w2_r561_acct.log "$LIVE" 2>/dev/null
echo "   日志 = $LIVE（$(wc -l < "$LIVE" 2>/dev/null || echo 0) 行）"

echo
echo "── 2. 【P1 正判据】对**真实**日志断言 ──"
check "$LIVE"; P1=$?
echo "   ⇒ P1 = $([ "$P1" = 0 ] && echo '✅ PASS' || echo '❌ FAIL')"

echo
echo "── 3. 【NC-A】**把 el.sigma_tensor 从 1 改成 2**，判据必须 FAIL ──"
NCA="$LOGDIR/acct_nca.log"
sed -E 's/^(    el\.sigma_tensor +)1([. ])/\g<1>2\g<2>/' "$LIVE" > "$NCA"
echo "   改动处：$(diff <(grep -E '^    el\.sigma_tensor ' "$LIVE") \
                       <(grep -E '^    el\.sigma_tensor ' "$NCA") | head -4 | tr '\n' ' ')"
check "$NCA" > /dev/null 2>&1; NCA_RC=$?
echo "   ⇒ NC-A = $([ "$NCA_RC" != 0 ] && echo '✅ 判据**失败**了（有分辨力）' || echo '❌ **判据恒真**')"

echo
echo "── 4. 【NC-B】**删掉 el.eps0_fields 那一行**，判据必须 FAIL ──"
NCB="$LOGDIR/acct_ncb.log"
grep -vE '^    el\.eps0_fields ' "$LIVE" > "$NCB"
check "$NCB" > /dev/null 2>&1; NCB_RC=$?
echo "   ⇒ NC-B = $([ "$NCB_RC" != 0 ] && echo '✅ 判据**失败**了' || echo '❌ **判据恒真**')"

echo
echo "── 5. 【NC-C】**仪表活性**：计数器必须能报出**不同的数**（否则它可能只是个常数）──"
echo "   证据（**本会话实测**，不是推理）："
echo '     · L6 `--ufv-c 1`：`op._minmod` 的 n/步 **42 → 0**（走 C 融合核，不再调 numpy 的 _minmod）'
echo '     · L5 `--argmin2-reuse 1`：`argmin2.winner` 的计数 **4 → 0**（复用 region 的 winner）'
echo '     · 两者都在 `R581_OPOPT_L1L2.md` §11/§12 有留档 ⇒ **计数器不是常数**'
echo "   ⚠ 记账：本脚本的 NC-A/NC-B 验的是**判据**能失败；NC-C 验的是**仪表**能变化。"
echo "     两者缺一不可，但性质不同。"
echo '   ⚠ **本脚本第一版又踩了反引号坑**（`echo "… \`cmd\` …"` 里的反引号**被执行**）——'
echo '     与 `_r581_guardchk.sh` **同一个错**，**同一会话里犯第二次**。'
echo '     ⇒ 纪律：**脚本里凡是 echo 的文本，一律用单引号**；要插变量再用双引号。'

echo
echo "=============================================================================="
if [ "$P1" = 0 ] && [ "$NCA_RC" != 0 ] && [ "$NCB_RC" != 0 ]; then
  echo "✅ **计数回归硬断言全部通过**（P1 正判据 + 两个负对照都有分辨力）"
  echo "   ⇒ 可写进任何回归门：\`bash _r581_countgate.sh\`（FAIL 时返回非 0）"
  RC=0
else
  echo "❌ **有判据未通过** —— P1=$P1  NC-A=$NCA_RC  NC-B=$NCB_RC"
  RC=1
fi
echo "=== R581 COUNTGATE DONE $(date '+%F %T') ==="
exit $RC
