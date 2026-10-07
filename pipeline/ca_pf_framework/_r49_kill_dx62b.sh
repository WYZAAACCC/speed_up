#!/bin/bash
# R49: 精确杀掉 mb1s62 第二次启动（它起在 `ed_by_face` 扩展之前 ⇒ 没有 p90/max 列，
#       而这两列正是 R48 点名要的受控检验量）⇒ 早杀早重跑。
set -u
for P in $(pgrep -f 'dx-nm 62.5' | head -5); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$CMD" in
    *_bk_exp.py*) echo "kill $P : $(echo "$CMD" | cut -c1-70)"; kill -9 "$P" ;;
    *) echo "skip $P (不是 _bk_exp)" ;;
  esac
done
sleep 2
echo "--- 残留"
ps -eo pid,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-90
