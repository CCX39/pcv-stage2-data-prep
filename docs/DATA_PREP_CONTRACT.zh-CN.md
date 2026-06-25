# Stage2 数据准备项目契约

> 阶段 2A 更新：本阶段不生成 DRC，只冻结当前数据准备侧的 composite DRC representation 语义、Draco pilot candidate family 与 Stage2 理论接口交接边界。

## 1. 项目目的与范围

本仓库服务于 Work1 Stage2 的真实数据准备与资产元数据工作。Stage2 的目标是在 Stage1 给定 `Budget_total` 后，为每个空间 tile 选择离散质量档位；本仓库未来负责提供可追溯的 tile 级多质量候选资产、资产元数据和后续 pilot 所需证据。

阶段 2A 仅进行文档与只读 CLI 事实确认，不执行 PLY -> DRC 编码、DRC -> PLY 解码、round-trip verification、DRC 文件大小测量、decode-cost benchmark、XML 生成、正式 asset catalog 生成、Stage2Input 生成或批量帧资产生成。

## 2. 当前已确认的数据准备方向

### 已确认

- 第一轮真实资产 pilot 源帧为 8i Longdress 的 `longdress_vox10_1051.ply`，`frame_id = 1051`。该决定只冻结第一轮 pilot 的源帧。
- `longdress_raw_g128_fullseq_pilot_v1` 已冻结为 frame 1051 pilot 的 fixed raw-coordinate grid profile；该决定不等于全序列正式最终 grid 已冻结。
- 新数据准备项目保留五个点密度质量档位：`PDL = {0.2, 0.4, 0.6, 0.8, 1.0}`。
- `PDL = 1.0` 表示该 tile 的完整原始点集，不进行降采样。
- 后续新管线的中间点云资产只使用 `binary little-endian PLY`。
- DRC 必须由对应质量档位的 binary PLY 生成。
- 理论 grid universe 中某帧为空的 tile 不生成实际 binary PLY 文件，也不生成实际 DRC 文件。
- 阶段 1A 只生成 frame 1051 非空 tile 的 `PDL = 1.0` binary little-endian PLY baseline。
- 阶段 1C 冻结 `longdress_1051_g128_tilelocal_pdl5_v1` sampling profile：低 PDL 采用 tile-local deterministic seeded permutation prefix sampling。
- base seed 固定为 `20260530`，seed identity 字段为 `sampling_profile_id`、`dataset_id`、`frame_id`、`grid_profile_id`、`tile_id`；`target_pdl` / `quality_level` 不参与 seed identity。
- `p < 1.0` 时目标点数为 `max(1, floor(N*p))`，`p = 1.0` 时使用全部 `N` 点。
- 同一 tile 内必须满足 nested property，并按 source index 升序输出。
- metadata 必须同时记录 `target_pdl` 与 `actual_retained_ratio`。
- 阶段 1D 的 multi-PDL pilot root 中，`PDL = 1.0` 必须逐字节复制阶段 1A baseline；低 PDL 资产是 calibration sampling rule 的 tile-local derived adaptation。
- PDL 当前定位为 `source_pdl`，即 tile-local nested sampling 后的 source point-density axis；它不是最终 Stage2 delivery candidate 的唯一离散质量轴。
- 后续 Stage2 delivery representation candidate 应记录为 composite representation variant，其逻辑 identity 至少包含 `dataset_id`、`frame_id`、`grid_profile_id`、`tile_id`、`source_pdl`、`codec_id = draco`、point-cloud mode、`cl`、`qc` 与 `qp`。
- 当前第一版 DRC raw candidate family 为：`source_pdl ∈ {0.2,0.4,0.6,0.8,1.0}`、`codec = Draco`、point-cloud mode required、`cl = 10`、`qc = 6`、`qp ∈ {8,10,12}`。该 family 是研究者确认的 pilot candidate family，尚未完成实际编码、round-trip fidelity、R/D/Q evidence 或最优性验证。

### 当前方向但未冻结细节

- 新数据准备管线采用全序列共享、固定的空间坐标网格；同一 `tile_id` 在不同帧中应代表同一个固定空间区域。
- tile 采用均匀空间划分，不采用人体语义分割。
- 目标是获得比旧 12-cell 切块更细的空间粒度，使 Stage2 具有更有意义的空间质量分配对象。
- 后续需要生成与现有播放器兼容的、参考旧组织思想的 DASH 风格自定义播放器资源清单 XML。

### 尚未决定

