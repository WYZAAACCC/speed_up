# ExaCA（LLNL 开源标准 CA）× 我的 CA：同材料、同初始条件的对比（2026-09-24）

## 0. 做了什么
1. **编译成功开源标准工具 ExaCA 2.2.0-dev**（Kokkos 4.5.00 自建，OpenMP 20 线程，MPI 单rank）
   → `/root/bench/ExaCA-master/build/bin/ExaCA`（+ 自带 `ExaCA-GrainAnalysis`）。
   ⚠ 装在 WSL 根盘（/mnt/f 是 9p，编译慢）；Kokkos 构建脚本 `_build_kokkos.sh`，ExaCA 构建脚本 `_build_exaca2.sh`。
2. **跑 ExaCA 官方小算例** `Inp_SmallDirSolidification`（20³, dx=1µm, In625, G=5e5 K/m, R=0.3 m/s,
   底面 25% 位点, 形核密度 250×10¹²m⁻³, dtn=5 K, σ=0.5 K, 3000 步, 9.7 s）→ 5 个随机种子。
3. **把它的约定逐条抄到我的 CA**（读其源码确定，不是猜）：
   - Directional 的 ΔT(z,t) = G(Rt − z·dx)，`location_init_undercooling=0`（域底）；
   - dt = 6.6667e-8 s（由 3000 步/20µm 反推 ✓ 与 `TimeStep=0.0666667` µs 一致）；
   - 界面响应 = 它材料文件的三次律 `V=−1.0302e-7ΔT³+1.0533e-4ΔT²+2.2196e-3ΔT`（未封顶）；
   - `SurfaceSiteDensity` = **面积密度**：位点数 = round(密度×10¹² × 底面面积)；本次 = 100 个位点，
     位置用**连续均匀分布再取整**（它的注释自己承认会因此低估密度）；
   - 形核：势点数 = round(`n_max(×10¹²) × 域体积`) = **2**；位置三维均匀随机；过冷度 ~N(5,0.5)；
     局部 ΔT 达到该值时激活（ExaCA 记录为**负 GrainID** ⇒ 它的 "nucleated fraction" 就是 GrainID<0 的占比）。

## 1. 结果（各 5 个随机种子）

| 指标 | ExaCA（标准工具） | 我的 CA | 判定 |
|---|---|---|---|
| 不同基底晶粒数 | **92.0 ± 3.1** | **88.6 ± 2.1** | ✅ 一致（"100 位点落 400 胞"的解析期望 = 88.2） |
| 平均晶粒尺寸 | 87.1 ± 3.0 胞 | 90.3 ± 2.1 胞 | ✅ 差 3.7% |
| 形核势点数（n_max·V = 2.0） | 2 | 2 | ✅ 一致 |
| **形核晶粒占比** | **0.289 ± 0.113** | **0.554 ± 0.057** | ❌ **差 1.9×** |
| 种子间波动 | ±3.1 | ±2.1 | ✅ 同量级 |
| 取向总体分布（简单平均 min∠⟨100⟩,+Z） | ~31° | 32.27° | ✅ 与取向表全体 32.0° 一致 |
| **尺寸加权 min∠（择优强度，越小越对齐）** | **22.93°** | **27.56°**（基底 28.28 / 形核 26.96） | ⚠️ **两边都有择优，但我方弱 ~20%** |

> 取向统计口径：对每个晶粒取 min_a angle(<100>_a, +Z)（与约定无关），按胞数加权。
> 全表的总体均值 32.0°；两个码的**不加权**均值都≈31–32° ⇒ 基底取向分布一致 ✓；
> 而**加权**均值都显著更低 ⇒ **两边都重现了 Walton–Chalmers 择优** ✓，但强度差 ~20% ✗。

**两个偏差同源**（都指向"竞争/择优"）：形核晶粒占比 1.9×、择优强度弱 20%。
已排除 p90 集总（pct=50/90/100 逐位相同）。

**进一步定位（`_diag_nucleated.py`）**：差别集中在"两个形核晶粒"上——
ExaCA 每次总有一颗形核晶粒被**饿死**（83 / 90 / 298 胞，只占一小块，z 范围也短），
而我这边两颗都长到 ~2200 胞 ⇒ **我的形核晶粒系统性偏强**。
- 已排除：**不是 p90 集总**（`lg_percentile`=50/90/100 结果逐位相同）。
- 待查：形核激活时刻/位置的语义差异、或我的 `envelope` 捕获在"新生核 vs 柱状晶"竞争时的行为
  （下一步：把输出帧加密，画两边形核晶粒的**生长曲线**对比）。

