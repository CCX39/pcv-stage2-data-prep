# 低 PDL 采样语义追溯与适配分析

## 1. 阶段目的与不生成资产的边界

本文件记录阶段 1B 对低 PDL 采样语义的只读追溯。目标是理解既有 `pcv-distance-quality-calibration` 项目中 `PDL = {0.2, 0.4, 0.6, 0.8, 1.0}` 的真实生成或渲染语义，并分析其如何适配当前 frame 1051、G128 fixed raw-coordinate grid、非空 tile 独立质量候选资产。

本阶段不生成新的点云资产，不重新生成阶段 1A 的 `PDL = 1.0` baseline，不生成低 PDL PLY、DRC、BIN、XML、asset catalog 或 Stage2Input；未运行 calibration 正式实验、导师脚本、旧播放器或 Draco 工具。

## 2. 审查范围与外部参考路径

只读参考路径：

```text
CALIBRATION_REPO_ROOT =
E:\Miunaaaa\0-work\code\pcv-distance-quality-calibration

OLD_ASSETS_ROOT =
E:\Miunaaaa\0-work\code\vv\pythonProject\static\data\video_data\video_1

MENTOR_SCRIPT_PACKAGE_ROOT =
E:\Miunaaaa\0-work\code\MENTOR_SCRIPT_PACKAGE_vv_preprocess
```

本轮只做静态代码阅读、配置阅读、已有输出 metadata 阅读和旧质量 PLY 的有限 header / 内容只读检查。未修改任何外部目录或文件。

## 3. calibration 项目 PDL 生成链路追溯

### 代码直接证实

calibration 的正式渲染入口由 `package.json` 定义：

| npm script | 入口 | 配置 |
| --- | --- | --- |
| `render:full:minimal` | `scripts/render_screenshots/index.mjs --mode full-minimal` | `configs/experiment.longdress.mvp.json` |
| `render:near:full10` | `scripts/render_screenshots/index.mjs --mode near-full10` | `configs/experiment.longdress.near.json` |

渲染链路：

```text
scripts/render_screenshots/index.mjs
-> src/web/app/capture-main.js
-> src/web/renderer/render-point-cloud.js
-> src/web/loaders/ply-loader.js
-> src/web/renderer/nested-quality.js
```

`render_screenshots/index.mjs` 对每个 `frame_id / view / distance / quality_level` 构造请求，其中包含：

```text
quality_level
quality_seed
nested_sampling
plyUrl
```

`render-point-cloud.js` 调用：

```text
buildNestedQualityGeometry(loaded.geometry, qualityLevel, qualitySeed)
```

`nested-quality.js` 是正式渲染路径中低质量几何的核心实现位置。

### 由代码与配置共同支持的合理结论

正式 calibration run 并不为 `0.2 / 0.4 / 0.6 / 0.8` 写出新的 PLY 文件。它在浏览器渲染时从完整 PLY 加载出的 Three.js `BufferGeometry` 构造低质量 geometry，然后输出 PNG 截图和 metadata。

`prepare_debug_samples/index.mjs` 会为 debug 流程写出 `0.01 / 0.05 / 0.1` 的 binary little-endian PLY 样本，但这些是 debug sample，不是正式 `PDL = {0.2, 0.4, 0.6, 0.8, 1.0}` 资产，也不是当前新数据准备管线的低 PDL 资产来源。

### 当前无法确认

未发现 calibration 项目中有正式写出 `PDL = 0.2 / 0.4 / 0.6 / 0.8 / 1.0` PLY 资产的生成链路。已有正式 run 输出是截图、metrics、lookup table 与 metadata，而不是 quality PLY asset set。

## 4. PDL 质量档位与输入输出单位

两个正式配置均直接记录：

```json
"qualityLevels": [0.2, 0.4, 0.6, 0.8, 1.0]
```

`configs/experiment.longdress.mvp.json` 与 `configs/experiment.longdress.near.json` 均记录：

```json
"sampling": {
  "seed": 20260530,
  "nested": true
}
```

正式 full-body run 与 near-field run 的 `run_summary.json` 均显示质量档位为：

```text
0.2, 0.4, 0.6, 0.8, 1.0
```

对 full-body run 中 frame 1051、front view、distance 1.0 的 metadata 抽查显示：

