# Pilot Tile-Local PDL Sampling Profile

## 1. 阶段目的与 profile scope

本文记录阶段 1C 冻结的 frame 1051 pilot low-PDL 采样契约。该契约用于后续在 `longdress_raw_g128_fullseq_pilot_v1` grid profile 下，对 frame 1051 的非空 tile 生成 five-level PDL binary PLY 资产。

版本化 profile：

```text
configs/pilot_sampling_profile.longdress_1051_g128_tilelocal_pdl5_v1.json
```

sampling profile id：

```text
longdress_1051_g128_tilelocal_pdl5_v1
```

scope 限定：

- 仅适用于当前 frame 1051、G128 pilot grid、非空 tile 的 five-level PDL 资产生成准备。
- 不自动等价于全序列最终采样 profile。
- 不定义 Draco 参数、XML schema、asset catalog schema 或 Stage2Input schema。
- 不构成 tile-level calibrated visual quality evidence。

## 2. 已冻结的五项研究者决策

### D1C-1：采样作用域

采用 `tile-local sampling`。每个非空 tile 的 `PDL = 1.0` binary PLY 是该 tile 的 source point set，`PDL = 0.2 / 0.4 / 0.6 / 0.8` 均在 tile 内独立生成。

不采用 frame-global sampling 后再切块作为当前正式资产生成路径。未来可将 frame-global sampling 作为额外对照或敏感性分析，但不属于当前正式 pipeline。

### D1C-2：低 PDL 采样算法与嵌套性

采用 deterministic seeded permutation prefix sampling。同一个非空 tile 内只生成一次确定性 Fisher-Yates permutation，各低 PDL 使用同一 permutation 的不同长度前缀。

必须满足：

```text
PDL 0.2 subset PDL 0.4 subset PDL 0.6 subset PDL 0.8 subset PDL 1.0
```

### D1C-3：seed 与稳定身份派生规则

基础 seed 固定为：

```text
20260530
```

每个非空 tile 的 permutation seed 由以下稳定身份字段派生：

```text
sampling_profile_id
dataset_id
frame_id
grid_profile_id
tile_id
```

`target_pdl` 或 `quality_level` 不得作为 seed identity 字段。这样同一个 tile 的所有 PDL 共享同一个 permutation。

### D1C-4：目标点数、最小保底与输出顺序

对于非空 tile：

```text
N = PDL=1.0 source point count
p = target PDL
```

目标点数：

```text
p < 1.0: n_p = max(1, floor(N * p))
p = 1.0: n_p = N
```

输出顺序：

```text
先由 permutation prefix 决定 selected set；
再将 selected source indices 升序排序；
最后按 source tile PLY 的原始相对顺序写出记录。
```

### D1C-5：metadata 与实际保留比例记录

未来每个非空 tile、每个 PDL 的 metadata 必须同时记录：

```text
target_pdl
actual_retained_ratio
```

其中：

```text
actual_retained_ratio = retained_point_count / source_point_count
```

对于小 tile，若 `max(1, floor(N * p))` 导致实际比例高于 target PDL，metadata 必须如实记录，不得伪装为严格等于 target PDL。

## 3. PDL 质量层级集合与 PDL=1.0 语义

质量层级集合冻结为：

```text
[0.2, 0.4, 0.6, 0.8, 1.0]
```

`PDL = 1.0` 表示该 tile 的完整 source point set，不采样、不 shuffle、不重排序、不去重、不量化、不裁剪、不应用坐标变换。

## 4. tile-local sampling 的准确流程

伪代码级规则：

```text
for each non-empty tile:
    N = source PDL=1.0 tile point count
    seed_identity = canonical identity from profile fields
    quality_seed = derive(base_seed, seed_identity)
    permutation = FisherYates(indices 0..N-1, quality_seed)

    for p in [0.2, 0.4, 0.6, 0.8, 1.0]:
        if p == 1.0:
            retained = all source indices
        else:
            k = max(1, floor(N * p))
            retained = permutation[0:k]

        output_indices = sort_ascending(retained)
```

重要约束：

- 不同 PDL 不重新计算 seed。
- 不同 PDL 不重新执行独立 shuffle。
- `target_pdl` / `quality_level` 不进入 seed identity。
- 输出顺序不是 permutation 顺序，而是 source index 升序。

## 5. seed identity 与 derived quality seed 规则

seed identity 模板固定为：