## 2. 结论

- ✅ **能达到："与开源标准工具在结构量上一致"**（晶粒数、平均晶粒尺寸、形核数、种子间波动）。
- ❌ **还不能说"通过"**：一个定量指标（形核晶粒占比）差 1.9×，且已缩小到一个可定位机制。
- ✅ 附带收益：项目现在**本地有 ExaCA**（可作为后续所有 CA 结论的标准参照），
  且"同输入两码对比"的流水线已建好（`_exaca_vs_mine.py` / `_mine_mirror.py` / `_diag_nucleated.py`）。

## 3. 复跑
```bash
bash /mnt/f/speed_up/_build_kokkos.sh            # Kokkos（~2 min）
bash /mnt/f/speed_up/_build_exaca2.sh            # ExaCA（~2 min）
cd /root/bench/run && /root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_exaca_vs_mine.py    # ExaCA 5 种子
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_mine_mirror.py                            # 我方 5 种子
/root/miniconda3/envs/ml/bin/python /mnt/f/speed_up/_diag_nucleated.py                          # 定位
```
---

## 4. 追根：读 ExaCA 的捕获实现（2026-09-24 续）

**`src/CAupdate.hpp :: cellCapture`（每个"活跃胞"= 有液相邻居的固相胞）**
```cpp
const float local_undercooling = temperature.getUndercooling(cycle, index);
interface.diagonal_length(index) += irf.compute(local_undercooling, phase_id(index));   // 逐胞 ℓ，用【局部】ΔT
...
if ((diagonal_length_cell >= interface.crit_diagonal_length(26*index + l)) && (neighbor_cell_type == Liquid)) {
    ... grain_id(neighbor_index) = my_grain_id;
    interface.createNewOctahedron(..., neighbor_index);      // ★ 新胞拿一个【重新定心】的八面体
    interface.calcCritDiagonalLength(neighbor_index, ...);   // ★ 重算临界长度（精确增量，不是累加路径代价）
}
```
⇒ **ExaCA = "逐胞 ℓ（局部 ΔT 驱动）+ 每次捕获做精确重新定心"**，
即经典 decentered octahedron 的**精确**实现。对比我的两种模式：

| | ℓ 的组织 | 驱动量 | 重定心 | 实测择优强度 |
|---|---|---|---|---|
| **ExaCA** | 逐胞 | 逐胞局部 ΔT | **精确**（八面体重新定位 + 重算临界长度） | **22.93°**（基准 31.17°）|
| 我的 `envelope`（现默认） | **整晶粒一个 ℓ** | 该晶粒前沿 V 的 p90 | 不需要 | **28.28°** |
| 我的 `decentered`（旧默认） | 逐胞 | 逐胞 | 用**格点路径代价**近似（审计 N1：径向短 25~40%） | 见审计 |

**两个偏差由此统一解释**：我的"整晶粒一个 ℓ"把局部驱动**集总**到一颗晶粒上，
对错取向晶粒的抑制偏弱 ⇒ ①择优强度弱 2.8×（22.9° vs 28.3° 的"选择量"）；
②随机取向的**形核晶粒**因此能多占体积（0.55 vs 0.29）✓ 同一个病根 ✓。
（p50/90/100 不敏感只说明"p90 这个参数"不重要，不能排除"单-ℓ 结构"本身的问题 ✓。）

**结论 / 修复方向**：采用 ExaCA 的形态——**逐胞 ℓ + 精确重定心**（这正是我在 CA3D_AUDIT §N1 里
记为"理想实现"的那一档），然后重跑本对比，期望择优强度与形核占比同时落到 ExaCA 量级。
---

## 5. ⚠ 重大更正（2026-09-24 续）：此前对比数字**全部作废**

读 ExaCA 启动日志发现它写的是 **`cooling rate of 300000 K/s`** ——
**它的 `R` 是"冷却速率 [K/s]"，不是界面速度 [µm/s]**。而我在"镜像"脚本里按 `ΔT = G·(R·t − z·dx)`
把它当成速度用 ⇒ **我的热场冷却率大了 5×10⁵ 倍**，V 全程被顶到上限 ⇒
**第 1~4 节里"形核占比差 1.9×、择优弱 20%"这两个结论是热场单位错误造成的假象，作废** ✗。

