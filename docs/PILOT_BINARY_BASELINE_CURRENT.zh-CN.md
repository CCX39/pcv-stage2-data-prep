# Frame 1051 Binary PLY Baseline 当前记录

## 1. 阶段目标与资产范围

阶段 1A 首次生成真实单帧 pilot 资产，范围严格限定为：

```text
Longdress frame 1051 原始 ASCII PLY
-> G128 fixed raw-coordinate grid 分块
-> 非空 tile 的 PDL = 1.0 binary little-endian PLY
-> frame-level metadata
-> 独立验证报告
```

本阶段未生成 `PDL = 0.2 / 0.4 / 0.6 / 0.8`、DRC、BIN、XML、player manifest、正式 asset catalog、Stage2Input 或批量帧资产。

## 2. 输入文件与 source provenance

只读输入文件：

```text
E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply\longdress_vox10_1051.ply
```

source header 直接观察：

```text
format ascii 1.0
element vertex 765821
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
```

source file sha256：

```text
58d59fe35383f5eb6257eeccec1b487cfaa694c0fc467ab5c5e2ad2161ba4fba
```

阶段 1A 不修改原始 PLY，不复制原始 PLY 到 Git，不应用 `frame_to_world_scale` 或 `frame_to_world_translation`。

## 3. grid profile 与生成命令

版本化 profile：

```text
configs/pilot_grid_profile.longdress_1051_g128_raw_v1.json
```

实际生成命令：

```powershell
python scripts\generate_pilot_binary_tiles.py `
  --raw-root "E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply" `
  --frame-id 1051 `
  --grid-profile "configs\pilot_grid_profile.longdress_1051_g128_raw_v1.json" `
  --output-dir "artifacts\pilot_1051_g128_raw_v1"
```

生成脚本只使用 Python 标准库。由于当前受限沙箱对仓库内目录 rename 操作返回权限拒绝，最终成功运行时使用了提升权限执行同一脚本；外部原始 PLY 仍仅作为只读输入。

## 4. PDL = 1.0 的准确语义

本阶段 `PDL = 1.0` 表示每个非空 tile 保留该 tile 的完整原始点集，不做降采样、去重、重排序、裁剪、量化或坐标变换。

低 PDL 采样算法、是否嵌套降采样、随机种子和点数取整规则尚未冻结。

## 5. 输出目录结构

本地生成资产目录：

```text
artifacts/pilot_1051_g128_raw_v1/
```

关键文件：

```text
generation_manifest.json
grid_profile_snapshot.json
frame_1051_tile_index.json
validation_report.json
tiles/<tile_id>/pdl_1.0.ply
```

`artifacts/` 被 Git 忽略，不提交其中任何文件。

## 6. 非空 / 空 tile 数量

| 指标 | 数值 |
| --- | ---: |
| theoretical tile count | 128 |
| non-empty tile count | 40 |
| empty tile count | 88 |
| source vertex count | 765821 |
| generated binary PLY file count | 40 |
| minimum non-empty tile point count | 765 |
| maximum tile point count | 44356 |
| maximum tile point share | 0.057920 |

空 tile 不生成 PLY 文件，metadata 中记录 `asset_status = not_generated_empty`。

## 7. 点数守恒与 binary PLY 验证结果

独立验证命令：

```powershell
python scripts\validate_pilot_binary_tiles.py `
  --raw-root "E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply" `
  --frame-id 1051 `
  --grid-profile "configs\pilot_grid_profile.longdress_1051_g128_raw_v1.json" `
  --artifact-dir "artifacts\pilot_1051_g128_raw_v1"
```

验证结果：

