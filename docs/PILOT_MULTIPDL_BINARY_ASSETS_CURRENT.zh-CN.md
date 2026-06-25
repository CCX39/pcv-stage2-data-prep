# frame 1051 五档 binary PLY pilot 资产记录

## 1. 阶段目标与生成范围

阶段 1D 针对 8i Longdress `frame_id = 1051`、固定 G128 pilot grid 和 40 个非空 tile，生成并验证五档 binary little-endian tile PLY：

```text
PDL = 0.2 / 0.4 / 0.6 / 0.8 / 1.0
```

本阶段是阶段 1C 已冻结 tile-local sampling contract 的受控实现与真实文件级验证，不重新讨论或修改 sampling semantics。

本阶段没有生成 Draco DRC、BIN、播放器 XML、正式 asset catalog、Stage2Input、多帧或全序列资产，也没有进行 GoF 聚合、`r_bytes` 正式映射、`d_ms` benchmark/proxy 或相机相关运行时字段生成。

## 2. 输入 baseline 与输出 artifact root

输入 baseline root：

```text
artifacts/pilot_1051_g128_raw_v1/
```

该 root 来自阶段 1A，包含 frame 1051 的 40 个非空 tile 的 `PDL = 1.0` binary little-endian PLY baseline，并已通过独立验证。

本阶段新生成 root：

```text
artifacts/pilot_1051_g128_tilelocal_pdl5_v1/
```

该目录位于 Git ignored 的 `artifacts/` 下，不进入版本库。新 root 包含：

```text
generation_manifest.json
grid_profile_snapshot.json
sampling_profile_snapshot.json
frame_1051_tile_index.json
validation_report.json
tiles/<tile_id>/pdl_0.2.ply
tiles/<tile_id>/pdl_0.4.ply
tiles/<tile_id>/pdl_0.6.ply
tiles/<tile_id>/pdl_0.8.ply
tiles/<tile_id>/pdl_1.0.ply
```

空 tile 不生成任何 PLY 文件，仅在 `frame_1051_tile_index.json` 中记录 `is_empty = true`、`point_count = 0`、`asset_status = not_generated_empty` 和空的 `quality_assets`。

## 3. PDL=1.0 byte-exact copy policy

本阶段研究者已确认：新 multi-PDL root 中每个非空 tile 的 `pdl_1.0.ply` 必须逐字节复制阶段 1A baseline root 中对应 tile 的 `pdl_1.0.ply`。

因此，本阶段的 `PDL = 1.0` 文件不是重新从原始 ASCII PLY 切块生成，也不是重新序列化生成。metadata 中记录其 provenance：

```text
provenance_kind = byte_exact_copy_of_stage1a_baseline
```

validator 已确认新 root 中 40 个 `PDL = 1.0` 文件与 baseline 对应文件的 SHA-256 和完整文件字节均一致。

## 4. 低 PDL 生成规则

低 PDL 资产使用阶段 1C 冻结的 sampling profile：

```text
sampling_profile_id = longdress_1051_g128_tilelocal_pdl5_v1
sampling_scope = tile_local
base_seed = 20260530
```

每个非空 tile 的 source point set 是 baseline `PDL = 1.0` PLY 中的点记录集合与记录顺序。seed identity 仅包含：

```text
sampling_profile_id
dataset_id
frame_id
grid_profile_id
tile_id
```

`target_pdl` / `quality_level` 不进入 seed identity。同一 tile 只生成一次确定性 Fisher-Yates permutation，低 PDL 使用该 permutation 的不同长度前缀；写出前将 selected source indices 升序排序，使输出记录保持 source tile PLY 的相对顺序。

目标点数规则：

```text
p < 1.0: retained_point_count = max(1, floor(N * p))
p = 1.0: retained_point_count = N
```

低 PDL 资产的 provenance 是：

```text
derived_adaptation_of_calibration_sampling_rule
```

它们不是 tile-level calibrated visual-quality evidence，不是 isolated-tile visual calibration，也不是 decoder latency 或网络开销测量。

## 5. 实际执行命令

本阶段实际执行并通过的四个验收命令为：

```powershell
python scripts\validate_tilelocal_sampling_reference.py --sampling-profile "configs\pilot_sampling_profile.longdress_1051_g128_tilelocal_pdl5_v1.json" --reference-vectors "tests\fixtures\tilelocal_sampling_reference_vectors.json"
```

```powershell
python scripts\validate_pilot_binary_tiles.py --raw-root "E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply" --frame-id 1051 --grid-profile "configs\pilot_grid_profile.longdress_1051_g128_raw_v1.json" --artifact-dir "artifacts\pilot_1051_g128_raw_v1"
```

```powershell
python scripts\generate_pilot_multquality_binary_tiles.py
```

```powershell
python scripts\validate_pilot_multquality_binary_tiles.py
```

