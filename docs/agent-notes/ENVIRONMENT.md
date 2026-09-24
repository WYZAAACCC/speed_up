# 本机干活手册（WSL / MOOSE / conda / 目录）

> **实测日期 2026-09-20。每条都是在这台机器上跑出来的，不是抄的。**
>
> 配套：`HANDOFF_2026-09-20.md`（当前状态）、`AGENTS.md` §3–§4（坑与环境事实）。
> 本文件**取代** `wsl-moose-environment-setup.md` 里过时的部分（那份记的是 2026-09-16 的搭建过程）。
>
> ⚠ **接手后第一件事就是把本文 §二、§三 读一遍** —— 这两节里的坑会让算例
> **静默变慢几十倍而不报错**，或者让脚本**莫名其妙 abort**。

---

## 一、拓扑：Windows 与 WSL 怎么对应

| Windows | WSL | 说明 |
|---|---|---|
| `F:\speed_up` | `/mnt/f/speed_up` | **仓库本体**。项目文件都在这，Windows 侧可读 ⇒ **任何情况下都安全** |
| — | `/root/work` | **算例运行目录**（ext4）。实测 412 个目录 / 13 GB。临时产物都在这 |
| `F:\WSL\Ubuntu\ext4.vhdx` | `/` = `/dev/sdd`，1007 GB，已用 39 GB | WSL 磁盘（**已从 C 盘迁出**） |
| — | `/root/moose` | MOOSE 源码，版本 `b892bff54e`（2026-08-22） |
| — | `/root/miniconda3/envs/{moose,ml}` | 两个 conda 环境，用途不同（见 §三） |
| — | `/root/projects/gb_jac` | **自建 app 的构建目录**（生产用二进制在这） |
| `F:\WSL\swap.vhdx` | swap（8 GB） | 也在 F 盘 |

**⚠ 算例必须在 ext4（`/root/work`）上跑，不要在 `/mnt/f` 上跑。**
`/mnt/f` 是 **9p 协议**挂载，慢，而且**对正在被追加的文件会静默返回过期数据**（见 §五）。

---

## 二、从 Windows 侧怎么调 WSL

**Claude Code 的 Bash 工具跑的是 Git Bash（Windows 侧），不是 WSL。** 必须显式调：

```bash
# 单行命令
wsl.exe -d Ubuntu -- bash -lc 'uname -r'

# ⚠ 多行 / 带变量 / 带续行符的命令 —— 一律先写成 .sh 文件再执行
```

