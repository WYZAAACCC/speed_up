#!/bin/bash
# R49: 杀掉 mb1s62 v3（它起在 `v_by_face` 落盘之前 ⇒ 缺 `v_*_nabs` 列，
#       而那正是本轮要定口径的**物理上正确**的那个预言）⇒ 早杀早重跑（此时仅 ~80 步）。
set -u
for P in $(pgrep -f 'dx-nm 62.5' | head -5); do
  CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$CMD" in
    *_bk_exp.py*) echo "kill $P : $(echo "$CMD" | cut -c1-60)"; kill -9 "$P" ;;
    *) echo "skip $P" ;;
  esac
done
sleep 2
ps -eo pid,args --no-headers | grep -F '_bk_exp.py' | grep -v grep | cut -c1-70
