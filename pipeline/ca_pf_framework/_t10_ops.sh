#!/bin/bash
# _t10_ops.sh --- ① 算子开关是否用优化档 ② 实际用了几个核
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10N160.log
echo "════ ① 算子开关（引擎自己打印的权威清单）════"
grep -a '算子开关' "$L" | tail -1
echo
echo "  ── 判据：对照 AGENTS.md §7.5 的已落地开关（优化档 = 右边那一列）──"
echo "     eps0      loop/einsum/gemm   → 优化 = einsum (1.76×)"
echo "     ed_pair   full/gather        → 优化 = gather (4.92×)"
echo "     k_loop    full/act           → 优化 = act  （⚠ 提速未确立，仅记账）"
echo "     act       unique/bincount    → 优化 = bincount (微基准 6.12×)"
echo "     argmin2   legacy/copyto      → 优化 = copyto (微基准 1.265×)"
echo "     grad      legacy/sliced      → 优化 = sliced （未确立）"
echo "     pf_phi    materialized/onfly → 优化 = onfly（省内存，速度中性）"
echo "     fft       c2c/rfft           → 优化 = rfft (1.71×) ⚠ 非逐位"
echo
echo "════ ② CPU 核数（实测）════"
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10N160 "*) P=$X; break ;; esac
done
if [ -z "$P" ]; then echo "  ⚠ 引擎不在"; exit 0; fi
echo "  pid = $P"
echo "  --- taskset 亲和性（允许跑在哪些核）---"
taskset -pc "$P" 2>/dev/null | sed 's/^/    /'
echo "  --- /proc 状态 ---"
awk '/^Cpus_allowed_list|^Threads|^VmRSS|^VmHWM/{printf "    %s\n", $0}' /proc/$P/status
echo "  --- 主机逻辑核数 ---"; nproc | sed 's/^/    /'
echo "  --- 实时占用（%CPU = 核数×100）---"
ps -o pid,etime,time,pcpu,rss --no-headers -p "$P" | sed 's/^/    /'
echo "  --- argv 里的并行开关 ---"
tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-nthreads [0-9]+|\-\-cores [0-9-]+' | sed 's/^/    /'
echo "  --- 线程数实测 ---"
echo "    /proc/$P/task 下的线程 = $(ls /proc/$P/task 2>/dev/null | wc -l)"
