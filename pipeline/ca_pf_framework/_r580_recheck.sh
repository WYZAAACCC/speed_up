#!/bin/bash
# _r580_recheck.sh --- 修正 `_r580_verify.sh` D/E/F 段的**量具 bug** 后重判。
#
# ## 我的 bug（必须留档，AGENTS §7.5 P6/P13）
# `_r580_verify.sh` 里写的是 `grep -qiE 'Traceback|Error' _w2_r580_smoke_default.log`，
# 但那个文件里装的是 `_r578_smoke.sh` 的 **stdout**，其中有一行是脚本自己 echo 的
# **`exit=0  traceback=0`** ⇒ `-i` 之下 "traceback" 命中 ⇒ **判 FAIL**。
# 即**检查器匹配到了自己的汇总行** —— 与"量具错了和被测量对象错了长得一模一样"同源。
# 正确做法：查**每臂自己的日志**（`_w2_r578_full.log` / `_w2_r578_act.log`），
# 并且把"自报的计数行"排除掉。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1

echo "############ D 重判：默认档（归档旧路）"
for F in _w2_r578_full.log _w2_r578_act.log _w2_r580_base.log; do
  [ -f "$F" ] || { echo "  (缺 $F)"; continue; }
  TB=$(grep -c '^Traceback' "$F" || true)
  ER=$(grep -cE '^(ValueError|RuntimeError|TypeError|KeyError|IndexError|AttributeError|AssertionError)' "$F" || true)
  printf '  %-24s Traceback=%s  异常行=%s  末行=%s\n' "$F" "$TB" "$ER" "$(tail -1 "$F" | cut -c1-90)"
done

echo
echo "############ F：CLI 开关全开档"
if [ -f _w2_r580_smoke_cli.log ]; then
  grep -E 'C-1a|C-1b|exit=|算子开关|C-2|C-3|C-4|共有列|✅|❌|PASS|FAIL' _w2_r580_smoke_cli.log | head -30
else
  echo "  (还没出)"
fi
for F in _w2_r580_allon.log _w2_r580_neg.log; do
  [ -f "$F" ] || { echo "  (缺 $F)"; continue; }
  TB=$(grep -c '^Traceback' "$F" || true)
  printf '  %-24s Traceback=%s  末行=%s\n' "$F" "$TB" "$(tail -1 "$F" | cut -c1-90)"
done
