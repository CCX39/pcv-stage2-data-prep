# Frame 1051 DRC Pilot Corpus 当前状态

## 1. Corpus Identity

本 corpus 面向 8i Longdress frame 1051，使用 `longdress_raw_g128_fullseq_pilot_v1` G128 pilot grid，以及阶段 1D 已生成并验证的五档 tile-local binary PLY source assets。

当前 DRC delivery candidate family 为：

```text
source_pdl x qp

source_pdl = {0.2, 0.4, 0.6, 0.8, 1.0}
qp = {8, 10, 12}
codec = Draco
point-cloud mode = -point_cloud
cl = 10
```

`qc` 当前不进入 variant identity、文件名、metadata 或实际命令。

## 2. Output Root

本地 artifact root 为：

```text
artifacts/pilot_1051_g128_drc_pdl5_qp3_cl10_v1/
```

该目录被 Git 忽略，不进入版本库。版本库仅保存生成脚本、验证脚本、profile 配置与中文说明文档。

## 3. 实际规模

根据 `generation_manifest.json` 与 `validation_report.json`：

| 项目 | 数值 |
| --- | ---: |
| non-empty tile | 40 |
| source_pdl 档位 | 5 |
| qp 档位 | 3 |
| DRC variant 总数 | 600 |
| qp=8 DRC 数量 | 200 |
| qp=10 DRC 数量 | 200 |
| qp=12 DRC 数量 | 200 |

按 qp 汇总的 measured encoded file size 为：

| qp | DRC 数量 | total_drc_file_size_bytes |
| ---: | ---: | ---: |
| 8 | 200 | 7140527 |
| 10 | 200 | 8963511 |
| 12 | 200 | 10748050 |

这些 byte size 是生成后 DRC 文件的 measured encoded file size，不自动等价于最终网络开销、正式 `r_bytes` 或 `D(i,v)`。

## 4. Provenance

本 corpus 的 source artifact 为：

```text
artifacts/pilot_1051_g128_tilelocal_pdl5_v1/
```

生成 manifest 记录了：

- `source_pdl`、`qp`、`cl` 与 codec identity；
- source PLY relative path、SHA-256 与 file size；
- DRC relative path、SHA-256 与 measured file size；
- encoder / decoder executable path 与 SHA-256；
- source artifact manifest 与 tile index 的 SHA-256；
- profile snapshot 与 generation summary。

当前记录到的 Draco executable SHA-256 为：

```text
encoder_sha256 = EF2BDDC544E46CBA1396037998055A51517D867E9374AD26A4C69947C47AC4C6
decoder_sha256 = CA931DFBBD7EA70311F6642147FF495EDD4682C120AF365F797CFACA2EFF3460
```

## 5. 验证边界

全量 600 个 DRC 均通过 basic decode-integrity 检查：

- decoder exit code 为 0；
- decoded PLY 可解析；
- decoded PLY 含 `x/y/z/red/green/blue`；
- decoded point count 等于对应 source PLY point count；
- decoded coordinates 均为有限数；
- RGB triplet multiset 与 source PLY 完全一致；
- DRC 文件存在且 byte size 大于 0。

6 个 canary variant 执行阶段 2B.1 同等强度的深度检查：

```text
min/max non-empty tile x pdl=1.0 x qp={8,10,12}
```

canary 检查覆盖：

- order-independent bidirectional geometry point-set validation；
- high-confidence mutual-nearest local RGB association；
- qp=8/10/12 DRC hash effect。

## 6. 当前可用事实

当前已经具备：

- frame 1051 的真实 tile-level composite variant identity；
- 600 个真实 DRC delivery candidate files；
- 每个 DRC 的 measured encoded file size；
- 每个 DRC 到 source binary PLY、tile、source_pdl、qp、encoder/decoder toolchain 的 provenance；
- 全量 basic decode-integrity evidence；
- 固定 canary 的 order-independent round-trip 深度验证 evidence。

## 7. 当前未完成

当前仍未完成：

- 最终 target-side `D(i,v)` benchmark；
- 最终 DRC-aware `Q_base(i,v)`；
- Stage2Input；
- lookup projection；
- Pareto pruning；
- 正式 asset catalog；
- 播放器 XML / DASH 风格自定义资源清单；
- 多帧或全序列 DRC corpus。

因此，本 corpus 可作为 frame 1051 Stage2 pilot 的真实 DRC asset foundation，但不能写成完整数据集、最终 codec profile、最终 solver contract 或端侧性能测量结果。