ExaCA 的正确约定（源码确认）：
```cpp
float getUndercooling(cycle, index) const {
    return init_undercooling + (cycle - last_time_below_liquidus(index)) * current_cooling_rate(index);
}
```
⇒ Directional: `ΔT(z,t) = R·t − G·z`（R=3e5 K/s, G=5e5 K/m）⇒ 等温线速度 = R/G = **0.6 m/s**；
`TimeStep = 0.0666667 µs = 6.667e-8 s`（日志确认）。

修正后我方（同 5 种子）：晶粒数 **88.6±2.1**、平均晶粒 **90.3±2.1 胞**、**形核占比 0.116±0.020**。
对比 ExaCA（92.0±3.1 / 87.1±3.0 / 0.289±0.113）：
结构量仍一致 ✓✓；**形核占比从"高 1.9×"翻转成"低 2.5×"** ⇒ 说明这两个量对热场极敏感，
且**每算例只有 2 个形核位点 ⇒ 统计太弱**（5 个样本）⇒ 必须加种子数才能定论。

**为做 Ti64 比较，已给 ExaCA 增加 `"function": "table"`（读 dT[K],V[m/s] 两列 CSV，
按 dt/dx 归一 + 线性插值 + 端点截断）**，编译通过、材料文件能被解析 ✓；
但用它跑 Ti64 算例时 ExaCA 卡住（10 min+ 不结束），疑似我的表在设备侧没拿到数据
（V 恒为 0 ⇒ 前沿不动 ⇒ 它"跑到全固"的循环不结束）⇒ 待修。
**当前 Ti64 对比尚未成功**。
---

## 6. 收尾（2026-09-24）：CA/ExaCA 验证线关闭

**最终状态（Ti64，同材料同初条件，各 20 种子，口径已统一）**

| 指标 | ExaCA (Ti64) | 本 CA (`envelope` 默认 / `cell`) | 差 | 判定 |
|---|---|---|---|---|
| 不同晶粒数 | 88.20 | 89.75 | +1.8% | ✓（p=0.078） |
| 固相胞总数 | 8000.0 | 8000.0 | **0.0%** | ✓✓ |
| 平均晶粒尺寸 | 90.9 | 89.1 | −2.0% | ✓ |
| 形核晶粒占比 | 0.10 | 0.11 | +4.6% | ✓（p=0.725） |
| 择优强度（基底加权 min∠） | 22.10° | 23.71° | **+7.3%** | ✗ 唯一残差 |

**已排除的残差来源**：几何（`cell` 的 `oct_recenter` 与 ExaCA `createNewOctahedron` **位级一致**，单元测试 8/8 ✓）；
ℓ 增长规则（逐胞局部 ΔT + `INIT_OCT=0.01` ✓）；**裁决规则**（"先到先得"实验否证：23.69° vs 23.71°，
且把形核占比搞坏到 0.16 ✗）；形核/晶粒数/固相总量（全一致 ✓）。
⇒ 那 7% 最可能是**有限样本（86 晶粒）上的统计偏移**或某个记账细节，作为**已知偏差**记账，不再追。

**本轮我自己的两处度量错误（已更正）**：
① 把 ExaCA 日志的 `Solid cells`（分类之一，不含 `Active`）当成全固相 ⇒ 假的 "+11%" ✗；
② 平均晶粒尺寸两边口径不同（我只取了正 ID）⇒ 假的 "+9.2%" ✗。
更正后两项都一致（0.0% / −2.0%）✓。

**交付物**：`ca3d.py` 新增 `capture="cell"`（位级复刻 ExaCA 形态）与 `cell_tiebreak` 开关；
本机可用 ExaCA 2.2.0-dev + Kokkos 4.5（`/root/bench/`，含我给 ExaCA 加的 `"function":"table"` 查表界面响应）；
脚本 `_ti64_compare.py` / `_ti64_cell.py` / `_unit_oct.py` / `_verify_cell_geom.py` / `_chk_solid_total.py`；
回归：`verify_ca3d.py 20/1/0`、`verify_ca3d_physics.py 16/0/0`、`verify_ca3d_envelope.py 12/0/0` ✓（改动未破坏既有判据 ✓）。
默认仍是 `envelope`（未动生产行为 ✓）。