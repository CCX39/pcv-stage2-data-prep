# Stage2 数据准备项目契约

> 阶段 0D 更新：本阶段允许对完整 Longdress 序列进行受控、只读的 raw-coordinate envelope 与 occupancy 扫描，用于验证 provisional G128 profile；仍禁止正式切块、点云格式转换、质量版本生成、Draco 编码、XML 生成、asset catalog 生成和 Stage2Input 生成。

## 1. 项目目的与范围

本仓库服务于 Work1 Stage2 的真实数据准备与资产元数据工作。Stage2 的目标是在 Stage1 给定 `Budget_total` 后，为每个空间 tile 选择离散质量档位；本仓库未来负责提供可追溯的 tile 级多质量候选资产、资产元数据和后续 pilot 所需证据。

阶段 0D 允许对完整 Longdress 序列进行受控、只读的 raw-coordinate envelope 与 occupancy 扫描，用于验证 provisional G128 profile；仍禁止正式切块、点云格式转换、质量版本生成、Draco 编码、XML 生成、asset catalog 生成和 Stage2Input 生成。

## 2. 当前已确认的数据准备方向

### 已确认

- 第一轮真实资产 pilot 源帧为 8i Longdress 的 `longdress_vox10_1051.ply`，`frame_id = 1051`。该决定只冻结第一轮 pilot 的源帧。
- `G128 = 4 x 8 x 4` 已确认为 frame 1051 单帧 pilot 的 provisional grid profile；该决定不等于全序列正式最终 grid 已冻结。
- 新数据准备项目保留五个点密度质量档位：`PDL = {0.2, 0.4, 0.6, 0.8, 1.0}`。
- `PDL = 1.0` 表示该 tile 的完整原始点集，不进行降采样。
- 后续新管线的中间点云资产只使用 `binary little-endian PLY`。
- DRC 必须由对应质量档位的 binary PLY 生成。
- 理论 grid universe 中某帧为空的 tile 不生成实际 binary PLY 文件，也不生成实际 DRC 文件。

### 当前方向但未冻结细节

- 新数据准备管线采用全序列共享、固定的空间坐标网格；同一 `tile_id` 在不同帧中应代表同一个固定空间区域。
- tile 采用均匀空间划分，不采用人体语义分割。
- 目标是获得比旧 12-cell 切块更细的空间粒度，使 Stage2 具有更有意义的空间质量分配对象。
- 后续需要生成与现有播放器兼容的、参考旧组织思想的 DASH 风格自定义播放器资源清单 XML。

### 尚未决定

- 最终网格维度 `Nx × Ny × Nz`、grid origin、全序列空间包络计算规则、cell size、边界归属规则、`tile_id` 编码格式和工作性 vertical axis。
- 低 PDL 的具体采样算法、是否采用嵌套降采样、随机种子、确定性排序规则、点数取整规则，以及 PDL 记录目标比例还是实际保留比例。
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

### 当前方向但未冻结细节

- DRC 文件字节数未来可作为生成资产的 measured 文件尺寸，用于 `r_bytes` 候选口径之一。
- 该字节数不等于真实端到端网络传输总开销。

### 尚未决定

- 低 PDL 采样算法、嵌套关系、随机性与确定性规则。
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

## 7. provenance 与术语边界

本项目必须区分以下术语：

- `measured`：由实际文件、实际运行或实际测量直接得到。原始文件实际字节数、实际点数、生成后 DRC 文件实际字节数可属于 measured。
- `calibrated`：经过标定过程建立的数值或模型输出。
- `derived`：由已有 measured 或 confirmed 信息按明确规则计算得到。tile bbox、tile center、tile point count、tile-to-camera distance 等通常属于 derived。
- `proxy`：为实验或工程近似采用的替代指标，必须明确标注不能等同真实测量。
- `synthetic`：人工构造或模拟生成的数据。

未来 DRC 文件字节数可以是对生成资产的 measured 文件尺寸，但不等于真实端到端网络传输总开销。点数、PLY 文件大小或 DRC 文件大小不等于真实 decoder latency。未经 benchmark 的 `d_ms` 不得写成 measured。

旧资产和未来新资产必须区分 provenance 与生成 profile，不能把 proxy、derived 或 synthetic 数据写成 measured 数据。

## 8. 当前明确不做的内容

当前阶段不做以下工作：

- 不复制、切块、转换或保存正式点云资产。
- 不生成 binary PLY、DRC、BIN、XML、JSON manifest、asset catalog 或 Stage2Input。
- 不运行导师脚本、旧播放器、Draco encoder 或 decoder。
- 不设计、实现或冻结最终 grid；阶段 0D 的全序列 envelope 与 occupancy 扫描仅限受控、只读、provisional 证据收集。
- 不冻结具体 `Nx × Ny × Nz`。
- 不冻结 Draco 参数。
- 不冻结 XML tag/schema。
- 不修改 `pcv-stage2-allocation` 或 `pcv-distance-quality-calibration`。
- 不整体复用导师脚本包，不直接运行旧脚本。
- 不创建英文版重复文档。

## 9. 未冻结决策清单

1. 最终 tile grid 维度、origin、空间包络、cell size、边界归属和 `tile_id` 编码。
2. 工作性 vertical axis 与 Longdress 坐标尺度解释。
3. 低 PDL 采样算法、嵌套降采样、随机种子、确定性排序和点数取整。
4. Draco encoder 版本、调用方式、量化参数、压缩等级和解码验证。
5. asset catalog、player manifest XML 与 Stage2Input 的具体字段和互相关联方式。
6. 空 tile 是否进入 Stage2Input 或播放器 XML。
7. `r_bytes`、`d_ms` 与相机相关字段的正式口径。
8. 基于阶段 0D 全序列 envelope 与 G128 occupancy 结果的正式 pilot grid profile 审阅、调整与冻结流程。

## 10. 文档维护规则

- 每次后续阶段任务完成后，必须更新 `docs/PROJECT_STATE_CURRENT.zh-CN.md`。
- 若本阶段新增或修改研究者确认的决策，必须同步更新 `docs/DECISION_LOG.zh-CN.md`。
- 只有数据准备边界、资产语义、provenance 规则或核心输入输出契约发生变化时，才更新 `docs/DATA_PREP_CONTRACT.zh-CN.md`。
- 所有项目说明文档仅维护中文版本，无需专门创建英文对应文件。
