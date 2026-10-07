#!/bin/bash
# 杀掉 T12-D12b 遗留的 python（按 cwd 限定，不误伤别的作业）
# 记账：AGENTS.md §3.10/§3.11 —— 停后台作业 ≠ 停它起的子进程；必须按 cwd 显式查一遍。
for P in $(pgrep -x python); do
  C=$(readlink /proc/"$P"/cwd 2>/dev/null)
  case "$C" in
    *ca_pf_framework*) kill -9 "$P"; echo "killed $P (cwd=$C)";;
    *) echo "skip $P (cwd=$C)";;
  esac
done
sleep 2
echo "remaining python: $(pgrep -x python | wc -l)"
