# 原始坐标空间 Grid Probe 当前记录

## 1. 目的与只读边界

本文件记录阶段 0C 对 8i Longdress 少量帧进行的 raw-coordinate grid probe。目的仅是为后续人工冻结单帧 pilot 网格方案提供证据，不生成正式 tile 资产。

审查日期：2026-06-23。

本轮仅执行了受控、只读的 PLY header 与坐标扫描，并在仓库内 `outputs/grid_probe/` 写入小型本地检查结果。`outputs/` 受 `.gitignore` 忽略，不作为版本化资产提交。

本轮未生成 tile PLY、quality-level PLY、binary PLY、DRC、BIN、XML、asset catalog、manifest 或 Stage2Input；未运行旧播放器、导师脚本、Draco encoder 或 Draco decoder；未修改任何外部数据目录。

## 2. 输入数据与扫描 frame 集合

外部只读输入目录：

```text
E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply
```

本轮只扫描以下 5 个帧：

| frame_id | 文件名 | 作用 |
| --- | --- | --- |
| 1051 | `longdress_vox10_1051.ply` | pilot frame |
| 1125 | `longdress_vox10_1125.ply` | bbox 初步观察 |
| 1200 | `longdress_vox10_1200.ply` | bbox 初步观察 |
| 1275 | `longdress_vox10_1275.ply` | bbox 初步观察 |
| 1350 | `longdress_vox10_1350.ply` | bbox 初步观察 |

没有扫描完整 300 帧。

## 3. PLY 格式与 header 观察

5 个扫描帧均被脚本识别为：

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

直接观察到的 comment 字段：

```text
Version 2, Copyright 2017, 8i Labs, Inc.
frame_to_world_scale 0.179523
frame_to_world_translation -45.2095 7.18301 -54.3561
width 1023
```

5 个扫描帧未观察到 `obj_info`。本阶段只记录 `frame_to_world_scale` 与 `frame_to_world_translation` 的原始 header 字符串，不解释其数学语义，也不自动应用到坐标。

## 4. raw-coordinate bbox 结果

下表的 bbox 均来自直接读取 PLY 中 `x/y/z` 字段，不是物理米坐标，也不是已确认世界坐标。

| frame_id | vertex_count | bbox_min (x,y,z) | bbox_max (x,y,z) | center (x,y,z) | extent (x,y,z) |
| --- | ---: | --- | --- | --- | --- |
| 1051 | 765821 | (103, 9, 22) | (459, 1012, 318) | (281, 510.5, 170) | (356, 1003, 296) |
| 1125 | 821060 | (81, 7, 276) | (423, 1004, 550) | (252, 505.5, 413) | (342, 997, 274) |
| 1200 | 800259 | (105, 3, 81) | (440, 993, 570) | (272.5, 498, 325.5) | (335, 990, 489) |
| 1275 | 893378 | (27, 8, 149) | (430, 1011, 390) | (228.5, 509.5, 269.5) | (403, 1003, 241) |
| 1350 | 806806 | (151, 5, 87) | (397, 1012, 523) | (274, 508.5, 305) | (246, 1007, 436) |

## 5. provisional envelope 的定义与限制

本轮 provisional envelope 定义为 5 个扫描帧 raw-coordinate bbox 的并集：

```text
bbox_min = (27, 3, 22)
bbox_max = (459, 1012, 570)
center   = (243, 507.5, 296)
extent   = (432, 1009, 548)
```

限制：

- 该 envelope 只来自 5 个采样帧，不代表全序列最终空间包络。
- 不能据此确认官方坐标轴方向、物理单位或世界坐标定义。
- `frame_to_world_scale` 与 `frame_to_world_translation` 虽在 header 中观察到，但本阶段未确认其应如何参与新 grid 定义。

## 6. G54 与 G128 的配置

本轮仅比较两个候选 profile：

| profile | Nx x Ny x Nz | theoretical cell count | 说明 |
| --- | --- | ---: | --- |
| G54 | 3 x 6 x 3 | 54 | 候选粗粒度 probe profile |
| G128 | 4 x 8 x 4 | 128 | 候选较细粒度 probe profile |

临时 tile id 使用：

```text
gx_<ix>_gy_<iy>_gz_<iz>
```

该命名只用于 probe 输出，不是正式 `tile_id` 编码决定。

## 7. 点归属规则与不变量检查

点归属规则：

```text
每个轴使用 [min, max) 半开区间；
刚好落在该轴最大边界的点归入最后一个 cell；
三个轴的 index 组合唯一确定一个临时 tile。
```

不变量检查结果：

| 检查项 | 结果 |
| --- | --- |
| 每个扫描帧 parsed point count 等于 PLY header vertex count | 通过 |
| G54 各 tile point_count 之和等于 pilot frame 点数 | 通过 |
| G128 各 tile point_count 之和等于 pilot frame 点数 | 通过 |
| G54 每个点恰好归属一个 tile | 通过 |
| G128 每个点恰好归属一个 tile | 通过 |
| non_empty_tile_count + empty_tile_count 等于 theoretical cell count | 通过 |

本地输出文件：

```text
outputs/grid_probe/config_snapshot.json
outputs/grid_probe/frame_bbox.csv
outputs/grid_probe/grid_stats.json
outputs/grid_probe/invariants.txt
outputs/grid_probe/tile_counts_G54.csv
outputs/grid_probe/tile_counts_G128.csv
```

## 8. 两个候选 grid 的统计对比

统计分母为 frame 1051 的总点数 `765821`。

