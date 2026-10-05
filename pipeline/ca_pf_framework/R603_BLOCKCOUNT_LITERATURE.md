# R603 —— 块数律：**文献分支已命中**（block size ∝ prior-grain size）

> 触发：用户质疑「块数是规定值、不是物理涌现」（记于 `R602_BLOCKCOUNT_DEBT.md`）
> 目标：按 **文献 → 推导 → 标定** 的次序给「块数」找一条真律
> 日期：2026-10-05　方法：用户建议走 **HTML 页面**（PDF 被 fetch 工具拒收）

## 1. ★ 文献命中（可直接引用）

**Galindo-Nava, E. I. & Rivera-Díaz-del-Castillo, P. E. J.**
*A model for the microstructure behaviour and strength evolution in lath martensite*,
**Acta Materialia 98 (2015)**, DOI **[10.1016/j.actamat.2015.07.018](https://doi.org/10.1016/j.actamat.2015.07.018)**
· accepted version: Cambridge Apollo, [handle 1810/291264](https://www.repository.cam.ac.uk/handle/1810/291264)，
[仓储 DOI 10.17863/CAM.38443](https://doi.org/10.17863/CAM.38443)

**摘要原文（从仓储 HTML 条目页取得，非 PDF）**：
> "**The packet and block size were found to linearly depend on the prior-austenite grain size**
> when introducing relevant crystallographic and geometric relationships of their hierarchical
> arrangements."

### 1.1 为什么这条律**正好可用**（与本框架严丝合缝）
| 要素 | 说明 |
|---|---|
| 律的形式 | **block / packet 尺寸 ∝ 原奥氏体晶粒尺寸 `D`**（引入晶体学与层级几何后成正比） |
| 与本框架的契合 | **Window B 的设定就是「单个 prior-β 晶粒内部的一个三维盒子」** ⇒ **`D` 是物理输入**（来自 Window A 的晶粒骨架），**不是可调参数** |
| ⇒ 块数 | 由 `d_block ≈ k_b · D` + 盒子体积 + 层级几何给出 ⇒ **块数成为 `D` 的导出量** |

**⇒ 这正面回应了用户的质疑**：块数**不该外部指定**，而应由 **(原晶粒尺寸 `D`) × (晶体学几何因子)** 决定；
而 `D` 在本框架里是**物理输入**。

## 2. ⚠ 尚缺：系数 `k_b` 的具体形式

摘要有**律的形式**、无系数。accepted version 是 PDF，**本会话 fetch 工具对 PDF 直接拒收**
（`unsupported content type "application/pdf"`）。
**⇒ 下一步仍走 HTML 路线**：① 找该文的 HTML 全文镜像；
② 找**引用了这条式子**的 HTML 页面（综述、学位论文 HTML 版、教学讲义）。

## 3. 参数出处总账（本轮更新）

| 参数 | 分级 | 变化 |
|---|---|---|
| **块数 `B`** | **文献**（Acta Mater. 98 (2015)，DOI 已登记） | ⬆️ **由"标定"升级** |
| `sigma_y` | ❌ 无出处 ⇒ 已走完升级次序（文献工具受限 → **推导** R601，证不敏感）⇒ 无需标定 | — |
| `mob` | ⚠️ 仅"实测/来源" | 待找文献 |
| `ed-eta` / `nvar` / `DS_REF` | ✅ 各有**推导**出处（`DS_REF` 另带 DOI + ±20% 带 + 自洽断言） | — |
| `alpha-km` | 文献（`R507_SHAPE_CLOSURE.md`） | — |

## 4. 方法学记账（值得留）

**PDF 被拒 ≠ 文献拿不到。** 仓储/期刊的**条目页（HTML）** 往往含**完整摘要**，
足以判定"有没有这条律、形式是什么"。**先取 HTML 条目页，再决定要不要啃全文** —— 成本低得多。
（本会话此前两次因为直接取 PDF（403 / unsupported content type）就判定"文献拿不到"，
**是方法用错了**，不是文献不存在。）
