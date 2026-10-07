#!/usr/bin/env bash
# _collect.sh --- 汇总所有作业的关键行（跳过 RuntimeWarning 噪声）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
show() {
  echo "===== $1 ====="
  if [ -f "$1" ]; then
    grep -v -e 'RuntimeWarning' -e 'self.reinitialize' -e '^  #' "$1" | tail -"${2:-14}"
  else
    echo '(missing)'
  fi
  echo
}
show _t22.log 16
show _t23.log 16
show _t16prod.log 8
show _t13b.log 8
echo "===== procs ====="
ps -o pid,etime,pcpu,rss,args --no-headers -C python | cut -c1-78
echo "===== mem ====="
free -g | head -2