| 指标 | G54 | G128 |
| --- | ---: | ---: |
| theoretical cell count | 54 | 128 |
| non-empty tile count | 25 | 46 |
| empty tile count | 29 | 82 |
| minimum non-empty tile point count | 189 | 66 |
| p10 non-empty tile point count | 606.4 | 1580 |
| median non-empty tile point count | 26747 | 15161.5 |
| p90 non-empty tile point count | 59235 | 31857 |
| maximum non-empty tile point count | 92858 | 38290 |
| maximum tile point share | 0.121253 | 0.049999 |
| minimum tile point share, all cells | 0 | 0 |
| minimum non-empty tile point share | 0.000247 | 0.000086 |

G54 降序摘要前 12 个 tile：

| rank | tile_id | point_count | point_share |
| ---: | --- | ---: | ---: |
| 1 | `gx_1_gy_1_gz_0` | 92858 | 0.121253 |
| 2 | `gx_1_gy_2_gz_0` | 77559 | 0.101276 |
| 3 | `gx_1_gy_5_gz_0` | 60953 | 0.079592 |
| 4 | `gx_1_gy_4_gz_0` | 56658 | 0.073983 |
| 5 | `gx_1_gy_0_gz_0` | 55124 | 0.071980 |
| 6 | `gx_1_gy_3_gz_0` | 51563 | 0.067330 |
| 7 | `gx_0_gy_3_gz_0` | 50803 | 0.066338 |
| 8 | `gx_1_gy_2_gz_1` | 48855 | 0.063794 |
| 9 | `gx_1_gy_1_gz_1` | 44979 | 0.058733 |
| 10 | `gx_2_gy_3_gz_0` | 42404 | 0.055371 |
| 11 | `gx_0_gy_4_gz_0` | 41515 | 0.054210 |
| 12 | `gx_2_gy_4_gz_0` | 35630 | 0.046525 |

G128 降序摘要前 12 个 tile：

| rank | tile_id | point_count | point_share |
| ---: | --- | ---: | ---: |
| 1 | `gx_2_gy_1_gz_0` | 38290 | 0.049999 |
| 2 | `gx_1_gy_4_gz_0` | 38187 | 0.049864 |
| 3 | `gx_2_gy_1_gz_1` | 36112 | 0.047155 |
| 4 | `gx_1_gy_3_gz_0` | 35729 | 0.046655 |
| 5 | `gx_1_gy_5_gz_0` | 32529 | 0.042476 |
| 6 | `gx_2_gy_2_gz_0` | 31185 | 0.040721 |
| 7 | `gx_2_gy_2_gz_1` | 28853 | 0.037676 |
| 8 | `gx_1_gy_3_gz_1` | 27828 | 0.036337 |
| 9 | `gx_2_gy_4_gz_0` | 26651 | 0.034801 |
| 10 | `gx_2_gy_3_gz_0` | 25793 | 0.033680 |
| 11 | `gx_2_gy_3_gz_1` | 25465 | 0.033252 |
| 12 | `gx_1_gy_2_gz_0` | 24291 | 0.031719 |

## 9. 直接观察到的事实

- 指定 5 帧均为 ASCII PLY，且均包含 `x/y/z/red/green/blue` vertex 属性。
- 指定 5 帧均观察到相同的 `frame_to_world_scale` 与 `frame_to_world_translation` header comment 字符串。
- frame 1051 点数为 `765821`。
- 使用 5 帧 raw bbox 并集作为 provisional envelope 时，G54 在 frame 1051 上有 25 个非空 tile，G128 有 46 个非空 tile。
- G128 的最大 tile point share 低于 G54；在本轮 probe 中，G128 的最大单 tile 占比约为 5.00%，G54 约为 12.13%。

## 10. 仅作为初步推测的解释

- G128 相比 G54 提供了更细的空间划分，最大 tile 点数占比更低，可能更适合继续讨论 Stage2 的空间质量分配粒度。
- G128 同时带来更多空 tile 与更多低点数非空 tile，后续可能增加 metadata、空 tile 表达和播放器资源组织复杂度。
- G54 更粗，非空 tile 数更少，可能更容易完成第一轮端到端 pilot，但部分 tile 聚集较多点，空间分配粒度可能偏粗。

上述均为基于本轮 5 帧与 frame 1051 的初步解释，不是最终 grid 选型。

## 11. 不能从本阶段确认的事项

- 最终 `Nx x Ny x Nz`。
- 全序列最终 envelope、grid origin、cell size 与边界归属规则。
- 正式 `tile_id` 编码。
- 工作性 vertical axis。
- Longdress 坐标轴方向、物理单位或米制解释。
- 是否应使用 `frame_to_world_scale` 与 `frame_to_world_translation` 建立正式世界坐标。
- G54 或 G128 是否能适配全 300 帧。
- 空 tile 是否进入未来 Stage2Input 或播放器 XML。
- 质量版本、PDL 采样算法、Draco profile、`r_bytes` 与 `d_ms` 口径。

## 12. 对下一阶段人工决策的建议

建议研究者优先讨论：

1. 是否继续以 G128 为下一轮候选，或在 G54 与 G128 之间提出中间 grid。
2. 是否先补充更多只读帧 bbox probe，再冻结全序列 provisional envelope 计算规则。
3. 空 tile 在 asset metadata、player manifest XML 与 Stage2Input 中是否分别出现，以及路径字段如何表示。
4. 是否需要在正式 grid 冻结前先确认 `frame_to_world_*` header 字段的来源与语义。
5. 播放器资源层是否能够接受比旧 12-cell 更细的 cell/tile 数量。

本阶段结果更适合支持下一轮讨论，不适合直接启动批量切块或批量编码。
