#!/bin/bash
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_param_audit.py \
        pipeline/ca_pf_framework/_t10_g3chk.sh \
        pipeline/ca_pf_framework/_t10_final.sh
git commit -q -F - <<'MSG'
新goal ①：核验在跑的 t10PRT2 确为最新代码 —— windowB_surface.py mtime 10:03:48 (sha 131c8383b772)，引擎启动 10:04:09 ⇒ 代码早于启动 ⇒ 继续跑、不重启。已核环境变量 SEED_CLEAN=1 SEED_CLEAN_EVERY=20 SEED_CARVED_DBG=1 SEED_PROTECT=1 SEED_PROTECT_MIN=100；VmSwap=0，历龄 1:58。

新goal ②：按新规则（文献→推导→标定）处理无出处参数。σ_y(873K) 文献取不到（搜索仅返标题；NASA NTRS PDF 返回 403）⇒ 按规则升级到推导，而 R601 已给出推导并证明 η 对 σ_y 不敏感（σ_y ∈ 0.1–2 GPa 结论不变）⇒ 无需标定。

新goal ③：新增参数出处总账工具 _t10_param_audit.py。首轮筛查 23 个物理参数 × 162 份文档：全部至少有 1 处出处关键词命中；但**仅命中「标定」**的有 4 个 —— DS_REF（参考扩散系数）、mob（相场迁移率 M）、nvar（变体数）、B（每块板条数）⇒ 按新规则这 4 个应先找文献。

局限（已记）：grep 命中 ≠ 出处可靠，命中的仍需读原文确认；argv 提取因 tag 匹配失败返回 0 字符，需修；尚未扫描 *.py 注释。
MSG
git log --oneline -1
