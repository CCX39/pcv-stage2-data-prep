# 全序列 Raw-Coordinate Envelope 扫描与 G128 占用验证

## 1. 阶段目标与只读边界

本文件记录阶段 0D 对 8i Longdress 原始序列 300 帧进行的受控、只读 raw-coordinate envelope 扫描，以及基于完整 envelope 的 G128 occupancy 验证。

审查日期：2026-06-24。

本阶段目标是为“全序列共享、固定空间坐标网格”提供完整 raw-coordinate 证据，并验证研究者已确认的 `G128 = 4 x 8 x 4` 单帧 pilot provisional grid profile 在全序列 envelope 下的占用情况。

本轮未生成任何正式 tile PLY、binary PLY、quality-level PLY、DRC、BIN、XML、manifest、asset catalog 或 Stage2Input；未运行旧播放器、导师脚本、Draco encoder 或 Draco decoder；未修改原始 Longdress 目录或其他外部资产。

## 2. 输入目录、预期 frame 范围与实际扫描结果

外部只读输入目录：

```text
E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply
```

预期文件范围：

```text
longdress_vox10_1051.ply
...
longdress_vox10_1350.ply
```

实际扫描结果：

| 项目 | 结果 |
| --- | --- |
| 预期 frame 范围 | 1051-1350 |
| 实际扫描 frame 数 | 300 |
| 缺失 frame | 未观察到 |
| 扫描是否完整连续 | 是 |
| Stage A bbox 扫描耗时 | 246.64 s |
| Stage B G128 occupancy 扫描耗时 | 411.46 s |
| 总耗时 | 658.09 s |

点数范围：

| 指标 | frame | vertex_count |
| --- | ---: | ---: |
| 最小点数 | 1253 | 733580 |
| 最大点数 | 1137 | 916250 |

## 3. 扫描脚本、运行参数与输出路径

新增扫描脚本：

```text
scripts/run_full_sequence_envelope_scan.py
```

实际运行参数：

```powershell
python scripts\run_full_sequence_envelope_scan.py `
  --raw-root "E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply" `
  --frame-start 1051 `
  --frame-end 1350 `
  --output-dir outputs\full_sequence_envelope_scan `
  --pilot-frame-id 1051 `
  --grid-nx 4 `
  --grid-ny 8 `
  --grid-nz 4 `
  --progress-every 25