| quality_level | point_count | source_point_count | quality_seed |
| ---: | ---: | ---: | ---: |
| 0.2 | 153164 | 765821 | 614905603 |
| 0.4 | 306328 | 765821 | 614905603 |
| 0.6 | 459492 | 765821 | 614905603 |
| 0.8 | 612656 | 765821 | 614905603 |
| 1.0 | 765821 | 765821 | 614905603 |

这些点数与 `floor(765821 * q)` 一致。`quality_seed` 来自 `render_screenshots/index.mjs` 中的 `seedForSource(config.sampling.seed, plyRelative)`，不是单独只用配置中的 `20260530`。

## 5. 嵌套性、随机性、点顺序与取整规则证据

### 嵌套性

代码直接证实 `nested-quality.js` 对同一个 source geometry、同一个 seed 使用同一个 permutation：

```text
permutation = shuffledIndices(sourcePointCount, seed)
selected = permutation.slice(0, outputPointCount)
```

由于 `0.2 / 0.4 / 0.6 / 0.8` 使用同一个 permutation 的不同长度前缀，因此在同一 source geometry、同一 seed、同一 point count 下具有：

```text
0.2 点集 ⊆ 0.4 点集 ⊆ 0.6 点集 ⊆ 0.8 点集 ⊆ 1.0 点集
```

这是由代码规则推出的 derived nested property。

### 随机性与 seed

`src/shared/utils/seeded-rng.mjs` 实现了确定性 seeded RNG，并在 `shuffledIndices(count, seed)` 中执行 Fisher-Yates shuffle。`seedForSource` 会把配置 seed 与 PLY 相对路径混合为具体 `quality_seed`。

因此，正式 run 的采样具有确定性和可复现性，但依赖：

- source geometry 的点数；
- source geometry 的原始点顺序；
- 配置 seed；
- PLY 相对路径字符串。

### 点顺序

`nested-quality.js` 在取出 permutation 前缀后执行：

```text
selected.sort((left, right) => left - right)
```

这意味着 selected set 由 permutation 前缀决定，而输出 geometry 的点顺序回到原始 source index 升序。算法没有按坐标排序，也没有对点做空间排序。

### 目标点数取整

`nested-quality.js` 的低质量点数为：

```text
Math.max(1, Math.floor(sourcePointCount * qualityLevel))
```

`qualityLevel = 1.0` 时直接返回 source geometry，点数为完整 source point count。

### 预处理与属性处理

`ply-loader.js` 支持 ASCII 与 binary little-endian PLY，解析 `x/y/z` 和 RGB 字段，构造 Three.js `position` 与 `color` attributes。颜色会转换为 `0-1` 浮点用于渲染；这属于渲染 geometry 表达，不是写出 PLY 资产。

正式渲染路径未观察到坐标变换、去重、体素化、坐标量化或点云裁剪。`near-field` 仍加载完整 Longdress PLY，只改变 camera target 与 partial-view 检查规则。

## 6. 旧质量资产的有限只读观察

本轮仅选择一个旧资产组做有限检查：

```text
GOF_1 / A3_ply_binary / frame_0 / cell_0
```

检查对象：

| 旧 representation | 文件 | format | vertex_count | 相对 R1 比例 | schema |
| --- | --- | --- | ---: | ---: | --- |
| R1 | `R1/frame_0/frame_0_cell_0.ply` | binary_little_endian 1.0 | 227188 | 1.000000 | `float x/y/z`, `uchar red/green/blue` |
| R2_0.8 | `R2_0.8/frame_0/frame_0_cell_0.ply` | binary_little_endian 1.0 | 181750 | 0.799998 | 同上 |
| R3_0.6 | `R3_0.6/frame_0/frame_0_cell_0.ply` | binary_little_endian 1.0 | 136312 | 0.599996 | 同上 |
| R4_0.4 | `R4_0.4/frame_0/frame_0_cell_0.ply` | binary_little_endian 1.0 | 90875 | 0.399999 | 同上 |

只读内容集合检查结果：

| 检查 | 结果 |
| --- | --- |
| `R2_0.8 ⊆ R1` | 是 |
| `R3_0.6 ⊆ R2_0.8` | 否 |
| `R4_0.4 ⊆ R3_0.6` | 否 |
| `R3_0.6 - R2_0.8` 的额外记录数 | 27368 |
| `R4_0.4 - R3_0.6` 的额外记录数 | 36271 |

