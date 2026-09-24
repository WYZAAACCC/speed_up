# ExaCA 基准算例镜像（2026-09-24）

## 目的
用**别人的开源 CA（ExaCA，LLNL）的公开算例**做"同初始条件"对比。

## 已取到的（本目录）
| 文件 | 内容 |
|---|---|
| `exaca/Inp_TwoGrainDirSolidification.json` | ExaCA 双晶定向凝固算例（**完整初始条件**） |
| `exaca/Inp_DirSolidification.json` | 单晶定向凝固 + 体形核（密度 10） |
| `exaca/Inp_EquiaxedGrain.json` | 等轴单晶（49³, G=R=0） |
| `exaca/Inp_SingleLine.json` | 单道（需 ExaCA-Data 的温度场文件） |
| `exaca/Inconel625.json` | **ExaCA 自己的界面响应函数**：`V(dT)=−1.0302e-7 dT³+1.0533e-4 dT²+2.2196e-3 dT` m/s，`freezing_range=210 K` |
| `exaca/GrainOrientationVectors.csv` | 基底取向表（10001 条单位向量） |
| `P25.npy` / `P99.npy` | 该算例两个种子的晶体轴（GrainID 25 / 9936，已由 CSV 重建） |

算例原文（`Inp_TwoGrainDirSolidification.json`）：
`CellSize=1 µm, 200³, G=5e5 K/m, R=3e5 µm/s(=0.3 m/s), InitUndercooling=10 K,`
`Nucleation.Density=0, Substrate 两种子 (x=100,y=50) 与 (x=100,y=150), GrainIDs 25 与 9936`。

## 关键限制（为什么不能做"逐胞对比"）
1. **ExaCA 的 Material 列表里没有 Ti64** ✗（只有 In625/SS316/AlSi10Mg/SS316L）⇒ "Ti64 的 ExaCA 数据"不存在。
2. **拿不到 ExaCA 的输出** ✗：本机 `github.com`/`codeload`/`raw` 全被墙，只有 `api.github.com` 通，
   而 API 对 >1 MB 文件不返回内容 ⇒ 无法下载它 example 的 VTK 输出（ExaCA-Data 仓另存）。
3. **算力**：原算例 dx=1 µm、200³ 需要 ~10⁵ 步；纯 Python 跑不动 ⇒ 本镜像把 dx 放大到 **4 µm**
   （同物理尺寸 200 µm、50³、~2900 步、19 s）。**这是记账过的近似**：几何/取向/无量纲驱动相同，分辨率不同。

## 本机镜像的做法与结果（`_exaca_mirror.py`）
- 用 ExaCA 的 **In625 三次律** + `freezing_range=210 K` 作界面响应（照抄其材料文件）；
- 用其**真实取向**（GrainID 25 / 9936）；
- 用其 G、R、ΔT0、种子间距（100 µm）与物理尺寸；
- 解析预测（先写）：沿 +z 的径向速率 ∝ 1/Σ_a|p_a·ẑ| ⇒ 25: 0.709、**9936: 0.882 ⇒ 9936 更快**。

实测（`mirror_result.json`）：
| 模式 | GrainID25 | GrainID9936 | 预测方向 |
|---|---|---|---|
| `envelope` | 59258 胞 | **65742 胞** | **PASS** |
| `decentered` | 59258 胞 | **65742 胞** | **PASS** |

- 会合面在 y 中线上下来回摆动（24.5 → 37.5 → 34.5 胞），**朝更快的晶粒一侧弯曲** ✓ 物理预期的竞争形态。
- ⚠ **两种捕获模式结果逐位相同** ⇒ 该算例（与熔池算例一样）由**热约束归属**主导
  （`T<T_SOL` 的胞一律按包络 argmax 落定），**没有隔离出生长动理学** ⇒ 这条对比**不能**用来判生长律。
- ⚠ 我的"会合面 vs 解析 locus"在原脚本里用的是 `sup_A = sup_B`，**该式只在均匀驱动下成立**
  （T4 已证 0.25 胞）；本算例有梯度 ⇒ 那个 11 胞的"偏差"是**对比式用错**，不是 CA 错。已有记录。

## 要做"真·文献数据对比"，需要下面任一项
1. **ExaCA 的输出**：任何能跑 ExaCA 的人执行 `exaca Inp_TwoGrainDirSolidification.json`（4 行命令），
   把输出的 `GrainID` VTK/npy 给我 ⇒ 可做统计级对比（晶粒数、宽度分布、织构、GB 取向差分布）；
2. **一篇 Ti64 CA/PF 论文的完整输入参数 + 报告值**（本项目检索任务书 §214 正是这一项，仍未闭）；
3. **实验 EBSD**（开放数据集或你自己的）⇒ 唯一真正的物理验证目标。

## 复跑
```bash
cd /mnt/f/speed_up
/root/miniconda3/envs/ml/bin/python _exaca_mirror.py     # ~2 min（两种模式）
cat bench/exaca/mirror_result.json
```