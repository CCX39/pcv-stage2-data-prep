# Sampling Reference Validation 当前记录

## 1. 验证目的与不生成资产边界

本文记录阶段 1C 对 tile-local low-PDL sampling profile 的参考实现一致性验证。

本阶段验证的是 sampling rule 的确定性与内部一致性，不是点云视觉质量验证，不是 DRC 解码验证，不是播放器加载验证，也不是 tile-level calibration。

本阶段未读取真实 PLY，未生成任何 PLY、DRC、BIN、XML、asset catalog、Stage2Input 或批量帧资产。

## 2. calibration 参考语义

本阶段只读核对了 calibration 项目的以下文件：

```text
E:\Miunaaaa\0-work\code\pcv-distance-quality-calibration\src\web\renderer\nested-quality.js
E:\Miunaaaa\0-work\code\pcv-distance-quality-calibration\src\shared\utils\seeded-rng.mjs
E:\Miunaaaa\0-work\code\pcv-distance-quality-calibration\scripts\render_screenshots\index.mjs
```

代码直接证实的行为：

- `qualityLevel === 1` 时直接返回 source geometry。
- `p < 1.0` 时点数为 `Math.max(1, Math.floor(sourcePointCount * qualityLevel))`。
- `shuffledIndices(count, seed)` 使用 seeded RNG 与 Fisher-Yates shuffle。
- Fisher-Yates 从 `count - 1` 递减到 `1`。
- `swapIndex = Math.floor(random() * (index + 1))`。
- 选中 permutation prefix 后，`selected.sort((left, right) => left - right)`，即输出 source index 升序。
- `seedForSource` 将 base seed 与 source identity 混合为 deterministic quality seed。

## 3. 新 profile 的 derived adaptation 点

新 profile 保留 calibration 的以下采样语义：

- base seed 与稳定 source identity 派生 deterministic quality seed；
- seeded RNG；
- Fisher-Yates permutation；
- permutation prefix selection；
- selected source index ascending 输出顺序；
- `max(1, floor(N * p))` 目标点数规则。

新 profile 的 adaptation：

- calibration 的 source identity 是完整 PLY 相对路径；
- 本项目的 source identity 是稳定 tile identity；
- seed identity 字段固定为 `sampling_profile_id, dataset_id, frame_id, grid_profile_id, tile_id`；
- `target_pdl` / `quality_level` 不参与 seed identity。

该 adaptation 不声称新 tile seed 与 calibration 完整 frame PLY 的 `quality_seed` 数值一致。

## 4. reference vector 设计

固定 reference vectors 文件：

```text
tests/fixtures/tilelocal_sampling_reference_vectors.json
```

该文件不包含真实 PLY 数据，不代表真实点云资产，不代表视觉质量实验。

测试 case：

| case_id | N | 目的 |
| --- | ---: | --- |
| `small_tile_min_retention_N2` | 2 | 验证 `max(1, floor(N*p))` 对小 tile 的保底行为。 |
| `non_integer_ratio_tile_N17` | 17 | 验证非整比例下的 floor 规则、actual ratio 和 nested property。 |
| `larger_tile_permutation_N101` | 101 | 验证较大 index 集上的 Fisher-Yates、prefix selection 与输出顺序。 |

reference vector 来源：

```text
直接导入 calibration 的 src/shared/utils/seeded-rng.mjs 中 shuffledIndices；
seed identity 派生按 scripts/render_screenshots/index.mjs 中 seedForSource 语义转录；
未运行 calibration 正式实验。
```

## 5. Python 验证脚本运行命令

验证脚本：

```text
scripts/validate_tilelocal_sampling_reference.py
```

实际运行命令：

```powershell
python scripts\validate_tilelocal_sampling_reference.py `
  --sampling-profile "configs\pilot_sampling_profile.longdress_1051_g128_tilelocal_pdl5_v1.json" `
  --reference-vectors "tests\fixtures\tilelocal_sampling_reference_vectors.json"
```

运行结果：

```text
PASS: tile-local sampling reference validation succeeded for 3 case(s); profile=longdress_1051_g128_tilelocal_pdl5_v1
```

## 6. 各测试 case 的输入概览

| case_id | tile_id | source_point_count | expected_derived_quality_seed |
| --- | --- | ---: | ---: |
| `small_tile_min_retention_N2` | `gx_0_gy_0_gz_0` | 2 | 2039635627 |
| `non_integer_ratio_tile_N17` | `gx_1_gy_2_gz_0` | 17 | 1448106842 |
| `larger_tile_permutation_N101` | `gx_2_gy_4_gz_1` | 101 | 359065722 |

## 7. seed / count / selected indices / nested property 验证结果

验证脚本检查并通过：

- `quality_levels` 恰为 `[0.2, 0.4, 0.6, 0.8, 1.0]`。
- `sampling_scope` 为 `tile_local`。
- `base_seed` 为 `20260530`。
- seed identity 按 profile 中固定字段顺序构造。
- seed identity 不包含 `target_pdl` 或 `quality_level` 字段。
- derived quality seed 与 reference vector 一致。
- `p = 1.0` 时 retained point count 等于 `N`。
- `p < 1.0` 时 retained point count 等于 `max(1, floor(N * p))`。
- 每个 PDL 输出 index 列表严格升序。
- 每个 index 均位于 `[0, N-1]`。
- 每个 PDL index 列表无重复。
- nested property 成立。
- `actual_retained_ratio = retained_point_count / N`。

## 8. 通过与失败条件

通过条件：

- profile 与 fixture 字段一致；
- 所有 expected seed、count、index set 和 ratio 均匹配；
- 所有 invariant 均成立。

失败条件：

- profile 或 fixture JSON 无法解析；
- quality levels、seed identity、derived seed、count、index 或 ratio 任一不一致；
- index 越界、重复、非升序；
- nested property 不成立。

验证脚本失败时返回非零状态，不跳过失败 vector，不静默修正 fixture。

## 9. 当前不能证明的事项

本阶段不能证明：

- tile-local PDL 的视觉质量阈值；
- isolated tile calibration；
- DRC 编码或解码行为；
- 播放器加载行为；
- `r_bytes` 或 `d_ms` 正式口径；
- 多质量 PLY 生成脚本的属性保真。

## 10. 对下一阶段的约束

下一阶段生成真实多质量 binary PLY 时必须使用：

- `configs/pilot_sampling_profile.longdress_1051_g128_tilelocal_pdl5_v1.json`；
- 同一 tile 内共享一个 derived quality seed；
- 同一 tile 内共享一个 permutation；
- `max(1, floor(N*p))` 目标点数规则；
- source index 升序输出规则；
- metadata 同时记录 `target_pdl` 与 `actual_retained_ratio`。

下一阶段仍不应生成 DRC、BIN、XML、asset catalog、Stage2Input 或批量帧资产，除非研究者另行确认阶段范围。
