#!/usr/bin/env bash
# _collect2.sh --- 汇总（含 T21 / T11j / T24rve）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
show() {
  echo "===== $1 ====="
  if [ -f "$1" ]; then
    grep -v -e 'RuntimeWarning' -e 'self.reinitialize' -e '^  #' -e 'g.advance(' "$1" | tail -"${2:-14}"
  else
    echo '(missing)'
  fi
  echo
}
show _t21.log 14
show _t11j_after_a1a2.log 14
show _t16prod.log 5
show _t13b.log 5
show _t24rve.log 6
echo "===== procs ====="
ps -o pid,etime,pcpu,rss,args --no-headers -C python | cut -c1-74
free -g | head -2
