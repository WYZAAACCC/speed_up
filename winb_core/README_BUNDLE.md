# Window B 最小可运行主仿真集

由 `pipeline/ca_pf_framework/_r746_make_bundle.py` 导出。
**源目录未被修改**（只读）；每个文件的 SHA256 见 `MANIFEST.sha256`。

## 内容（20 个 .py + 3 个 C 扩展件）

| 文件 | 字节 | sha256[:12] |
|---|---:|---|
| `T16_verify_rve.py` | 16090 | `e8355af2105c` |
| `_band_health.py` | 8060 | `97ef978923ec` |
| `_bk_exp.py` | 350084 | `0d057c0edbf2` |
| `_bk_measure.py` | 74344 | `07aef6564819` |
| `_r581_ufv.c` | 13196 | `c44b3731bc70` |
| `_r581_ufv.so` | 20872 | `66260bef0112` |
| `_r581_ufvc_build.txt` | 1485 | `3e3200fbc3e0` |
| `_r68_facet_op.py` | 7155 | `b53383901de6` |
| `_t5_therm.py` | 18530 | `181690e69542` |
| `windowB_acct.py` | 12399 | `d81c2a54bf5d` |
| `windowB_aniso_elastic.py` | 8386 | `455fb561554c` |
| `windowB_bench3d.py` | 14542 | `67a9c63c2d81` |
| `windowB_closure.py` | 64670 | `c76a2ceed598` |
| `windowB_drag.py` | 2774 | `7d975f4d55f9` |
| `windowB_film.py` | 12168 | `f927a869a17f` |
| `windowB_km.py` | 19156 | `d56538b85042` |
| `windowB_lath.py` | 28873 | `5f7228decde7` |
| `windowB_par.py` | 25142 | `78eed934a8b9` |
| `windowB_pf.py` | 9760 | `3bafad94da55` |
| `windowB_pf3d.py` | 57058 | `7ce0ddf1d89a` |
| `windowB_surface.py` | 444152 | `d416ea60e4da` |
| `windowB_ti64_variants.py` | 8949 | `a801490dbdc3` |
| `windowB_wulff.py` | 6403 | `c2814c61eb13` |

## 怎么跑

```bash
PY=/root/miniconda3/envs/ml/bin/python
cd /mnt/f/speed_up/winb_core
$PY _smoke.py                       # 先证明能跑通（已验证 ✅）
$PY -u _bk_exp.py --help            # 全部参数
```

**`_smoke.py` 的实测结果**（本包导出后跑过）：
```
rc = 0 ;  series.csv 存在 True ;  meta.json 存在 True ;  可疑串（无）
⇒ ✅ 包可完整运行
```

## 依赖

* Python 3.12 + numpy（本机用 `/root/miniconda3/envs/ml/bin/python`）
* **无外部数据文件依赖**（已实测：唯一的读依赖是同一目录内的 `WINDOWB_VARIANTS.txt`，
  而那两行在 `windowB_ti64_variants.py:172-173` 的 `main()` 内、`import` 时不执行）
* ⚠ **`_r581_ufv.so` 不入 git**（`.gitignore:7` 的 `*.so`；源目录那份也没入库）
  ⇒ **clone 之后拿到的是 `.c` 而不是 `.so`**。
  `windowB_surface.py:116` 是 `import _r581_ufv as _C`（在 try 里，失败抛出）
  ⇒ **要么按 `_r581_ufvc_build.txt` 重建 `.so`，要么确认该路不需要**。
  重建入口：源目录的 `bash _r581_buildc.sh`（**不在本包内**）。

## 完整性

* 23 个文件与源目录 **逐位一致**（`MANIFEST.sha256` 23/23 自洽，已独立复核）
* 源目录**零改动**（`git status` 干净；`R629 E1`）

## 这个包**不包括**什么

| 不在包内 | 在哪 |
|---|---|
| `_exp/` 全部运行归档 | `pipeline/ca_pf_framework/_exp/` |
| 问题台账 / 规范 / 报告（303 个 `.md`） | `pipeline/ca_pf_framework/*.md` |
| 审计与验证脚本（`_audit*.py` / `_chk*.py` / `T*_verify*.py`…） | 同上目录 |
| 一次性探针（`_probe_*` / `_diag_*` / `_patch_*` / `_fix_*`） | 同上目录 |

⇒ **本包 = 能跑仿真的最小集**；证据链与历史实验**留在原目录**，两者不互相干扰。
