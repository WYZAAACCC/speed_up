#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "--- 精确计数（各应 = 2）---"
echo -n "  os.environ.get('SEED_PROTECT') == '1' : "
awk "/os.environ.get\\('SEED_PROTECT'\\) == '1'/{n++} END{print n+0}" windowB_surface.py
echo -n "  j not in _prot                        : "
awk "/j not in _prot/{n++} END{print n+0}" windowB_surface.py
echo -n "  _carved = \\[j for j in range           : "
awk "/_carved = \\[j for j in range/{n++} END{print n+0}" windowB_surface.py
echo -n "  [SEEDCARVED]                          : "
awk "/\\[SEEDCARVED\\]/{n++} END{print n+0}" windowB_surface.py
echo -n "  SEED_PROTECT_MIN                      : "
awk "/SEED_PROTECT_MIN/{n++} END{print n+0}" windowB_surface.py
echo "--- 语法 ---"
/root/miniconda3/envs/ml/bin/python -m py_compile windowB_surface.py && echo "  OK"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_patch_seedprot.py \
        pipeline/ca_pf_framework/windowB_surface.py \
        pipeline/ca_pf_framework/windowB_surface.py.bak_s304prot \
        pipeline/ca_pf_framework/_t10_ev70.py \
        pipeline/ca_pf_framework/_t10_deadseed.py \
        pipeline/ca_pf_framework/_t10_v200.sh \
        pipeline/ca_pf_framework/_t10_goal2chk.sh
git commit -q -m '★★ 形核正确性缺陷定位：t10CL2@step200 有 47 个形核事件，其中 10 个(21%)一个胞都不剩(68,119-126,162)，带内胞分布是双峰(>=1623 或 =0)、无中间态 ⇒ 是被抹掉而非没长起来；且 119-126 是 8 个连续同变体(6)场 ⇒ 整段块被一次性抹掉，与 phi[j]=max(phi[j],-sdf) 吻合。另：我那个 carved_j 量具一直恒为 0（判定写在 max 之后）⇒ 此前把"擦除未触发"当证据是错的(第10次量具失误)。s304：写前记 carved 掩码(修量具) + 保护已有实质核(负胞数>=SEED_PROTECT_MIN 默认100)不被后来籽晶抹掉；默认全关、归档逐位不变、独有成功串[SEEDCARVED]。另修正"形核=70"的计数错误(是 grep 多算行；逐行解析真值 47)'
git log --oneline -1
