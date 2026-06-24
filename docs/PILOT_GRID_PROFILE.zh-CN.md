# Frame 1051 Pilot Grid Profile

## 1. 目的与 scope

本文记录阶段 1A 使用的 frame 1051 pilot fixed raw-coordinate grid profile。该 profile 用于生成 `longdress_vox10_1051.ply` 的 `PDL = 1.0` binary little-endian tile PLY baseline。

该 profile 已冻结为 frame 1051 pilot 的真实资产生成规则，但不等于官方世界坐标、物理尺度或最终全序列实验网格。

## 2. profile_id

```text
profile_id = longdress_raw_g128_fullseq_pilot_v1
dataset_id = 8i_longdress
source_frame_id = 1051
source_file = longdress_vox10_1051.ply
coordinate_basis = raw_coordinate
```

版本化配置文件：

```text
configs/pilot_grid_profile.longdress_1051_g128_raw_v1.json
```

## 3. raw-coordinate 语义与限制

本 profile 直接使用原始 Longdress ASCII PLY 中 `x/y/z` 字段的 raw-coordinate 值。阶段 0A、0C、0D 均观察到原始 PLY header 中存在 `frame_to_world_scale` 与 `frame_to_world_translation` comment，但阶段 1A 不解释其数学语义，也不应用任何坐标变换。

因此，本文中的 origin、max、extent、cell_size 与 tile bbox 均是 raw-coordinate 下的 derived 结果，不应写成物理米制坐标、官方世界坐标或已确认坐标轴语义。

## 4. G128 维度、origin、max、extent、cell_size

| 字段 | 数值 |
| --- | --- |
| grid_dimensions | `4 x 8 x 4` |
| theoretical_cell_count | `128` |
| grid_origin | `(0, 0, 0)` |
| grid_max | `(481, 1023, 660)` |
| grid_extent | `(481, 1023, 660)` |
| cell_size | `(120.25, 127.875, 165)` |

这些数值来自阶段 0D 的完整 300 帧 raw-coordinate envelope 扫描结果：

```text
full_sequence_bbox_min = (0, 0, 0)
full_sequence_bbox_max = (481, 1023, 660)
```

## 5. tile_id 规则与索引起点

阶段 1A 使用的 tile id 格式为：

```text
gx_<ix>_gy_<iy>_gz_<iz>
```

索引从 0 开始：

```text
ix in [0, 3]
iy in [0, 7]
iz in [0, 3]
```

该格式已作为 frame 1051 pilot 资产生成规则使用，但仍不自动等于最终全序列实验资产的正式 `tile_id` 规则。

## 6. 边界归属规则

每个轴使用半开区间：

```text
[min, max)
```

若某点坐标恰好等于该轴的 `grid_max`，则归入该轴最后一个 cell。三个轴的 index 组合唯一确定一个 tile，每个点必须恰好归属一个 tile。

## 7. grid universe、frame index 与资产文件的职责区分

G128 grid universe 包含 128 个理论 tile。`frame_1051_tile_index.json` 必须记录全部 128 个 tile，包括空 tile。

资产文件只为 frame 1051 的非空 tile 生成：

```text
tiles/<tile_id>/pdl_1.0.ply
```

frame-level tile index 负责记录 tile 是否为空、点数、bbox、资产相对路径、生成文件 sha256 和文件尺寸。binary PLY 文件只保存实际点记录，不承担完整 provenance、Stage2Input 或播放器 manifest 职责。

## 8. 空 tile 规则

frame 1051 中无点的 tile 不生成实际 PLY 文件、零字节 PLY 或占位文件。

空 tile 在 metadata 中记录为：

```text
is_empty = true
point_count = 0
asset_status = not_generated_empty
pdl_1_0_ply_relpath = null
```

空 tile 是否进入未来 Stage2Input 或播放器 XML 尚未冻结。

## 9. 与阶段 0C / 0D 的证据关联

阶段 0C 使用 5 帧 provisional envelope 对 G54 与 G128 做候选 probe。阶段 0D 对 Longdress 1051-1350 全 300 帧完成 raw-coordinate envelope 扫描，并在完整 envelope 下验证 G128 occupancy。

阶段 0D 中 frame 1051 在完整 envelope 下的 G128 结果为：

| 指标 | 数值 |
| --- | ---: |
| vertex_count | 765821 |
| non-empty tile count | 40 |
| empty tile count | 88 |
| maximum tile point share | 0.057920 |

阶段 1A 采用该完整 envelope 派生 profile 生成 `PDL = 1.0` baseline。

## 10. 明确未冻结的内容

- 是否将该 profile 作为最终全序列实验 grid。
- 低 PDL 采样算法、嵌套关系、随机种子和点数取整。
- Draco encoder 版本、命令、量化参数、压缩等级和解码验证规则。
- player manifest XML schema、asset catalog schema 与 Stage2Input 字段。
- `r_bytes` 与 `d_ms` 的正式口径。
- Longdress 坐标轴语义、物理单位或 `frame_to_world_*` 的数学语义。
