#!/bin/bash
# _r580_rollback_test.sh --- ★ 实测"回滚真的能用"（goal 判据 ② 要求：实测回滚一次并验证恢复成功）
#
# 做法：挑一个**两个快照里都没被改过**的文件（windowB_par.py）做**可逆的人为破坏**，
#       然后走 `_r580_rollback.sh afterP1 --apply` 真恢复，再逐条验证：
#         T1 破坏后 sha256 确实变了（否则这个测试本身没意义 —— 负对照意识）
#         T2 dry-run 能正确报出"不同"
#         T3 apply 后 sha256 回到快照值
#         T4 回滚动作自己留了档（rollback_from_afterP1_*）
#         T5 恢复后的代码真的能跑（逐位回归）
#         T6 坏快照会被拒绝（负对照：把 SHA256SUMS 改歪，必须 exit≠0 且不覆盖文件）
set -u
cd "$(dirname "$0")" || exit 1
LOG="_r580_rollback_test.log"
: > "$LOG"
ok(){ echo "  ✅ $*" | tee -a "$LOG"; }
bad(){ echo "  ❌ $*" | tee -a "$LOG"; FAIL=1; }
FAIL=0
TARGET=windowB_par.py
SNAP="_r580_backup/afterP1_20261002_065520"

echo "=== 回滚实测 $(date '+%F %T') ===" | tee -a "$LOG"
H0=$(sha256sum "$TARGET" | cut -c1-16)
echo "T0 起始 $TARGET sha256=${H0}" | tee -a "$LOG"

# ---- T1 人为破坏（可逆：只加一行注释）------------------------------------
cp -p "$TARGET" "_r580_rollback_test_${TARGET}.orig"
printf '\n# _r580_rollback_test 人为破坏标记 %s\n' "$(date '+%s')" >> "$TARGET"
H1=$(sha256sum "$TARGET" | cut -c1-16)
if [ "$H1" != "$H0" ]; then ok "T1 破坏后 hash 变了（${H0} → ${H1}）—— 负对照成立"; else bad "T1 破坏后 hash 没变 ⇒ 本测试无意义"; fi

# ---- T2 dry-run -----------------------------------------------------------
OUT=$(bash _r580_rollback.sh afterP1 2>&1)
if echo "$OUT" | grep -q "\[不同\] $TARGET"; then ok "T2 dry-run 报出 [不同] $TARGET"; else bad "T2 dry-run 没报出差异：$(echo "$OUT" | tail -3)"; fi
if cmp -s "$SNAP/$TARGET" "$TARGET"; then bad "T2 dry-run 竟然改了文件！"; else ok "T2 dry-run 未改动文件"; fi

# ---- T3 apply -------------------------------------------------------------
OUT=$(bash _r580_rollback.sh afterP1 --apply --no-regress 2>&1)
echo "$OUT" | tail -8 | sed 's/^/    | /' >> "$LOG"
H2=$(sha256sum "$TARGET" | cut -c1-16)
if [ "$H2" = "$H0" ]; then ok "T3 apply 后 sha256 回到快照值（${H2}）"; else bad "T3 恢复失败：期望 ${H0} 实得 ${H2}"; fi

# ---- T4 回滚自身留档 ------------------------------------------------------
if ls -1d _r580_backup/rollback_from_afterP1_*/ >/dev/null 2>&1; then
  ok "T4 回滚动作自己留了档：$(ls -1d _r580_backup/rollback_from_afterP1_*/ | tail -1)"
else bad "T4 没找到 rollback_from_afterP1_* 留档"; fi

# ---- T5 恢复后能跑（逐位回归）---------------------------------------------
if bash _r576_regress.sh >"_r580_rollback_test_regress.log" 2>&1; then
  ok "T5 恢复后逐位回归通过"
else
  bad "T5 恢复后回归失败，见 _r580_rollback_test_regress.log"; tail -5 "$_r580_rollback_test_regress.log" 2>/dev/null | sed 's/^/    | /' >> "$LOG"
fi

# ---- T6 负对照：坏快照必须被拒绝 ------------------------------------------
BADSNAP="_r580_backup/_TESTBADSNAP_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$BADSNAP"; cp -p "$SNAP"/*.py "$SNAP/SHA256SUMS" "$BADSNAP/"
printf '\n# 篡改\n' >> "$BADSNAP/$TARGET"          # 让内容与 SHA256SUMS 不符
HBEFORE=$(sha256sum "$TARGET" | cut -c1-16)
bash _r580_rollback.sh "_TESTBADSNAP_" --apply --no-regress >"_r580_rollback_test_bad.log" 2>&1
RC=$?
HAFTER=$(sha256sum "$TARGET" | cut -c1-16)
if [ "$RC" -ne 0 ] && [ "$HBEFORE" = "$HAFTER" ]; then
  ok "T6 坏快照被拒绝（exit=$RC）且未覆盖工作区文件"
else
  bad "T6 坏快照没被拦住（exit=$RC, hash ${HBEFORE}→${HAFTER}）"
fi
rm -rf "$BADSNAP"   # 这是本脚本自己刚建的临时目录，不在任何运行目录上

echo "=== 结论：$([ "$FAIL" -eq 0 ] && echo '全部通过 ✅' || echo '有失败项 ❌') ===" | tee -a "$LOG"
exit "$FAIL"