- 最终网格维度 `Nx × Ny × Nz`、grid origin、全序列空间包络计算规则、cell size、边界归属规则、`tile_id` 编码格式和工作性 vertical axis。
- Draco encoder 版本、命令或调用方式、geometry quantization、color quantization、compression level、误差容忍规则和 DRC 解码验证规则。
- 新 XML 的具体字段、目录模板、资源路径规则和播放器兼容条件。

## 3. 资产类型与语义边界

后续资产链方向为：

```text
原始 Longdress ASCII PLY
-> 切块后生成 binary little-endian tile PLY
-> 针对每个 quality level 的 binary PLY
-> 对应生成 Draco DRC 资产
```

原始 Longdress ASCII PLY 是外部输入资产，不进入 Git。新项目不为早期 ASCII tile PLY 路径建立兼容性或正式生成逻辑。

旧资产只能作为历史参考或目录关系参考，不能自动视为新项目的正式实验资产。旧目录名中的 `0.8`、`0.6`、`0.4`、`qp`、`qc`、`cl` 等字符串不得直接写成已证实的 PDL 或 Draco 参数。

阶段 1D 的五档 binary PLY pilot root 是真实文件级 pilot 资产集合，但不是正式 asset catalog，不是 Stage2Input，也不是播放器 XML 或 DRC 资产包。该 root 中的 file size 与 SHA-256 是 measured file records；点数、文件大小与实际保留比例不得写成 decoder latency、端到端网络开销或 tile-level visual quality threshold。

当前 delivery asset 路线为：

```text
binary PLY -> DRC
```

binary PLY 是 source asset、Draco encoding input、round-trip validation reference，也可作为 uncompressed experimental baseline；但不默认作为正常 Stage2 delivery candidate。DRC 是后续实际 delivery representation candidate。BIN 当前项目范围明确排除，不进行 PLY/DRC 的 BIN 二次打包；旧项目与导师脚本中的 BIN 流程仅为 historical static reference。

## 4. 空 tile 与跨帧 tile identity 原则

### 已确认

- 新管线采用全序列共享、固定的空间坐标网格方向。
- 不为每一帧按自身 bounding box 重新定义 tile。
- 同一 `tile_id` 在不同帧中应代表同一个固定空间区域。
- 对于理论 grid universe 中存在、但某一帧内没有点的 tile，不生成实际 binary PLY 或 DRC 文件。

### 当前方向但未冻结细节

后续元数据必须明确记录空 tile 信息，例如：

```text
tile_id
is_empty = true
point_count = 0
asset_status = not_generated_empty
```

### 尚未决定

- 空 tile 是否进入未来正式 Stage2Input。
- 空 tile 是否进入播放器 XML，以及采用何种表达方式。
- 空 tile 的路径字段是 `null`、缺省还是其他形式。
- solver 中如何最终处理空 tile。

## 5. 质量版本与编码资产原则

### 已确认

- PDL 集合为 `{0.2, 0.4, 0.6, 0.8, 1.0}`。
- `PDL = 1.0` 表示完整原始点集。
- 新中间资产采用 binary little-endian tile PLY。
- DRC 由对应质量档位的 binary PLY 生成。
- 低 PDL 采用 tile-local deterministic seeded permutation prefix sampling。
- 同一非空 tile 内不同 PDL 共享同一个 derived quality seed 与 Fisher-Yates permutation。
- `target_pdl` / `quality_level` 不进入 seed identity。
- `p < 1.0` 使用 `max(1, floor(N*p))`；`p = 1.0` 使用全部 `N` 点。
- 输出点记录按 source tile PLY 的相对顺序写出。
- metadata 必须同时记录 `target_pdl` 和 `actual_retained_ratio`。
- 在阶段 1D multi-PDL root 中，`PDL = 1.0` 采用 `byte_exact_copy_of_stage1a_baseline` provenance；低 PDL 采用 `derived_adaptation_of_calibration_sampling_rule` provenance。
- 后续每个 DRC candidate 的 asset metadata 必须至少能追溯 `source_pdl`、codec、point-cloud mode、`cl`、`qc`、`qp`、source binary PLY、encoder executable 或 profile provenance。

### 当前方向但未冻结细节

- DRC 文件字节数未来可作为生成资产的 measured 文件尺寸，用于 `r_bytes` 候选口径之一。
- 该字节数不等于真实端到端网络传输总开销。

### 尚未决定

- Draco 参数、版本、量化误差和验证规则。
- `d_ms` 是真实 benchmark、derived estimate 还是 proxy。

## 6. manifest、asset catalog 与 Stage2Input 的职责分离

后续至少区分以下三类文件或数据层：

