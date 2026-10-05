#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "--- 精确计数 ---"
echo -n "  print('[SEEDCARVED] k=%d carved=%s protected=%s' : "
awk "/print\\('\\[SEEDCARVED\\]/{n++} END{print n+0}" windowB_surface.py
echo -n "  if j == 0:  (排除母相)                          : "
awk "/if j == 0:/{n++} END{print n+0}" windowB_surface.py
echo -n "  _prot.add(j)                                   : "
awk "/_prot.add\\(j\\)/{n++} END{print n+0}" windowB_surface.py
/root/miniconda3/envs/ml/bin/python -m py_compile windowB_surface.py && echo "  语法 OK"

# 停旧跑（保留数据）并起新跑
TAG=t10PRT2
TS=$(date +%m%d_%H%M)
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*|*_t10_sw2.sh*) kill -9 "$P" 2>/dev/null; echo "  KILL $P" ;; esac
done
sleep 6
D=_exp/_bk_t5/dry_t10PRT
[ -d "$D" ] && mv "$D" "${D}_protbug_$TS" && echo "  t10PRT 数据 → $(basename ${D}_protbug_$TS)（保护含母相的缺陷轮）"
[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_prt_$TS.txt

PY=/root/miniconda3/envs/ml/bin/python
SEED_CLEAN=1 SEED_CLEAN_EVERY=20 SEED_PROTECT=1 SEED_PROTECT_MIN=100 \
SEED_CARVED_DBG=1 setsid $PY _t5_short.py --tag $TAG \
    --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 --ckpt-every 200 --ckpt-keep 2 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --nuc-occ-guard 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 27 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（s304b：母相不保护）"
setsid nohup bash _t10_sw2.sh $TAG 28800 > /dev/null 2>&1 < /dev/null &
echo "  swap 报警已挂"
sleep 110
P=""
for X in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
done
if [ -n "$P" ]; then
  echo "  pid=$P 历龄=$(ps -o etime= -p $P | tr -d ' ')"
  awk '/^VmRSS|^VmSwap/{printf "  %s\n", $0}' /proc/$P/status
else echo "  ⚠ 未找到进程"; fi
cd /mnt/f/speed_up && git add pipeline/ca_pf_framework/_t5_patch_protfix.py pipeline/ca_pf_framework/windowB_surface.py pipeline/ca_pf_framework/windowB_surface.py.bak_s304b pipeline/ca_pf_framework/_t10_prtchk.sh pipeline/ca_pf_framework/_t10_prtrun.sh
git commit -q -m '★★ s304 缺陷当场被抓：t10PRT 的 [SEEDCARVED] 首次真实记账显示 protected=[0,1,111] —— 场 0 是母相，init_parent 令 phi[0]=-min(phi[1:]) 故 φ0 负胞数极大、恒被保护；而新板条形核处母相必须被擦成正值(否则 region=argmin 仍选母相、板条在物理相口径下不出现) ⇒ 我的保护会把核变成死核。s304b：保护范围排除场 0，只保护变体场 1..nv。t10PRT 数据保留为 dry_t10PRT_protbug_*，起 t10PRT2 重验。另：carved 记账同时确认了擦除机制真实存在(k=2 播时改到 0,1,111)'
git log --oneline -1