**为什么不能直接塞多行**：Git Bash → `wsl.exe` 这一层会把 `$变量`、`$()`、
反斜杠续行吞掉。**本手册写作时实测过一次**：一个带 `\` 续行的 `for` 循环，
循环变量被吃成空串，四个二进制全部报"缺"——而它们其实都在。
⇒ **判据：命令一旦超过一行，就走文件。**

**标准做法**：

```bash
# 1) 用 Write 工具（或 WSL 侧 python3）把脚本写到共享盘
# 2) 在 WSL 里转行尾后执行
wsl.exe -d Ubuntu -- bash -lc 'sed "s/\r$//" /mnt/f/speed_up/x.sh > /tmp/x.sh && bash /tmp/x.sh'
```

**`sed 's/\r$//'` 不能省** —— 见 §十。

**发行版名**：`wsl.exe --list --verbose`。默认是 **Ubuntu**（另有 `docker-desktop`，不用）。

---

## 三、conda：两个环境，用途不同

| 环境 | 用途 | 关键 |
|---|---|---|
| **`moose`** | **跑 MOOSE、建 app、编译** | 有 `mpicxx`；`LIBMESH_DIR` = `PETSC_DIR` = `/root/miniconda3/envs/moose` |
| **`ml`** | **跑生成器（Python + torch）** | `frozen/gen_aniso_nonad.py`、`splice_aniso_nonad.py` |

`run_nonad_prod.sh` 就是**先 `ml` 跑生成器、再切回 `moose` 跑 MOOSE**（第 151 / 440 行各切一次）。

### 所有 `validated/*.sh` 的标准前言

```bash
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
ROOT="${ROOT:-/root/work/xxx}"           # 算例跑在 ext4
SEED="${SEED:-/root/work/jitcache_seed}" # JIT 缓存种子
```
（38 个脚本里都是这几行，照抄即可。）

### 🔴 不激活 `moose` 会发生什么 —— **静默变慢，不报错**

**这是本手册最值钱的一条。** 实测（`gb_jac-opt` 跑一个带 `ParsedMaterial` 的 1D 小算例）：

| | 退出码 | 日志 | `.jitcache` |
|---|---|---|---|
| **不激活** | **0** ✅ | `JIT compile failed.` / `Failed to JIT compile expression, falling back to byte code interpretation.` | **不生成** |
| 激活 `moose` | 0 ✅ | 无 | 生成 |

**⇒ 退出码 0、数值也对，只是所有 parsed 表达式退回字节码解释执行 —— 慢几十倍。**
生产输入里有几条几千字符的巨型 parsed 表达式（`L` 2181 字符、`M` 279、`F_at` 136），
退化后代价是数量级的。

⇒ **每个算例跑完必须查一句**：
```bash
grep -c "JIT compile failed" run.log     # 必须是 0
```

> **⚠ 反直觉的地方，别被"能跑起来"骗了**：**不激活 conda，二进制本身照样能启动** ——
> `gb_jac-opt` 的 RPATH 直指 `/root/miniconda3/envs/moose/lib`，
> `ldd` 显示 `libmesh_opt.so.0`、`libpetsc.so.3.25` 都能解析。
> 所以**症状不会出现在启动时，只出现在 JIT 那一步**，中途才刷屏。

### JIT 缓存

MOOSE 把 JIT 产物放在**工作目录**的 `.jitcache/`。
项目预置了一个种子 `/root/work/jitcache_seed`（**539 项 / 4.4 MB**），
脚本用这一行**幂等**地铺进去：

```bash
[ -d "$SEED" ] && { mkdir -p .jitcache; cp -rn "$SEED"/. .jitcache/ 2>/dev/null || true; }
```

- ⚠ **`cp -r` 不加 `-n` 会在目标已存在时报 `File exists` 并 abort**
  （`set -e` 下整个脚本停）。**实测踩过。**
- 每个新目录第一次跑都要付 JIT 编译钱（**几分钟**），铺了种子就省掉。
  忘了铺的后果 = 每个 `A` 档多花 5 分钟。

---

## 四、MOOSE 二进制

| 路径 | 用途 | 实测 mtime |
|---|---|---|
| **`/root/projects/gb_jac/gb_jac-opt`** | **生产用**：原版全部对象 + 自建 `ACGrGrPolyJ` | 2026-09-19 20:00 |
| `/root/moose/modules/phase_field/phase_field-opt` | 原版，未改动（跑 `test_cg.i` 这类旧算例用） | 2026-09-16 01:21 |
| `/root/projects/gb_jac_dbg/` | 调试版（另建的 debug 构建） | — |
| ~~`/root/moose/modules/combined/combined-opt`~~ | **本机不存在**（别的 MOOSE 教程常引，这里没有） | — |

**⚠ 用错二进制**：拿原版 `phase_field-opt` 跑生产输入 ⇒
`'ACGrGrPolyJ' is not a registered object`。**看到这条先查二进制，别查输入。**

**重建 app**：`bash pipeline/app/build_app.sh`（源码在 `pipeline/app/`，app 名 `GbJac`）
⚠ 建之前**必须激活 conda**，否则报两条**与核代码毫无关系**的错：
```
/bin/sh: libmesh-config: not found
***ERROR*** WASP does not seem to be available.
```

---

## 五、`/mnt/f` 的 9p 缓存陷阱（**最隐蔽**）

```
F:\ on /mnt/f type 9p (rw,noatime,aname=drvfs;path=F:\;...,cache=0x5,msize=65536)
```

对同一个**正在被追加**的 CSV 连续读三次，实测：

```
第 1 次: 1757 行, 末 t=0.0351
第 2 次: 2680 行, 末 t=0.0535
第 3 次: 6185 行, 末 t=0.1236   ← 与 shell 的 wc -l 一致
```

**症状**：结果**时间倒退**、行数比 `wc -l` 少、或"跑很久没进展"。
**本项目因此误判过两次** —— 一次以为"结果发散了"，一次以为"平衡依赖 `M`"。**两次都是假的。**

**防**：读 CSV 一律走 **`pipeline/validated/robust_csv.py` 的 `read_rows()`**
（反复读到与 `wc -l` 一致为止，取行数最多的那次）。
**⚠ 只影响读。** MOOSE 写文件没问题，算例本身也没问题。交互式排查时 `tail`/`wc`/`awk` 走另一条路径，实测更可靠。

---

## 六、资源预算与「别占满机器」

| 项 | 值 |
|---|---|
| 逻辑核 | **20**（i7-14700HX，12 物理核 / 20 线程） |
| WSL 内存 | `.wslconfig` 限 **24 GB**；实测 `free -g` 给 **23 GB**（可用 22） |
| **规划内存用 22 GB，不是 32 GB** | |
| 磁盘 | `/` 已用 39 GB / 1007 GB；`/mnt/f` 剩 **714 GB** |
| GPU | **与本工作无关** —— MOOSE 主求解走 CPU，PETSc/ASM **不自动用 GPU**。别指望显卡加速 |

- **长任务后台跑** —— 机器是共享的，用户会同时跑别的东西。
- **别在这个 WSL 里同时起两个以上重作业。** 本机 WSL 只有 23 GB，
  MOOSE 单进程 0.3~3 GB，JIT 还会并行起多个 `mpicxx`/`cc1plus`。
  **历史上 WSL 整机卡死（`ps` 都数不出进程）就发生在「同时两个 MOOSE + 一个 gdb」的时候。**
- **编译并行度用 `-j 8`** —— MOOSE 用 unity build，单个编译单元 2–4 GB，
  `-j 12` 会 OOM 把 WSL 整个搞崩。
- 生产全尺寸成本（实测）：**峰值 3.45 GB / 245 s·步⁻¹**，单条轨迹 **12–22 小时**。

---

## 七、网络与代理

- `.wslconfig` 里 **`networkingMode=mirrored`** ⇒ **WSL 里直接用 `127.0.0.1:7897`**。
- `wsl_proxy.sh`（仓库根目录）动态探测主机 IP，是给 **NAT 模式**兜底的：
  ```bash
  wsl.exe -d Ubuntu -- bash -lc 'source /mnt/f/speed_up/wsl_proxy.sh'
  ```
- 代理工具是 **Watt Toolkit（Steam++）**，端口 7897。它会对 github.com 做 **TLS 中间人**，
  用自签根证书。**证书已装进 WSL**（`/usr/local/share/ca-certificates/` + `update-ca-certificates`）。
  **不要去关 git 的 `sslVerify`** —— 那是把问题藏起来，不是解决。
- **文献检索的通道限制**（实测，见 `HANDOFF_2026-09-20.md` §4.6）：
  `WebFetch` **对所有域名**被拦；WSL `curl` 能下 **springer / nature / iop / arxiv / 机构仓库**，
  但 **mdpi(403) / sciencedirect / tandfonline(403) / osti(超时)** 不通。
- ⚠ `~/.codex/config.toml` 里 **`web_search = "disabled"`**，本项目有大量文献检索工作，需要时显式开启。
- ⚠ `~/.codex/config.toml` 的 `[projects.'...']` 信任列表里**可能没有 `f:\speed_up`**，
  用 Codex 在本仓库工作前先加进去。

---

## 八、WSL 卡死怎么判断、怎么救

**判据**：`ps -e --no-headers | wc -l` 返回 **0**（`/proc` 都读不到）
⇒ 内核/虚拟化层卡死，**不是路径问题**。

⚠ 最容易误判的地方：报错是「某个路径读失败」，看着像权限/路径写错。
实际是**部分失败** —— 同一时刻 `/`、`/root/moose`、`/usr/bin` 能读，`/root/work`、`/usr`、`/mnt/f` 读不了。
**「父目录 `/usr` 失败而子目录 `/usr/bin` 成功」这种模式，就已经排除了路径问题。**

**恢复次序**（⚠ `--shutdown` 有时不够）：

```powershell
wsl.exe --terminate Ubuntu     # ← 关键这步：强制杀掉发行版实例
Start-Sleep 5
wsl.exe --shutdown
Start-Sleep 10
wsl.exe -e bash -lc 'echo ALIVE; ps -e --no-headers | wc -l'
```

**2026-09-20 实测**：`--shutdown` 后每条命令几秒内又卡死（连 `pgrep`、`free` 都卡），
而 `wsl --list --verbose` 显示 **Running** —— **VM 起来了，但 guest 的 init/shell 无响应。**
补上 `--terminate` 后立刻恢复（46 个进程、`up 0 min`）。
⇒ **判据：不是看 VM 在不在，是看 guest 里 `ps` 能不能数出进程。**

**抢数据**：**别 `cp`/`mv`（目录操作会失败），直接 `cat` 具体文件** ——
实测"目录列举失败"时**具体文件仍可读**。抢到的东西**立刻写到 `/mnt/f`**，别留在 WSL 里。
**项目文件全程在 `/mnt/f`，Windows 侧可读 ⇒ 任何情况下都安全。** 抢救只针对 WSL 内的算例产物。

**`sync` 没有用**（实测无效），只能重启。

---

## 九、杀进程

```bash
# ✅ 正确：精确进程名 + 按 PID
for P in $(pgrep -x gb_jac-opt); do kill -9 "$P"; done

# ❌ 危险：pkill -f 匹配**完整命令行**，而你自己那条
#    wsl -e bash -lc '... gb_jac-opt -i ...' 里就含这个字符串 ⇒ shell 自杀（退出码 9）
pkill -f "gb_jac-opt -i"
```

**停后台任务 ≠ 停子进程。** 停掉的只是那层 shell，MOOSE 会继续跑（偷 CPU、cwd 变 `(deleted)`）。
**僵尸判据**：`readlink /proc/<pid>/cwd` 里带 `(deleted)`。

```bash
for P in $(pgrep -x gb_jac-opt); do
  CWD=$(readlink /proc/$P/cwd 2>/dev/null)
  case "$CWD" in *"(deleted)"*) kill -9 "$P";; esac
done
```
⇒ **每次停掉一个跑 MOOSE 的后台任务，都要显式查一遍残留。**

---

## 十、写文件的行尾

| 在哪写 | 结果 |
|---|---|
| **WSL 的 python3** / Claude 的 Write 工具 | LF ✓ |
| **Windows 的 python3（Git Bash 里调）** | **CRLF** ✗ |

**后果**：`.sh` 首行变 `#!/bin/bash^M` ⇒ `set -eo pipefail` 被解析成 `pipefail\r`
⇒ bash 报 **`set: pipefail: invalid option name`** —— **报错信息完全不提行尾**，
看着像脚本逻辑坏了。**本项目在这个坑上栽过两次。**

**诊断法**：
```bash
head -1 script.sh | cat -A     # 看到 ^M$ 就是 CRLF
file script.sh                  # 会直接写 "with CRLF line terminators"
```

**⇒ 改 `.i` / `.sh` 的 Python 一律在 WSL 里跑**（`wsl.exe -d Ubuntu -- bash -lc 'python3 ...'`），
别在 Git Bash 里调 Windows 的 python3。

**附带两条 Windows 侧 python3 的坑**：
- **没有 numpy**（`ModuleNotFoundError`）⇒ 分析脚本用纯标准库（如 `validated/gb_width_vs_s.py`），或走 WSL。
- **输出中文报 GBK 错**（`UnicodeEncodeError: 'gbk' codec`）⇒ 加 `PYTHONIOENCODING=utf-8`。

---

## 十一、一页速查

```bash
# 探活
wsl.exe -d Ubuntu -- bash -lc 'echo ALIVE; nproc; free -g | head -2'

# 跑一个 validated 脚本（脚本自己会 cd 到 /root/work）
wsl.exe -d Ubuntu -- bash -lc 'sed "s/\r$//" /mnt/f/speed_up/pipeline/validated/run_xxx.sh > /tmp/r.sh && bash /tmp/r.sh'

# 跑完必须查 JIT
wsl.exe -d Ubuntu -- bash -lc 'grep -c "JIT compile failed" /root/work/xxx/run.log'

# 查残留僵尸
wsl.exe -d Ubuntu -- bash -lc 'for P in $(pgrep -x gb_jac-opt); do echo "$P $(readlink /proc/$P/cwd)"; done'

# 清理
wsl.exe -d Ubuntu -- bash -lc 'du -sh /root/work/* | sort -rh | head -20'
```