| 检查项 | 结果 |
| --- | --- |
| source header vertex count = 实际解析点数 | 通过 |
| source 点数 = 128 个 tile point_count 之和 | 通过 |
| source 点数 = 全部输出 binary PLY vertex count 之和 | 通过 |
| non_empty_tile_count + empty_tile_count = 128 | 通过 |
| frame 1051 non-empty tile count = 40 | 通过 |
| frame 1051 empty tile count = 88 | 通过 |
| 每个非空 tile 恰有一个 `pdl_1.0.ply` | 通过 |
| 空 tile 没有 binary PLY 文件 | 通过 |
| 每个输出点位于对应 tile 空间边界内 | 通过 |
| 每个输入点恰好归属一个 tile | 通过 |

## 8. 文件格式检查结果

本阶段新输出强制 schema：

```text
format binary_little_endian 1.0
element vertex <tile_point_count>
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
```

schema 兼容性预检表：

| 对象 | PLY format | vertex property 顺序 | x/y/z 类型 | red/green/blue 类型 | 是否存在额外 vertex 属性 | 是否与本阶段新输出 profile 兼容 | 证据来源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 原始 `longdress_vox10_1051.ply` | `ascii 1.0` | `x, y, z, red, green, blue` | `float` | `uchar` | 未观察到 | 作为 source schema 兼容 | 阶段 1A header 解析 |
| 旧 `A3_ply_binary/.../frame_0_cell_0.ply` | `binary_little_endian 1.0` | `x, y, z, red, green, blue` | `float` | `uchar` | 未观察到 | 作为 binary PLY schema 参考兼容 | 只读读取 header 到 `end_header` |
| 导师 `asciiTobin.py` | 输出意图为 binary PLY | 保留输入 property 列表 | 依据输入类型打包 | 依据输入类型打包 | 取决于输入 | 不直接复用；脚本会应用固定 transform 且依赖 Open3D | 静态阅读脚本 |
| 本阶段新输出 `pdl_1.0.ply` | `binary_little_endian 1.0` | `x, y, z, red, green, blue` | `float` | `uchar` | 无 | 兼容并已验证 | 独立验证脚本 |

导师脚本中观察到固定 transform 参数和可视化/批量转换逻辑。本阶段没有运行该脚本，也未采用其 transform、硬编码路径或批处理行为。

## 9. source digest 与 output digest 的验证说明

本阶段 canonical record 格式为：

```text
<fffBBB
```

含义：

```text
float32 x
float32 y
float32 z
uint8 red
uint8 green
uint8 blue
```

验证脚本按 tile 独立计算 source canonical record digest 与输出 binary PLY digest，并确认全部非空 tile 一致。这说明在本阶段支持的属性集合内，输出 tile PLY 的坐标与 RGB 值相对于原始 PLY header 声明的类型规范化后没有发生静默丢失或改变。

## 10. 生成资产的 measured / derived / 未确认字段区分

measured：

- 原始 source PLY 文件 sha256。
- 原始 source PLY header vertex count 与实际解析点数。
- 生成后 binary PLY 的文件尺寸与 sha256。
- 生成后 binary PLY header vertex count。

derived：

- tile bbox、tile point count、空 tile 状态。
- non-empty / empty tile count。
- maximum tile point share。
- canonical digest 比对结果。

未确认：

- Longdress 坐标轴语义、物理单位或米制解释。
- `frame_to_world_*` 的数学语义。
- 低 PDL 采样规则、Draco profile、XML schema、Stage2Input 字段。
- `r_bytes` 与 `d_ms` 的正式口径。

binary PLY 文件大小是生成资产的 measured 文件尺寸，但不是未来 Stage2 的正式 `r_bytes`，也不是端到端网络传输总开销。本文没有生成或声明任何 `d_ms`。

## 11. 当前明确未生成的资产

- `PDL = 0.2 / 0.4 / 0.6 / 0.8` binary PLY。
- Draco DRC。
- BIN。
- XML 或 player manifest。
- 正式 asset catalog schema。
- Stage2Input。
- 其他 frame 或全序列资产。

## 12. 后续阶段建议

建议先审阅 frame 1051 binary PLY baseline 的分块统计与可视化/加载可行性，再冻结 PDL 采样规则并生成多质量 binary PLY。