```

本地小型输出路径：

```text
outputs/full_sequence_envelope_scan/config_snapshot.json
outputs/full_sequence_envelope_scan/frame_raw_bbox.csv
outputs/full_sequence_envelope_scan/frame_g128_occupancy.csv
outputs/full_sequence_envelope_scan/g128_tile_activity_summary.csv
outputs/full_sequence_envelope_scan/sequence_envelope.json
outputs/full_sequence_envelope_scan/invariants.txt
outputs/full_sequence_envelope_scan/scan_summary.json
```

`outputs/` 受 Git 忽略，本轮不提交这些本地输出。

## 4. PLY 格式与 header 观察

脚本仅支持本阶段已观察到的 ASCII PLY，并对所有 300 帧检查：

```text
format ascii 1.0
element vertex <count>
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
```

本轮 300 帧的 vertex property 顺序一致。脚本也记录了 header comment 中的：

```text
frame_to_world_scale
frame_to_world_translation
```

但本阶段未自动应用或解释这些字段的数学语义。

## 5. 全序列 raw-coordinate bbox 结果

全序列 raw-coordinate bbox 并集：

```text
bbox_min = (0, 0, 0)
bbox_max = (481, 1023, 660)
center   = (240.5, 511.5, 330)
extent   = (481, 1023, 660)
```

全局 extrema 对应 frame：

| 轴 | 最小值 | 对应 frame | 最大值 | 对应 frame |
| --- | ---: | --- | ---: | --- |
| x | 0 | 1313, 1314 | 481 | 1069 |
| y | 0 | 1079, 1083 | 1023 | 1172, 1173, 1174 |
| z | 0 | 1056 | 660 | 1112 |

每帧 bbox extent 范围：

| 轴 | min | median | mean | max |
| --- | ---: | ---: | ---: | ---: |
| x extent | 196 | 330 | 318.70 | 439 |
| y extent | 976 | 998 | 998.19 | 1017 |
| z extent | 189 | 352 | 338.60 | 491 |

以上 bbox 均来自 PLY 中 `x/y/z` 字段的 raw-coordinate 值。

## 6. 全序列 envelope 的 provenance 与限制

provenance：

```text
derived from raw-coordinate bbox union across scanned frames
```

限制：

- 该 envelope 是从 300 帧原始 ASCII PLY 的 `x/y/z` raw-coordinate bbox 推导得到。
- 该 envelope 不能自动表述为物理米坐标、官方世界坐标或已确认尺度。
- `frame_to_world_scale` 与 `frame_to_world_translation` 在 header 中可观察到，但其数学语义和是否应进入正式 grid 定义仍未确认。
- 该 envelope 可作为 G128 full-sequence provisional grid parameters 的派生依据，但尚不是研究者冻结的正式最终 grid。

## 7. G128 full-sequence provisional grid parameters

使用完整 raw-coordinate envelope 派生的 G128 参数：

```text
Nx x Ny x Nz = 4 x 8 x 4
theoretical cell count = 128
grid_origin = (0, 0, 0)
cell_size = (120.25, 127.875, 165)
```

边界归属规则：

```text
每个轴采用 [min, max) 半开区间；
恰好等于全局 max 的点归入最后一个对应 cell；
每个点必须恰好归属一个 cell。
```

临时 tile id：

```text
gx_<ix>_gy_<iy>_gz_<iz>
```

该临时命名仍不是正式 `tile_id` 编码冻结决定。

## 8. 全序列 G128 occupancy 汇总

每帧 G128 non-empty tile count：

| 指标 | 数值 |
| --- | ---: |
| min | 37 |
| median | 45 |
| mean | 44.48 |
| max | 53 |

每帧 maximum tile point share：

| 指标 | 数值 |
| --- | ---: |
| min | 0.050517 |
| median | 0.063077 |
| mean | 0.064533 |
| max | 0.097896 |

非空 tile 数较少的样例：

| frame | non-empty tile count | maximum tile point share |
| ---: | ---: | ---: |
| 1255 | 37 | 0.062362 |
| 1174 | 37 | 0.065037 |
| 1078 | 37 | 0.064994 |

非空 tile 数较多的样例：

| frame | non-empty tile count | maximum tile point share |
| ---: | ---: | ---: |
| 1185 | 53 | 0.063550 |
| 1291 | 52 | 0.071397 |
| 1216 | 52 | 0.076121 |

128 个 theoretical tile 中，从未在任何扫描帧中激活的 tile 数量：

```text
20
```

这些从未激活的 tile 只说明在本序列 raw-coordinate envelope 与 G128 provisional grid 下未观察到点，不代表未来正式管线一定生成或不生成对应 metadata。

## 9. frame 1051 在完整 envelope 下的 G128 occupancy

frame 1051 在完整 full-sequence envelope 下的 G128 occupancy：

| 指标 | 数值 |
| --- | ---: |
| vertex_count | 765821 |
| non-empty tile count | 40 |
| empty tile count | 88 |
| minimum nonzero tile point count | 765 |
| maximum tile point count | 44356 |
| maximum tile point share | 0.057920 |

该结果使用完整 300 帧 raw-coordinate envelope，不同于阶段 0C 的 5 帧 provisional envelope。

## 10. 与阶段 0C 五帧 provisional envelope 结果的对比

阶段 0C 的 5 帧 envelope：

```text
bbox_min = (27, 3, 22)
bbox_max = (459, 1012, 570)
extent   = (432, 1009, 548)
G128 cell_size = (108, 126.125, 137)
```

阶段 0D 的全序列 envelope：

```text
bbox_min = (0, 0, 0)
bbox_max = (481, 1023, 660)
extent   = (481, 1023, 660)
G128 cell_size = (120.25, 127.875, 165)
```

frame 1051 的 G128 结果对比：

| 指标 | 阶段 0C：5 帧 envelope | 阶段 0D：全序列 envelope |
| --- | ---: | ---: |
| non-empty tile count | 46 | 40 |
| empty tile count | 82 | 88 |
| maximum tile point share | 0.049999 | 0.057920 |

主要差异：

- 全序列 envelope 在 x/y/z 三个轴上都比 5 帧 envelope 更大。
- 使用更大的 full-sequence envelope 后，frame 1051 的点被分配到更大的 cell 中，因此非空 tile 数从 46 降为 40。
- 最大 tile point share 从约 5.00% 增至约 5.79%。
- 这说明 0C 的 5 帧 envelope 对 frame 1051 的 G128 结果偏乐观地细分了部分空间；是否接受 full-sequence envelope 下的占用分布仍需研究者确认。

## 11. 不变量检查

Stage A 不变量：

| 检查项 | 结果 |
| --- | --- |
| scanned_frame_count = 300 | 通过 |
| 1051-1350 每个期待 frame 恰好对应一个输入文件 | 通过 |
| 每帧 parsed_point_count = header_vertex_count | 通过 |
| 全序列 envelope 包含每帧 bbox | 通过 |

Stage B 不变量：

| 检查项 | 结果 |
| --- | --- |
| 每帧各 tile point_count 之和 = 该帧 total point count | 通过 |
| 每个点恰好归属一个 G128 cell | 通过 |
| 每帧 non_empty_tile_count + empty_tile_count = 128 | 通过 |
| 每帧无负 tile point_count | 通过 |

## 12. 直接观察到、derived 结果与未确认事项

直接观察到：

- 1051-1350 共 300 个预期 PLY 文件存在并被读取。
- 所有扫描帧均为 `format ascii 1.0`。
- 所有扫描帧均包含 `x/y/z/red/green/blue` vertex 属性。
- 所有扫描帧 parsed point count 与 header vertex count 一致。

derived：

- 每帧 raw-coordinate bbox。
- 全序列 raw-coordinate envelope。
- G128 full-sequence provisional `grid_origin` 与 `cell_size`。
- 每帧 G128 tile occupancy、non-empty tile count、empty tile count 与 maximum tile point share。
- 128 个 theoretical tile 中有 20 个在本轮 300 帧扫描中从未激活。

未确认：

- Longdress 坐标轴语义、物理单位或米制解释。
- `frame_to_world_scale` 与 `frame_to_world_translation` 的数学语义及其是否进入正式 grid 定义。
- 正式最终 grid、正式 `tile_id`、正式边界规则。
- G128 是否适合全序列正式资产生成。
- PDL 采样规则、Draco profile、XML schema、`r_bytes` / `d_ms` 正式口径。

## 13. 对下一阶段人工决策的建议

建议研究者审阅：

1. 是否接受 full-sequence raw-coordinate envelope `(0, 0, 0)` 到 `(481, 1023, 660)` 作为后续正式 pilot grid 的候选包络。
2. 是否接受 `G128 = 4 x 8 x 4` 在完整 envelope 下的占用分布，特别是 frame 1051 的 40 个非空 tile 和最大 tile point share `0.057920`。
3. 是否需要调整 envelope 边界、grid 维度或边界归属规则后再冻结 pilot grid。
4. 20 个全序列 never-active theoretical tile 在未来 metadata、player manifest XML 与 Stage2Input 中是否保留。
5. 在研究者确认正式 pilot grid profile 后，再进入单帧正式切块与 level-1 binary PLY 基线生成准备。

本阶段结果仍不支持直接启动批量切块、质量版本生成、Draco 编码或完整 XML 生成。
