#!/bin/bash
# _r581_crit78.sh --- 复核 **判据⑦（能开尽开 vs 全默认，≥5 轮 + 区间）** 与 **判据⑧（车道表 + load average）**
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════════ ⑦ 配对提速（能开尽开 vs 全默认）════════'
echo '  ── 找记录：1.2xx× / 区间 / 5 轮 ──'
for f in R581_OPOPT_L1L2.md R580_VERIFY.md R581_FINAL_SUMMARY.md OPOPT_LEDGER.md R577_OPOPT2.md; do
  [ -f "$f" ] || continue
  n=$(grep -cE '1\.2[0-9]+×|区间 \[|5 轮|五轮' "$f" 2>/dev/null || echo 0)
  printf '  %-26s 命中 %s 行\n' "$f" "$n"
done
echo
echo '  ── 具体行（前 6）──'
grep -hnE '能开尽开|全默认' R58*.md 2>/dev/null | head -6 | cut -c1-118 | sed 's/^/    /'
echo
echo '════════ ⑧ 并行是真的（车道表 / load average / 各道占用）════════'
echo '  ── 找"车道表"类记录 ──'
grep -lnE '车道表|taskset|load average|loadavg' R58*.md 2>/dev/null | head -6 | sed 's/^/    /'
echo
echo '  ── 现成的并行编排器 ──'
ls -1 _r579_par.sh _r581_par.sh _r579_cpusamp* _r581_cpusamp* 2>/dev/null | sed 's/^/    /'
echo
echo '  ── **当前**的 load average 与各道占用（实测，可入档）──'
cat /proc/loadavg | sed 's/^/    loadavg: /'
nproc | sed 's/^/    nproc: /'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  cpu=$(ps -o %cpu= -p "$p" 2>/dev/null | tr -d ' ')
  et=$(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')
  printf '    tag=%-9s %%CPU=%-7s 时长=%s\n' "${tag:-?}" "$cpu" "$et"
done
echo
echo '  ── 绑核情况（taskset 掩码）──'
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
  tag=$(printf '%s' "$c" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
  m=$(taskset -pc "$p" 2>/dev/null | sed 's/.*: //')
  printf '    tag=%-9s 允许的核=%s\n' "${tag:-?}" "$m"
done
