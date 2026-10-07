#!/bin/bash
# _t5_git_s194.sh --- 提交读取工具的修正
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_readlog.sh pipeline/ca_pf_framework/_t5_auto_judge.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s194 修 _t5_readlog.sh 的 nf2 读取(原取"最后一列"是错的)

缺陷: 我上一轮读 nf2 时用了 awk '{print $NF}'(最后一列), 而 nf2 不是最后一列 => 读出来是空
=> 判据④ 的签名读取无效。
修法: 改为**按列名读**(csv.DictReader), 并额外报"nf2>0 的首次 step"。

验证: t5H3 末行 nf2=0 (step 1220), nf2>0 首次 = 尚无; t5V2 末行 nf2=0 (step 520), 首次 = 尚无
=> 判据④ 未出现(尺度 ~2580 步)。

⚠ 注: 该缺陷**不影响**自动判定作业 pwsh-2579 —— 它本来就用 Python 按列名读。
MSGEOF
git log --oneline -1
