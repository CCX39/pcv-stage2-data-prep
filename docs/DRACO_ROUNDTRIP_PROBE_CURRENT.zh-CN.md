# Draco round-trip probe 当前记录

## 1. 阶段目标与范围

阶段 2B / 2B.1 针对 frame 1051 的两个代表性非空 tile 执行并收敛 Draco PLY -> DRC -> PLY round-trip probe。probe 覆盖：

```text
2 个代表 tile
× 5 个 source_pdl
× 3 个 qp
= 30 个 DRC variants
```

本阶段只验证当前本机 Draco CLI、`source_pdl × qp` 变体、几何 point-set fidelity、RGB 值保留与 provenance 链。它不是全量 600 DRC corpus，不是正式 asset catalog，不是 Stage2Input，不是 target-side decode benchmark，也不是 DRC-aware `Q_base(i,v)` 标定。

## 2. 输入、输出与代表 tile

source multi-PDL artifact root：

```text
artifacts/pilot_1051_g128_tilelocal_pdl5_v1/
```

probe artifact root：

```text
artifacts/draco_roundtrip_probe_1051_g128_pdl5_qp3_cl10_v1/
```

代表 tile 由 `frame_1051_tile_index.json` 自动选择：

| 选择原因 | tile_id | source_point_count |
| --- | --- | ---: |
| min_nonempty | `gx_3_gy_6_gz_0` | 765 |
| max_nonempty | `gx_1_gy_4_gz_0` | 44356 |

probe root 中包含 30 个 `.drc` 与 30 个 `.decoded.ply`。这些 artifact 位于 Git ignored 路径中，不进入版本库。

## 3. Draco 工具链与命令语义

实际工具链：

| 工具 | 路径 | SHA-256 | 文件大小 |
| --- | --- | --- | ---: |
| encoder | `E:\Miunaaaa\0-work\code\draco_encoder\draco-1.5.7\build\Release\draco_encoder.exe` | `EF2BDDC544E46CBA1396037998055A51517D867E9374AD26A4C69947C47AC4C6` | 681472 |
| decoder | `E:\Miunaaaa\0-work\code\draco_encoder\draco-1.5.7\build\Release\draco_decoder.exe` | `CA931DFBBD7EA70311F6642147FF495EDD4682C120AF365F797CFACA2EFF3460` | 398848 |

编码命令语义：

```text
draco_encoder -point_cloud -i <source_ply> -o <target_drc> -cl 10 -qp <8|10|12>
```

解码命令语义：

```text
draco_decoder -i <target_drc> -o <decoded_ply>
```

本阶段没有使用 `-qc`、`-qg` 或任何颜色量化控制参数。

## 4. 旧 strict point-order contract 与修正

阶段 2B 初版 validator 曾要求 decoded PLY 保持 source PLY 的 point record order，并按相同 point index 比较 RGB。实际 Draco point-cloud decode 可以重排点记录，旧 contract 在 `gx_3_gy_6_gz_0 / pdl_0.2 / qp8` 等变体上触发同 index RGB mismatch。

研究者已确认：

```text
decoded point order 不要求保留；
point order 不作为当前 DRC delivery asset 的正确性不变量。
```

阶段 2B.1 validator 改为 order-independent validation：

1. vertex count 与 PLY schema 必须一致；
2. geometry 使用双向 nearest-neighbor point-set check；
3. RGB triplet multiset 必须完全一致；
4. 高置信 mutual-nearest spatial correspondence 点对的 RGB 必须完全一致；
5. point order 仅记录为 `not_required_for_draco_roundtrip`。

## 5. 几何 tolerance 与验证结果

每个 source / decoded pair 的几何容差由 source bbox span 与 `qp` 推导：

```text
step_x = span_x / (2^qp - 1)
step_y = span_y / (2^qp - 1)
step_z = span_z / (2^qp - 1)

geometry_tolerance =
sqrt(step_x^2 + step_y^2 + step_z^2)
+ 1e-6 * max(1.0, max(span_x, span_y, span_z))
```

独立 validator 对每个 pair 执行 source -> decoded 与 decoded -> source 双向 point-set check。阶段 2B.1 当前汇总结果：

| 指标 | 数值 |
| --- | ---: |
| source_to_decoded_max_distance | 0.4416230490721022 |
| source_to_decoded_mean_distance_max_across_variants | 0.2485783423474276 |
| decoded_to_source_max_distance | 0.4416230490721022 |
| decoded_to_source_mean_distance_max_across_variants | 0.2485783423474276 |
| geometry_tolerance_max | 0.8567411965697239 |

