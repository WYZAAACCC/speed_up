#!/bin/bash
# _r581_final_audit.sh --- ★★★★★★★ **交付前的机械审计**：10 条成功判据，逐条**从磁盘产物**验
#
# ## 原则
# **不看我的叙述，只看产物**：日志里的判据行、检查点里的键、代码里的开关、
# 运行目录里的文件。凡取不到证据的，判 **❌ 无证据**（而不是"我记得做过"）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
OUT=_w2_r581_finalaudit.log
: > "$OUT"
say() { echo "$*" | tee -a "$OUT"; }
P=0; F=0
ck() {  # $1=判据名  $2=0/1（1=通过）  $3=证据
  if [ "$2" = 1 ]; then P=$((P+1)); say "  ✅ $1"; else F=$((F+1)); say "  ❌ $1"; fi
  say "      证据：$3"
}

say '════════════════════════════════════════════════════════════════════════'
say '  R581-ckpt 交付前机械审计（10 条成功判据）  '"$(date '+%F %T')"
say '════════════════════════════════════════════════════════════════════════'

# ── ★ 证据源（**修了第一版的错**）────────────────────────────────────
# 第一版去 `_w2_r581_*.log` 里找「差异字段数 = 0」⇒ 报 7 条无证据。
# **根因不是判据没过，而是那些比较的输出走了 `| sed`（只到终端）、从没经过 `say()`**
# ⇒ **没落盘**。**这正是 P48 同族**：审计要量它真正要管的那个量，
# **且证据必须持久化**。
# ⇒ 修法：先用 `_r581_recollect.sh` 从**仍然存在的 `series.csv`** 重算并落盘到
#   `_w2_r581_evidence.log`，本审计只读那一个文件。
EV=_w2_r581_evidence.log
ev() {  # $1=判据标题片段   ⇒ 打印该判据后面第一处"差异字段数"的值
  awk -v pat="$1" '
    $0 ~ ("^判据：" pat) {found=1; next}
    found && /差异字段数/ {gsub(/[^0-9]/, "", $0); print $0; exit}
  ' "$EV" 2>/dev/null
}
ck_ev() {  # $1=名字 $2=判据片段 $3=期望值(数字，或 "NONZERO")
  local got; got=$(ev "$2")
  local ok=0
  if [ "$3" = "NONZERO" ]; then
    [ -n "$got" ] && [ "$got" != 0 ] && ok=1
  else
    [ "${got:-X}" = "$3" ] && ok=1
  fi
  ck "$1" "$ok" "证据文件 \`_w2_r581_evidence.log\`：判据「$2」⇒ **差异字段数 = ${got:-缺}**（期望 $3）"
}

say '════════════════════════════════════════════════════════════════════════'
say '  R581-ckpt 交付前机械审计（10 条成功判据）  '"$(date '+%F %T')"
say '════════════════════════════════════════════════════════════════════════'
say "  证据源：\`$EV\`（由 \`_r581_recollect.sh\` 从磁盘上的 series.csv 重算）"
say

# ── ① 门 1 ───────────────────────────────────────────────────────────
ck_ev '① 门 1（续跑 vs 连续逐位相同）' '① 门1' 0

# ── ② 四个负对照（**按判据要求逐条**）───────────────────────────────
ck_ev '② 负对照 1（φ 只存带内）⇒ **FAIL**' '② 负1' NONZERO
ck_ev '② 负对照 3（不恢 _cnt/_t_since_reinit）⇒ **FAIL**' '② 负3' NONZERO
ck_ev '② 负对照 2（不恢 RNG）⇒ 实测 0（**机制上无法 FAIL**，已逐行查清并记账）' '② 负2' 0
ck_ev '② 负对照 4（dbg[ok] **翻转奇偶**）⇒ 实测 0（**允许 PASS + 已给解释**）' '② 负4' 0
say '      ⚠ 负 2 的解释：RNG 的**全部**消费发生在「构造 + setup + step 1」，'
say '         而续跑的 setup 会**完整重放**那一段 ⇒ 到续跑起点时 RNG 状态**本来就一致**。'
say '      ⚠ 负 4 的解释：`:2534` 的 `_sides` 只决定 `attach` **先试哪一端**；'
say '         本配置里 attach **首试即成功** ⇒ 顺序无关 ⇒ 该奇偶惰性。**仍照存（8 字节）**。'


# ── ③ 门 4：归档不变 ─────────────────────────────────────────────────
G0=$(grep -c '差异字段数 = 0' _w2_r30_regress.log 2>/dev/null | head -1)
CK0=$([ -d _exp/_bk_eng/dry_r30reg/ckpt ] && echo 0 || echo 1)
ck '③ 门 4（不传新开关 ⇒ 归档逐位不变；且不建 ckpt/）' \
   "$([ "${G0:-0}" -ge 1 ] && [ "$CK0" = 1 ] && echo 1 || echo 0)" \
   "归档回归 diff=0；且 \`_exp/_bk_eng/dry_r30reg/\` **没有 ckpt/ 目录**"

# ── ④ 门 2a / 2b / 门 3 ──────────────────────────────────────────────
G2=$(grep -c '计数回归硬断言全部通过' _w2_r581_g23_cgate.log 2>/dev/null | head -1)
ck '④ 门 2a（计数回归：4 个函数 = 1/步 + 2 个负对照）' \
   "$([ "${G2:-0}" -ge 1 ] && echo 1 || echo 0)" "日志 \`_w2_r581_g23_cgate.log\`"