该旧资产组能说明旧 A3 binary PLY 的 schema 与阶段 1A binary PLY schema 相容，也说明点数比例与目录名中的 `0.8 / 0.6 / 0.4` 接近。但它不能证明旧质量资产具有完整嵌套关系；本次有限检查反而观察到 `R3` 与 `R4` 并不构成逐级子集关系。

因此，旧质量文件仅作为历史格式或目录参考，不用于确定新 pipeline 的 PDL 语义。

## 7. frame-global 与 tile-local 两种适配方案比较

### 方案 A：frame-global sampling 后再切块

含义：

```text
先对完整 frame 生成某个 PDL 点集
再按 G128 切块
```

优点：

- 更接近 calibration 正式 run 的 source scope，因为 calibration 是完整 Longdress PLY 上的 full-cloud rendering。
- 如果沿用同一 permutation 前缀，则 frame 全局层面可保持 nested property。
- 同一质量档位下的全帧点数可严格符合 `floor(frame_point_count * q)`。

风险与限制：

- 每个 tile 的实际保留比例可能明显偏离目标 PDL，尤其是小 tile 或稀疏 tile。
- 某些低点数 tile 可能在低 PDL 下变得极少点，甚至在算法不设 tile 保底时为空。
- Stage2 将每个 tile 视为独立质量候选；frame-global sampling 会让 tile 质量比例成为全局采样的副产物，而不是每个 tile 的明确目标比例。
- 如果未来某个 tile 单独被选择为高或低质量，frame-global 采样生成的 tile-local候选语义不够直接。

### 方案 B：tile-local sampling

含义：

```text
以每个非空 tile 的 PDL=1.0 点集为基准，
在 tile 内独立生成 PDL 0.2 / 0.4 / 0.6 / 0.8。
```

优点：

- 每个 tile 可以保持明确的目标密度比例，适合 Stage2 的 tile 级候选资产语义。
- 可在同一 tile 内使用同一个 permutation 前缀保证 nested property。
- 空 tile 仍不生成实际资产，只在 metadata 中记录。
- 与阶段 1A 的 tile-local `PDL = 1.0` baseline 资产结构自然衔接。

风险与限制：

- 这是从 full-cloud calibration 采样规则迁移到 tile-local source scope 的 derived adaptation，不是新的 tile-level calibrated evidence。
- 小 tile 的 `floor(N_tile * q)` 可能导致极低点数；若使用 `max(1, floor(...))`，实际比例会偏高。
- 若 seed 只依赖 frame 而不依赖 tile，可能在不同 tile 间产生不必要的相关性；若 seed 依赖 tile，则需冻结 seed 派生规则。
- tile-local 结果与 calibration 的 full-cloud rendering 条件不完全等价，不能直接声称视觉阈值已重新标定。

## 8. 与距离标定实验可比性的边界

既有 distance-quality calibration 的 calibrated evidence 来自完整 Longdress 点云的 Web/Three.js 渲染截图与图像指标。即使 near-field run 关注局部 target，它仍渲染完整点云，不是 isolated tile experiment。

因此，即使新 tile pipeline 采用与 calibration 相近的 seeded nested prefix sampling，得到的 tile-local 低 PDL PLY 也应表述为：

```text
derived adaptation of the calibration sampling rule
```

不得表述为：

```text
tile-level calibrated PDL
```

除非后续另行设计并完成 isolated tile 或 tile-composited 的视觉标定实验。

## 9. 候选采样方案与推荐条件

### 候选 1：tile-local seeded nested prefix sampling

| 字段 | 内容 |
| --- | --- |
| 采样作用域 | tile-local |
| 是否可保证嵌套 | 可以；同一 tile 内使用同一 permutation 前缀 |
| 是否可复现 | 可以；需冻结 seed 派生规则 |
| 是否依赖输入点顺序 | 是；依赖阶段 1A tile PLY 中的点顺序 |
| 是否需要随机种子 | 是 |
| 目标点数计算方式 | 候选沿用 `max(1, floor(N_tile * p))`，但是否对小 tile 使用保底需研究者确认 |
| 与 calibration 生成规则的关系 | 算法形态接近 calibration 的 seeded permutation prefix，但 source scope 从 full frame 改为 tile |
| 对 Stage2 tile-level quality semantics 的影响 | 每个 tile 质量比例清晰，最适合独立候选资产 |
| 主要风险 | 不是 tile-level calibrated evidence；小 tile 取整可能导致比例偏差 |
| 是否建议作为下一阶段实施候选 | 建议作为优先实施候选，前提是研究者确认 seed、取整和小 tile 规则 |

