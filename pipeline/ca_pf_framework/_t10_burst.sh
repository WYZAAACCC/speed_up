#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10N160.log
echo "=== NOW $(date '+%H:%M:%S') ==="
echo "--- ★ s295 分诊计数（burst 进度表；每次计数变化打一行）---"
grep -a 's295 形核分诊' "$L" 2>/dev/null | tail -6 | cut -c1-260
echo "  行数 = $(grep -ac 's295 形核分诊' "$L" 2>/dev/null)"
echo
echo "--- athermal 事件 / 补投轮 ---"
echo "  athermal 行 = $(grep -ac 'athermal' "$L" 2>/dev/null)"
grep -a 's292 补投轮' "$L" 2>/dev/null | tail -3
echo "  fresh 被拒退回 stack = $(grep -ac 'fresh` 被拒' "$L" 2>/dev/null)"
echo
echo "--- 最近写入的日志行（含时间戳推断）---"
tail -5 "$L" 2>/dev/null | cut -c1-190
echo
echo "--- 数据目录文件时间（看是否还在写）---"
ls -la --time-style=+%H:%M:%S _exp/_bk_t5/dry_t10N160/ 2>/dev/null | tail -6
