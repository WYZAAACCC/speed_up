#!/bin/bash
# _t5_autojudge_start.sh --- 启动自动判定作业（**不用管道**，全部重定向到文件）
#
# ## 为什么要这个包装（**我犯的错，留痕**）
# 上一次我用 `bash _t5_auto_judge.sh 2>&1 | head -6` 启动 ——
# **`head -6` 读满 6 行就退出 ⇒ stdout 管道关闭 ⇒ 脚本之后每次 `echo` 触发 SIGPIPE**
# ⇒ **整个持久交接机制有静默失效的风险**（作业显示 running，但管道对侧已关）。
# **⇒ 修法：不用管道；把 stdout/stderr **全部重定向到 F 盘的文件**（`>>` 不会因读端退出而破）。**
# **⇒ 判据**：脚本必须能连写 >100 行而不死（下方 `nohup` + `>>` 保证）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_t5_auto_judge.log
{
  echo "[$(date '+%F %T')] ════════ 启动器：无管道重启（修 head -6 的 SIGPIPE 风险）════════"
  echo "[$(date '+%F %T')] 语法检查："
  bash -n _t5_auto_judge.sh && echo '  ✅ _t5_auto_judge.sh 语法 OK'
  echo "[$(date '+%F %T')] ▶ 开始运行自动判定（stdout/stderr 全部本文件）"
} >> "$LOG" 2>&1

# ★ 关键：**不用管道**，直接重定向到日志；nohup 保证不随父 shell 退出而死
nohup bash _t5_auto_judge.sh >> "$LOG" 2>&1 &
NP=$!
echo "[$(date '+%F %T')] 自动判定 pid=$NP ⇒ 已后台运行（无管道）" >> "$LOG"
echo "  ✅ 已启动  pid=$NP  ⇒ 日志 $LOG"
sleep 5
echo
echo '── 5 秒后确认它还活着 ──'
if kill -0 "$NP" 2>/dev/null; then echo "  ✅ pid=$NP 存活"; else echo "  ⚠ pid=$NP 已退出（查日志）"; fi
tail -4 "$LOG" | sed 's/^/  /'