### 候选 2：frame-global seeded nested prefix sampling 后切块

| 字段 | 内容 |
| --- | --- |
| 采样作用域 | frame-global |
| 是否可保证嵌套 | 可以；在完整 frame 层面使用同一 permutation 前缀 |
| 是否可复现 | 可以；可沿用 calibration 的 source path seed 规则或冻结新规则 |
| 是否依赖输入点顺序 | 是；依赖原始 frame 点顺序 |
| 是否需要随机种子 | 是 |
| 目标点数计算方式 | `max(1, floor(N_frame * p))`，tile 内点数由后续切块结果决定 |
| 与 calibration 生成规则的关系 | source scope 最接近 calibration 正式 run |
| 对 Stage2 tile-level quality semantics 的影响 | tile 内实际比例不受控，可能削弱 tile 独立候选语义 |
| 主要风险 | 小 tile 比例波动大；低质量下部分 tile 可能过稀或为空 |
| 是否建议作为下一阶段实施候选 | 不建议作为默认资产生成方案，可作为对照或敏感性分析候选 |

## 10. 已直接证实、derived 结论与未确认事项

### 已直接证实

- calibration 正式配置包含 `qualityLevels = [0.2, 0.4, 0.6, 0.8, 1.0]`。
- calibration 正式配置包含 `sampling.seed = 20260530` 与 `sampling.nested = true`。
- 正式渲染路径调用 `buildNestedQualityGeometry`。
- 低质量点数计算使用 `Math.max(1, Math.floor(sourcePointCount * qualityLevel))`。
- `qualityLevel = 1.0` 直接使用 source geometry。
- `shuffledIndices` 使用 seeded RNG 与 Fisher-Yates shuffle。
- `prepare_debug_samples` 会写 binary PLY debug samples，但不是正式低 PDL PLY 资产。
- 旧 A3 单组检查中，`R2_0.8` 是 `R1` 子集，但 `R3_0.6` 不是 `R2_0.8` 子集，`R4_0.4` 不是 `R3_0.6` 子集。

### derived 结论

- calibration 正式低质量 geometry 在同一 source geometry 和同一 seed 下具有 nested property。
- frame 1051 full-cloud metadata 中各 PDL 点数与 `floor(765821 * p)` 一致。
- 若新 pipeline 在 tile-local scope 中复用相同 prefix rule，可在每个 tile 内获得 nested property；但这属于 derived adaptation。

### 未确认事项

- 新数据准备项目的正式 low-PDL sampling profile。
- tile-local seed 派生规则。
- 小 tile 的保底点数与取整规则。
- 是否需要保持 tile PLY 输出顺序为 source index 升序。
- 是否采用 frame-global 方案作为对照。
- tile-level visual quality threshold 或 isolated tile calibration。
- Draco 参数、`r_bytes` 与 `d_ms` 正式口径。

## 11. 需要研究者确认的最终决策

1. 新 pipeline 低 PDL 采样作用域采用 tile-local、frame-global，还是两者都保留。
2. 若采用 tile-local，seed 是否由 `profile_id / frame_id / tile_id / pdl` 或其他字段派生。
3. 低 PDL target point count 是否使用 `floor(N * p)`，以及是否保留 `max(1, ...)`。
4. 小 tile 在低 PDL 下是否允许实际比例显著高于目标比例，或需要特殊记录。
5. 是否要求每个 tile 内满足 `0.2 ⊆ 0.4 ⊆ 0.6 ⊆ 0.8 ⊆ 1.0`。
6. 输出 binary PLY 的点顺序是否保持原始 tile PLY source index 升序。
7. 是否需要把 actual retained ratio 与 target PDL 同时写入 metadata。
8. 是否在多质量 PLY 生成后再进行可视化加载或小规模渲染 sanity check。

## 12. 对下一阶段的建议

建议下一阶段在研究者确认采样契约后，仅对 frame 1051 的 40 个非空 tile 生成 `PDL = 0.2 / 0.4 / 0.6 / 0.8` binary PLY，并独立验证：

- 每个 tile 内的 nested property；
- 每个 PDL 的 target point count 与 actual retained ratio；
- 坐标与 RGB 属性保真；
- 空 tile 不生成资产；
- metadata 中明确区分 target PDL、actual ratio、measured file size 与 derived fields。

下一阶段仍不应生成 DRC、BIN、XML、Stage2Input 或批量帧资产。
