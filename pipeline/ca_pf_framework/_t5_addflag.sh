#!/bin/bash
# _t5_addflag.sh --- 找 `--nuc-law` 的定义位置，把 `--therm-hist` 加在它旁边
cd "$(dirname "$0")" || exit 1
grep -n "add_argument('--nuc-law'" _bk_exp.py | head -2 | cut -c1-110 | sed 's/^/  /'
grep -n "add_argument('--cool-rate'" _bk_exp.py | head -2 | cut -c1-110 | sed 's/^/  /'
grep -n "add_argument('--gamma0'" _bk_exp.py | head -2 | cut -c1-110 | sed 's/^/  /'