```text
asset catalog / asset metadata
player manifest XML
Stage2Input JSON
```

- asset catalog / asset metadata 负责记录资产存在性、点数、文件尺寸、bbox、center、provenance、生成 profile 等可追溯信息。
- player manifest XML 是 DASH 风格自定义播放器资源清单，可参考旧 XML 的 `AdaptationSet`、`Representation`、`SegmentTemplate` 组织思想。
- Stage2Input JSON 面向 Stage2 solver 或实验管线，不应与播放器资源清单强行合并。

当前不冻结 XML tag/schema、目录模板或 Stage2Input 字段。新 XML 不应承担全部数据准备、provenance 与运行时 Stage2 决策输入三种职责。

data-prep 不预先把 PLY-only distance lookup 当作 DRC candidate hard filter。DRC corpus 生成应保留完整 pilot candidate family，后续 solver-side 再决定 lookup projection、candidate filtering 与 Pareto pruning。

## 7. provenance 与术语边界

本项目必须区分以下术语：

- `measured`：由实际文件、实际运行或实际测量直接得到。原始文件实际字节数、实际点数、生成后 DRC 文件实际字节数可属于 measured。
- `calibrated`：经过标定过程建立的数值或模型输出。
- `derived`：由已有 measured 或 confirmed 信息按明确规则计算得到。tile bbox、tile center、tile point count、tile-to-camera distance 等通常属于 derived。
- `proxy`：为实验或工程近似采用的替代指标，必须明确标注不能等同真实测量。
- `synthetic`：人工构造或模拟生成的数据。

未来 DRC 文件字节数可以是对生成资产的 measured 文件尺寸，但不等于真实端到端网络传输总开销。点数、PLY 文件大小或 DRC 文件大小不等于真实 decoder latency。未经 benchmark 的 `d_ms` 不得写成 measured。

旧资产和未来新资产必须区分 provenance 与生成 profile，不能把 proxy、derived 或 synthetic 数据写成 measured 数据。

阶段 1D 的低 PDL tile-local 资产仅继承经过追溯并冻结的 sampling algorithm semantics；它们不是 tile-level calibrated visual-quality evidence。现有 calibrated evidence 仍来自完整 Longdress 点云的 full-cloud rendering 条件。

## 8. 当前明确不做的内容

当前阶段不做以下工作：

- 不生成 DRC、BIN、XML、player manifest、正式 asset catalog 或 Stage2Input。
- 不生成其他 frame 或全序列资产。
- 不运行导师脚本、旧播放器或任何 Draco 实际编码/解码命令；无输入 help/version 审查只用于记录 CLI 事实。
- 不把 frame 1051 pilot profile 写成官方世界坐标、物理米制网格、最优 grid 或最终全序列实验 grid。
- 不冻结 Draco 参数。
- 不冻结 XML tag/schema。
- 不修改 `pcv-stage2-allocation` 或 `pcv-distance-quality-calibration`。
- 不整体复用导师脚本包，不直接运行旧脚本。
- 不创建英文版重复文档。
- 不将 PLY-only distance lookup 直接写成 composite DRC variant hard cap。

## 9. 未冻结决策清单

1. 最终 tile grid 维度、origin、空间包络、cell size、边界归属和 `tile_id` 编码。
2. 工作性 vertical axis 与 Longdress 坐标尺度解释。
3. Draco encoder 版本、调用方式、量化参数、压缩等级和解码验证。
4. asset catalog、player manifest XML 与 Stage2Input 的具体字段和互相关联方式。
5. 空 tile 是否进入 Stage2Input 或播放器 XML。
6. `r_bytes`、`d_ms` 与相机相关字段的正式口径。
7. 是否将阶段 1A 的 frame 1051 pilot profile 推广到后续少量帧验证或全序列实验资产。
8. tile-local low-PDL 资产生成后的可视化加载 sanity check 范围。
9. composite DRC variants 的 `Q_base(i,v)`、`R(i,v)`、`D(i,v)` evidence 与 solver-side lookup projection / Pareto pruning 规则。

## 10. 文档维护规则

- 每次后续阶段任务完成后，必须更新 `docs/PROJECT_STATE_CURRENT.zh-CN.md`。
- 若本阶段新增或修改研究者确认的决策，必须同步更新 `docs/DECISION_LOG.zh-CN.md`。
- 只有数据准备边界、资产语义、provenance 规则或核心输入输出契约发生变化时，才更新 `docs/DATA_PREP_CONTRACT.zh-CN.md`。
- 所有项目说明文档仅维护中文版本，无需专门创建英文对应文件。