生成脚本第一次在受限执行环境中完成 staging 内容写入后，发布目录 rename 遇到 Windows `Access denied`。该失败发生在正式 target root 发布前，失败 staging 已清理；随后同一生成命令成功发布正式 root，并由独立 validator 完整验证通过。

## 6. 实际生成数量

实际 source frame：

```text
dataset = 8i Longdress
frame_id = 1051
source_file = longdress_vox10_1051.ply
source_vertex_count = 765821
```

实际生成结果：

| 项目 | 数量 |
| --- | ---: |
| theoretical tile count | 128 |
| non-empty tile count | 40 |
| empty tile count | 88 |
| generated PLY file count | 200 |
| generated low-PDL PLY file count | 160 |
| generated PDL=1.0 copy count | 40 |

按 PDL 汇总的输出点数：

| PDL | total output point count |
| --- | ---: |
| 0.2 | 153148 |
| 0.4 | 306313 |
| 0.6 | 459477 |
| 0.8 | 612642 |
| 1.0 | 765821 |

这些点数是生成资产的文件级统计，不是 `r_bytes`、`d_ms`、端到端网络开销或 decode-time 指标。

## 7. metadata 与 provenance 边界

`frame_1051_tile_index.json` 覆盖全部 128 个 theoretical grid cells。每个非空 tile 的每个 PDL asset 记录至少包含：

```text
sampling_profile_id
sampling_scope
dataset_id
frame_id
grid_profile_id
tile_id
target_pdl
source_point_count
retained_point_count
actual_retained_ratio
base_seed
seed_identity
derived_quality_seed
sampling_method
permutation_algorithm
source_order_policy
nested_group_id
relative_path
file_size_bytes
sha256
provenance_kind
```

其中：

```text
actual_retained_ratio = retained_point_count / source_point_count
nested_group_id = seed_identity
```

`file_size_bytes` 和 `sha256` 是生成文件的 measured records；不得将它们写为 `r_bytes`、`d_ms`、decoder latency 或网络开销。

## 8. 独立验证结果

`scripts/validate_pilot_multquality_binary_tiles.py` 已独立验证并通过以下核心不变量：

- 40 个非空 tile 均恰有五个 PLY：`0.2 / 0.4 / 0.6 / 0.8 / 1.0`。
- 88 个空 tile 均不生成 PLY，metadata 中记录为空 tile。
- 新 root 的每个 `PDL = 1.0` 文件与 baseline 对应文件逐字节一致，SHA-256 一致。
- 每个 PLY 均为 `binary_little_endian 1.0`，schema 为 `float x/y/z` 与 `uchar red/green/blue`。
- 每个低 PDL 文件的 retained point count 等于 `max(1, floor(N*p))`。
- `PDL = 1.0` 的 retained point count 等于 source point count，`actual_retained_ratio = 1.0`。
- 所有 PDL 的 `actual_retained_ratio` 与 `retained_point_count / source_point_count` 一致。
- 同一 tile 内满足 `0.2 subset 0.4 subset 0.6 subset 0.8 subset 1.0`。
- 低 PDL selected source indices 与独立推导的 permutation prefix 完全一致，输出 source indices 严格升序。
- 每条写出的 binary point record 与 source `PDL = 1.0` 中对应 source index 的 record 完全一致。
- metadata 中的 profile id、seed identity、derived seed、target PDL、retained counts、actual ratio、relative path、SHA-256 与 provenance 均与实际文件及独立推导结果一致。
- 不存在未记录 PLY、未知 PDL、重复 asset record、不存在的 tile id、空 tile 资产、metadata 指向不存在文件或文件未被 metadata 记录。

验证报告：

```text
artifacts/pilot_1051_g128_tilelocal_pdl5_v1/validation_report.json
```

## 9. 当前明确未做的内容

阶段 1D 未生成或未冻结以下内容：

- Draco DRC；
- BIN；
- 播放器 XML / DASH 风格自定义资源清单；
- 正式 asset catalog schema；
- Stage2Input JSON；
- 多帧或全序列资产；
- GoF 聚合；
- `r_bytes` 正式映射；
- `d_ms` benchmark、derived estimate 或 proxy；
- `visibility`、`screen_area`、`distance_norm`、`p_sal` 等运行时字段。

## 10. 对下一阶段的建议

下一阶段建议先审阅 frame 1051 五档 binary PLY 的文件级统计、metadata 与可加载性，再选择受控后续方向，例如：

- 对 frame 1051 五档 PLY 做可视化或播放器加载 sanity check；
- 在不冻结正式 asset catalog 的前提下，整理轻量 metadata 字段候选；
- 讨论 Draco encoder 版本、参数和验证口径；
- 明确 Stage2Input 与 player manifest XML 是否、何时消费这些 pilot 资产。

在研究者确认前，不应直接进入 DRC 编码、XML 生成、Stage2Input 生成或多帧批处理。