结论：当前 30 个 variants 的 decoded coordinates 均为有限数，且通过 order-independent 双向几何 point-set fidelity check。

## 6. RGB 验证结果

RGB 验证分为两层。

硬性条件：

```text
Counter(source RGB triplets) == Counter(decoded RGB triplets)
```

诊断条件：

```text
高置信 mutual-nearest spatial correspondence 点对的 RGB 必须 exact match。
```

当前 30 个 variants 的汇总结果：

| 指标 | 数值 |
| --- | ---: |
| rgb_multiset_exact_for_all_variants | true |
| mutual_unique_pair_coverage_min | 1.0 |
| mutual_unique_rgb_exact_match_rate_min | 1.0 |
| ambiguous_or_nonmutual_point_count_max | 0 |
| ambiguous_or_nonmutual_decoded_point_count_sum | 0 |
| ambiguous_or_nonmutual_source_point_count_sum | 0 |

已确认：RGB triplet multiset 完全一致；本轮所有高置信空间对应点对的 RGB 完全一致，且当前 probe 中未观察到 ambiguous / nonmutual 点。

仍需避免过度表述：该结果不等于颜色量化控制机制已确认，不等于 `qc` 已验证，也不等于 RGB compression 已优化。

## 7. DRC bytes 与 qp effect

按 `qp` 汇总的 DRC bytes：

| qp | min bytes | max bytes | sum bytes |
| ---: | ---: | ---: | ---: |
| 8 | 916 | 125790 | 408590 |
| 10 | 1041 | 160762 | 515399 |
| 12 | 1172 | 194934 | 619493 |

对 max_nonempty tile `gx_1_gy_4_gz_0` 的 `source_pdl = 1.0`，三档 `qp` 的 DRC SHA-256 两两不同：

| qp | bytes | SHA-256 |
| ---: | ---: | --- |
| 8 | 125790 | `C6E18CCB1ACCD18904117C24EA72EC1F701309DB5EA2B6851681F122C5788E3D` |
| 10 | 160762 | `D2D9274BB01552D8060DF0D003486BA0DDCE32D426DDCC8DC0207FBDF6A1A2BE` |
| 12 | 194934 | `792DE9958B67F6AC93125499D3271113DC89AFB0028A5A8FE1C131FB8AC5CA59` |

结论：当前 probe 观察到 `qp=8/10/12` 产生不同 DRC representation。DRC file size 是 generated encoded file 的 measured size；不得自动写成正式 `r_bytes`、端到端网络开销或 target-side `D(i,v)`。

## 8. qc 当前状态

当前 native `draco_encoder` help 未暴露 `-qc`。历史 `qc=4/6/8` 未观察到明显 DRC bytes 或视觉差异，可能与该参数未被当前 native CLI 识别或应用有关，但本轮不做最终归因。

当前 active DRC variant dimension 为：

```text
source_pdl × qp
```

`qc` 不进入当前 variant identity、file name、generation command 或 metadata 作为已生效参数。RGB compression-control / color quantization CLI 属于 future investigation，不阻塞当前 frame 1051 `source_pdl × qp` DRC pipeline。

## 9. 已确认事实与未证明事项

已确认：

- 当前安装的 Draco encoder / decoder 可对两个代表 tile 的五档 binary PLY 完成实际 PLY -> DRC -> PLY round-trip。
- `-point_cloud`、`-cl 10`、`-qp {8,10,12}` 在本轮实际命令中可执行。
- 30 个 DRC 与 30 个 decoded PLY 均存在，并通过 provenance、hash、file size 与 matrix 完整性验证。
- decoded PLY 的点记录顺序不作为正确性不变量。
- order-independent geometry point-set check、RGB multiset check、高置信 local RGB association check 均通过。
- max_nonempty tile 的 `source_pdl=1.0` 下，`qp=8/10/12` 的 DRC hash 两两不同。

尚未证明：

- 全量 `40 × 5 × 3 = 600` DRC corpus 已生成。
- target-side decode cost `D(i,v)` 已测得。
- DRC-aware `Q_base(i,v)` 已测得或标定。
- RGB compression-control / color quantization 参数已确认。
- lookup projection、Pareto pruning、Stage2Input 或正式 asset catalog 已冻结。

## 10. 下一阶段前提

阶段 2C 可在研究者确认后进入 frame 1051 全量 DRC 生成：

```text
40 non-empty tiles × 5 source_pdl × 3 qp = 600 DRC delivery variants
```

阶段 2C 应沿用本阶段确认的 order-independent round-trip validation contract，并继续明确区分 generated DRC file bytes、future `r_bytes` 口径、target-side `D(i,v)` 与 DRC-aware `Q_base(i,v)`。
