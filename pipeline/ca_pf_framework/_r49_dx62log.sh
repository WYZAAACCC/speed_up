#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
f=_w2_r47_mb1s62.log
echo "=== $f  ($(wc -l < $f) lines, mtime $(stat -c %y $f | cut -c1-19))"
grep -nE '^\s*\[' "$f" | tail -6
echo "=== grep snap/write lines"
grep -nE 'snap|写入|落盘|savez' "$f" | tail -10
echo "=== tail 12"
tail -12 "$f"