```text
sampling_profile_id={sampling_profile_id}|dataset_id={dataset_id}|frame_id={frame_id}|grid_profile_id={grid_profile_id}|tile_id={tile_id}
```

规范化规则：

- 字段顺序固定为 `sampling_profile_id, dataset_id, frame_id, grid_profile_id, tile_id`。
- 字段之间使用 `|` 分隔。
- key 与 value 使用 `=` 分隔。
- 字符串按 UTF-8 编码。
- 模板中不允许额外空格。
- value 按 profile 或 tile metadata 中记录的大小写原样使用。

derived quality seed 规则采用 calibration `seedForSource` 语义的 tile identity adaptation：

```text
hash = base_seed as unsigned 32-bit integer
for each byte in UTF-8(seed_identity):
    hash = ((hash XOR byte) * 16777619) mod 2^32
derived_quality_seed = hash
```

该规则保留“基础 seed + 稳定 source identity -> deterministic quality seed”的机制，但 source identity 从 calibration 的完整 PLY 相对路径改为本项目稳定 tile identity。因此不得声称新 tile seed 与 calibration 中完整 frame PLY 的 `quality_seed` 数值相同。

不得使用以下内容作为 seed identity 组成部分：

- target PDL 或 quality level；
- 输出文件名；
- 生成时间戳；
- 本地绝对路径；
- 随机 UUID；
- 未来资产文件路径。

## 6. Fisher-Yates permutation 与 prefix selection

calibration 参考语义：

- RNG state 初始化为 `seed >>> 0`。
- 每次 random 调用先加 `0x6d2b79f5`，再执行 32-bit `Math.imul` 混合。
- Fisher-Yates 从 `count - 1` 递减到 `1`。
- `swapIndex = floor(random() * (index + 1))`。

新项目 Python 参考实现按上述语义转录，并通过固定 reference vectors 验证。

## 7. source index ascending 输出顺序规则

每个 PDL 的 selected set 由 permutation prefix 决定，但实际输出前必须将 source indices 升序排序。

这表示输出 PLY 记录顺序保持 `PDL = 1.0` tile source 的相对顺序。不得按三维坐标排序、不得按颜色排序、不得按 permutation 顺序写出、不得在输出时随机重排。

## 8. target count、最小保底与 actual retained ratio

对于非空 tile，`p < 1.0` 时使用：

```text
max(1, floor(N * p))
```

这保证每个非空 tile 在低 PDL 下至少保留 1 个点。小 tile 的实际保留比例可能高于 target PDL，因此 metadata 必须记录：

```text
target_pdl
retained_point_count
source_point_count
actual_retained_ratio
```

## 9. nested property

同一 tile 内所有低 PDL 共享同一个 seed 和同一个 permutation，且每个 PDL 使用该 permutation 的不同长度前缀。因此在 index set 层面必须满足：

```text
0.2 subset 0.4 subset 0.6 subset 0.8 subset 1.0
```

后续多质量 PLY 生成必须独立验证该性质。

## 10. metadata 必填字段

未来每个非空 tile、每个 PDL 的 metadata 至少记录：

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
provenance
```

## 11. provenance 与 calibration 可比性边界

tile-local low-PDL assets 是 calibration sampling rule 的 tile-local derived adaptation。

它们不是：

- tile-level calibrated quality evidence；
- isolated tile visual calibration；
- decoder latency benchmark；
- 端到端网络开销测量。

现有 calibrated evidence 来自完整 Longdress 点云的 full-cloud rendering 条件。新 tile-local PDL 资产只继承经过追溯的 sampling algorithm semantics，不等价于重新完成 isolated tile visual calibration。

## 12. 当前明确不做的事项

阶段 1C 不生成：

- `PDL = 0.2 / 0.4 / 0.6 / 0.8` 的真实 tile PLY；
- DRC；
- BIN；
- XML 或播放器 manifest；
- asset catalog；
- Stage2Input；
- 多帧或全序列资产。

阶段 1C 也不运行 calibration 正式实验、导师脚本、旧播放器或 Draco 工具。

## 13. 与下一阶段多质量 binary PLY 生成的关系

下一阶段应在新的、独立 artifact root 中，仅对 frame 1051 的 40 个非空 tile 生成 five-level binary PLY，并验证：

- 每个 tile 内的 nested property；
- 每个 PDL 的 target count 与 actual retained ratio；
- 输出记录顺序；
- 坐标与 RGB 属性保真；
- 空 tile 不生成资产；
- metadata 中的 seed identity、derived quality seed 和 provenance。
