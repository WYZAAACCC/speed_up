#!/bin/bash
# _t5_git_s232.sh --- ★★★★★ 记账：SIGHUP 伪装成"修复导致崩溃"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_relaunch_mob2.sh pipeline/ca_pf_framework/_t5_amslow.sh \
        pipeline/ca_pf_framework/_t5_amkill.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s232 ★★★★★ 记账: SIGHUP 伪装成"修复导致崩溃"（真根因是我的重启脚本）

## 现象（一度误判）
修好 ellipse 的 BUG 后重启两臂 => 4 分钟后"进程存活 + 已过 step 1 形核 + Traceback=0" =>
判定"修复生效"。**但 12 分钟后再看：两臂**日志停在 18:17**、末步仍 0、**进程消失、
且日志里**既无 traceback 也无退出摘要**（`exit=` 次数 = 0、无 `====` 块）。**
=> 我一度怀疑"修复引入了静默崩溃"。

## 真根因（**是我的脚本，不是修复**）
`_t5_relaunch_mob.sh` 用 `&` 起了两臂，**然后脚本自己退出** =>
**子进程收到 SIGHUP ⇒ 静默死掉**（所以无 traceback、无退出摘要 —— 那两样都要活着的启动器才会打印）。
**对照**：`_t5_ab_mob.sh` 结尾有 `wait` => **它一直活着** => 它的子进程安然无恙。

## 判据（**下次一眼可辨**）
* **日志有退出摘要块（`exit=` / `====`）** => 启动器**活着跑完** => 是引擎自己退出（真崩溃/正常结束）；
* **日志无摘要且进程没了** => **启动器被打断** => 先怀疑**信号/父 shell**，**别怀疑被改的代码**。

## 修法
`setsid <cmd> < /dev/null >> log 2>&1 &`（**脱离本 shell 的会话**）+ **脚本自己 `wait`**（双保险）。
实测：重启后 t5AM 进程数 = 3 ✓

## 纪律（第 31 条）
**"改完代码就崩"的第一嫌疑人不该是新代码** —— 先问：**这次启动方式与上次有什么不同？**
（本次：上次有 `wait`、这次没有 ⇒ 差异在**启动方式**，不在代码。）
**⇒ 这正是"工具错了和被测量对象错了长得一模一样"（P6）的又一实例。**
MSGEOF
git log --oneline -1