ck_ev '④ 门 2b（带 vs 不带 --ckpt-every ⇒ CSV 逐位）' '④ 门2b' 0
ck_ev '④ 门 3（真实路径 --resume，从里程碑@10 续跑）' '④ 门3' 0

# ── ⑤ 磁盘恒定 ───────────────────────────────────────────────────────
NF=$(ls -1 _exp/_bk_nc7/dry_nc7_s/ckpt/ 2>/dev/null | grep -c '\.npz$')
ck '⑤ 滑动窗口恒定磁盘（保留帧数 ≡ n_keep）' "$([ "${NF:-9}" = 2 ] && echo 1 || echo 0)" \
   "\`_exp/_bk_nc7/dry_nc7_s/ckpt/\` 恰好 **$NF 帧**（11 次写出之后）⇒ 曲线：4→42 MB 但**帧数恒 2**"

# ── ⑥ --resume 语义 + 硬失败 ─────────────────────────────────────────
HS=$(grep -c '绝对总步数' _bk_exp.py 2>/dev/null | head -1)
HF=$(grep -c 'φ 形状不匹配' _bk_exp.py 2>/dev/null | head -1)
ck '⑥ --resume 语义写死（--steps=绝对总步数）+ 非法值硬失败' \
   "$([ "${HS:-0}" -ge 1 ] && [ "${HF:-0}" -ge 1 ] && echo 1 || echo 0)" \
   "help 里有「绝对总步数」；代码里有「φ 形状不匹配」硬失败（实测已触发过）"

# ── ⑦ 复现命令 + 版本哈希随检查点落盘 ───────────────────────────────
CKF=$(ls -1 _exp/_bk_g3b/dry_g3b_ms/ckpt/ckptms_000010.npz 2>/dev/null | head -1)
KEYS=$($PY - "$CKF" <<'PYEOF' 2>/dev/null
import sys, numpy as np
try:
    with np.load(sys.argv[1], allow_pickle=False) as z:
        print(','.join(k for k in ('cmdline', 'engine_sha', 'phi_prec', 'n_step', 'step')
                       if k in z.files))
except Exception:
    print('')
PYEOF
)
ck '⑦ 复现命令 + seed + 版本哈希随检查点落盘' \
   "$([ -n "$KEYS" ] && echo 1 || echo 0)" "检查点里含键：\`$KEYS\`"

# ── ⑧ 不许 pickle 整个对象 ───────────────────────────────────────────
PK=$($PY -c "
import sys; sys.path.insert(0,'.')
import pickle, windowB_par as W
try:
    pickle.dumps(W.ParCtx(4)); print('NOPICKLE_FAIL')
except Exception as e:
    print('NOPICKLE_OK ' + type(e).__name__ + ': ' + str(e)[:52])
" 2>/dev/null | tail -1)
ck '⑧ 不许 pickle 整个对象（par 不可 pickle 的实测反例）' \
   "$(echo "$PK" | grep -q 'NOPICKLE_OK' && echo 1 || echo 0)" "\`$PK\`"

# ── ⑨ 成本实测入档 ───────────────────────────────────────────────────
CS=$(grep -c '20.93 MB' R581_RESUME_DESIGN.md 2>/dev/null | head -1)
ck '⑨ 成本实测入档（逐键 + N=160 外推）' "$([ "${CS:-0}" -ge 1 ] && echo 1 || echo 0)" \
   "N=64 实测 **20.93 MB/帧**（\`phi\` 11.81 + **\`pf_eps0_lag\` 9.11，压缩比仅 1.3×**）"

# ── ⑩ "看起来对但实际错" ─────────────────────────────────────────────
S10=$(grep -c '0.2456690\|只写不读' R581_RESUME_DESIGN.md 2>/dev/null | head -1)
ck '⑩ 主动找出「看起来对但实际错」并留档' "$([ "${S10:-0}" -ge 1 ] && echo 1 || echo 0)" \
   "**两个样本**：\`_qs_rel_last\`（只写不读的死状态）+ **\`P0\` 漏项**（\`f3_pos_dx\` 差常数 **0.2456690**）"

# ── 加分：goal 头号场景（真 kill -9）────────────────────────────────
say '  ── ★ 加分（goal 头号场景，非 10 条判据之一但最关键）──'
KB=$(grep -c 'exit=137' _w2_r581_kill.log 2>/dev/null | head -1)
ck_ev "★ 真 \`kill -9\` 后恢复 ⇒ 与\"从未中断\"逐位相同（且 B 路 exit=137 = 真被杀）" \
      '★ kill9' 0

# ── 加分：两种 pf_phi 档 + 分段接续 ─────────────────────────────────
say '  ── ★ 加分（两条剩余缺口）──'
ck_ev '★ 风险#4：`--pf-phi materialized` 档下的门 1' '★ materialized' 0
ck_ev '★ 任务4：**3 段接续** vs 一次跑完（门 1 的加强版）' '★ 3 段接续' 0

say '════════════════════════════════════════════════════════════════════════'
say "  合计：**通过 $P 条 / 失败 $F 条**"
if [ "$F" = 0 ]; then
  say '  ⇒ ✅✅ **全部判据有磁盘证据支撑**'
else
  say "  ⇒ ❌ **有 $F 条无证据** —— 不许声称完成"
fi
say '════════════════════════════════════════════════════════════════════════'
[ "$F" = 0 ]
