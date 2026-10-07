#!/bin/bash
# _r290_cpu.sh —— 看 `_r280` 两臂的 CPU 时间是否在涨（判断"慢"还是"卡死"）。
cd "$(dirname "$0")" || exit 1
snap() {
  printf '  %-14s %-9s %-9s %-8s %s\n' TAG PID ETIME CPUS PCNT
  for p in $(pgrep -f '_bk_exp[.]py' 2>/dev/null); do
    cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    tag=$(printf '%s' "$cl" | grep -o 'tag [A-Za-z0-9_]*' | tail -1 | sed 's/tag //')
    et=$(ps -o etime= -p "$p" 2>/dev/null | tr -d ' ')
    tm=$(ps -o times= -p "$p" 2>/dev/null | tr -d ' ')
    pc=$(ps -o pcpu= -p "$p" 2>/dev/null | tr -d ' ')
    printf '  %-14s %-9s %-9s %-8s %s\n' "${tag:-?}" "$p" "${et:-?}" "${tm:-?}" "${pc:-?}"
  done
}
echo "=== T0 $(date '+%T') ==="; snap
sleep 30
echo
echo "=== T1 $(date '+%T')（30 s 后）==="; snap
echo
echo "=== _r280 两臂日志的最新步号 ==="
for f in _w2_r280_saSet2P0_run.log _w2_r280_saSet2F2P0_run.log; do
  printf '  %-34s 步=%s  size=%s\n' "$f" \
    "$(grep -o '^  \[ *[0-9]*\]' "$f" 2>/dev/null | tail -1 | tr -d ' []')" \
    "$(stat -c %s "$f" 2>/dev/null)"
done
