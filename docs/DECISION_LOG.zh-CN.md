# 数据准备决策记录

| 编号 | 主题 | 状态 | 简短结论 |
|---|---|---|---|
| D0B-1 | pilot source frame | RESOLVED_USER_CONFIRMED | 第一轮真实资产 pilot 使用 Longdress `longdress_vox10_1051.ply`，`frame_id = 1051`。 |
| D0B-2 | fixed shared spatial grid direction | DIRECTION_CONFIRMED_DETAILS_PENDING | 新管线采用全序列共享固定空间网格方向，但具体网格细节未冻结。 |
| D0B-3 | quality level set | RESOLVED_USER_CONFIRMED | PDL 集合为 `{0.2, 0.4, 0.6, 0.8, 1.0}`，其中 `1.0` 为完整点集。 |
| D0B-4 | binary PLY and DRC asset chain | RESOLVED_USER_CONFIRMED | 新中间资产使用 binary little-endian PLY，DRC 由对应质量档位 binary PLY 生成。 |
| D0B-5 | empty tile asset rule | RESOLVED_USER_CONFIRMED | 空 tile 不生成实际 binary PLY 或 DRC，但必须在元数据中记录。 |
| D0B-6 | DASH-style player manifest direction | DIRECTION_CONFIRMED_DETAILS_PENDING | 后续需要 DASH 风格自定义播放器资源清单 XML，但 schema 与消费契约未冻结。 |
| D0B-7 | old asset and mentor script reuse boundary | RESOLVED_USER_CONFIRMED | 旧资产和导师脚本仅作静态参考，不整体复用、不直接运行。 |
| D0B-8 | project state document maintenance rule | RESOLVED_USER_CONFIRMED | 后续每阶段结束必须更新项目状态文档，决策变化同步更新决策日志。 |
| D0D-1 | G128 single-frame pilot provisional grid profile | RESOLVED_USER_CONFIRMED | `G128 = 4 x 8 x 4` 仅作为 Longdress frame 1051 单帧 pilot 的 provisional grid profile。 |
| D1A-1 | frame 1051 pilot fixed raw-coordinate grid profile | RESOLVED_USER_CONFIRMED | `longdress_raw_g128_fullseq_pilot_v1` 已冻结为 frame 1051 pilot 的真实资产生成 profile。 |
| D1A-2 | frame 1051 PDL=1.0 binary PLY baseline asset scope | RESOLVED_USER_CONFIRMED | 阶段 1A 只生成 frame 1051 非空 tile 的 `PDL = 1.0` binary PLY baseline。 |
| D1B-1 | low-PDL sampling traceability and pending selection | SUPERSEDED_BY_D1C | 阶段 1B 完成采样追溯；最终规则已由 D1C-1 到 D1C-5 冻结。 |
| D1C-1 | tile-local low-PDL sampling scope | RESOLVED_USER_CONFIRMED | 正式 low-PDL 资产生成采用 tile-local sampling，不采用 frame-global sampling 后再切块作为默认路径。 |
| D1C-2 | seeded nested permutation prefix sampling | RESOLVED_USER_CONFIRMED | 同一 tile 内使用同一 seeded Fisher-Yates permutation，不同 PDL 使用不同长度前缀并保持嵌套。 |
| D1C-3 | tile identity based seed derivation | RESOLVED_USER_CONFIRMED | base seed 为 `20260530`，seed identity 由 sampling profile、dataset、frame、grid profile 与 tile id 派生；PDL 不参与。 |
| D1C-4 | target point count and source-order rule | RESOLVED_USER_CONFIRMED | `p<1` 使用 `max(1, floor(N*p))`，`p=1` 使用全部 N 点，输出按 source index 升序。 |
| D1C-5 | target PDL and actual retained ratio metadata rule | RESOLVED_USER_CONFIRMED | metadata 必须同时记录 `target_pdl` 与 `actual_retained_ratio`。 |
| D1D-1 | multi-PDL root PDL=1.0 baseline copy policy | RESOLVED_USER_CONFIRMED | 阶段 1D multi-PDL root 中的 `PDL = 1.0` PLY 必须逐字节复制阶段 1A baseline。 |
| D2A-1 | composite DRC delivery candidate semantics | RESOLVED_USER_CONFIRMED | PDL 是 source point-density axis；后续 delivery candidate 为 source_pdl 与 Draco profile 组成的 composite representation variant，BIN 当前排除。 |
| D2B-1 | Draco round-trip point-order and RGB validation semantics | RESOLVED_USER_CONFIRMED | decoded point order 不作为 DRC delivery 正确性不变量；round-trip 使用 order-independent geometry、RGB multiset 与高置信空间对应 RGB 检查。 |

## D0B-1 pilot source frame

- 决策编号：D0B-1
- 主题：第一轮单帧 pilot 源帧
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 0A 已确认原始 Longdress 目录存在 300 个 ASCII PLY，帧号 1051 到 1350 连续。
- 已确认内容：第一轮真实资产 pilot 选用 `dataset = 8i Longdress`、`source frame = longdress_vox10_1051.ply`、`frame_id = 1051`。
- 未确认边界：该决定不代表后续实验只使用这一帧，也不代表当前开始处理该帧。
- 对后续实现的影响：下一阶段可围绕 frame 1051 做 grid probe 与消费契约静态审查，但不能直接批量生成资产。
- 对论文或实验表述的影响：只能表述为第一轮 pilot 源帧选择，不能表述为完整实验数据集范围。

## D0B-2 fixed shared spatial grid direction

- 决策编号：D0B-2
- 主题：固定共享空间网格方向
- 状态：DIRECTION_CONFIRMED_DETAILS_PENDING
- 背景：Stage2 需要跨帧可比较的空间质量分配对象，旧 12-cell 切块粒度和语义仍不足以作为新管线最终规则。
- 已确认内容：后续新数据准备管线采用全序列共享、固定的空间坐标网格；不为每一帧按自身 bounding box 重新定义 tile；同一 `tile_id` 在不同帧中应代表同一固定空间区域；tile 是均匀空间划分，不是人体语义分割。
- 未确认边界：最终 `Nx × Ny × Nz`、grid origin、全序列空间包络计算规则、cell size、边界归属、`tile_id` 编码格式和工作性 vertical axis 尚未冻结。
- 对后续实现的影响：实现前必须先进行 frame 1051 的 grid probe 和小规模验证，不能在本阶段写死网格维度或物理米单位。
- 对论文或实验表述的影响：可以表述为空间稳定 tile 方向已确认，但不能宣称最终网格参数已确定。

## D0B-3 quality level set

- 决策编号：D0B-3
- 主题：质量档位集合
- 状态：RESOLVED_USER_CONFIRMED
- 背景：Stage2 需要离散质量档位供预算分配选择。
- 已确认内容：新数据准备项目保留五个点密度质量档位 `PDL = {0.2, 0.4, 0.6, 0.8, 1.0}`；`PDL = 1.0` 表示该 tile 的完整原始点集，不进行降采样。
- 未确认边界：低 PDL 的采样算法、是否嵌套降采样、随机种子、确定性排序规则、点数取整规则，以及 PDL 记录目标比例还是实际保留比例尚未冻结。
- 对后续实现的影响：可以围绕五档质量设计文档和试验计划，但不得实现或承诺具体采样方法。
- 对论文或实验表述的影响：可以说明离散 PDL 集合已由研究者确认；不能把旧目录中的 `0.8/0.6/0.4` 自动等同于新 PDL 语义。

## D0B-4 binary PLY and DRC asset chain

- 决策编号：D0B-4
- 主题：binary PLY 与 DRC 资产链
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 0A 与研究者补充说明表明，早期 ASCII tile PLY 路径不是新 pipeline 的正式复用目标。
- 已确认内容：后续新管线的中间点云资产只使用 binary little-endian PLY；资产链为原始 Longdress ASCII PLY -> 切块 binary tile PLY -> 各 quality level binary PLY -> 对应 DRC；DRC 必须由对应质量档位的 binary PLY 生成。
- 未确认边界：Draco encoder 版本、命令或调用方式、geometry quantization、color quantization、compression level、量化误差规则和解码验证规则尚未冻结。
- 对后续实现的影响：后续实现不需要为早期 ASCII tile PLY 路径建立正式兼容逻辑，也不得直接复用旧 Draco 参数。
- 对论文或实验表述的影响：可以表述新资产链方向；不能声称已经确定 Draco profile 或完成编码。

## D0B-5 empty tile asset rule

- 决策编号：D0B-5
- 主题：空 tile 资产规则
- 状态：RESOLVED_USER_CONFIRMED
- 背景：固定 grid universe 下，某些帧中会存在没有点的 tile。
- 已确认内容：空 tile 不生成实际 binary PLY 文件，不生成实际 DRC 文件；后续帧级或资产级元数据必须记录 `tile_id`、`is_empty = true`、`point_count = 0`、`asset_status = not_generated_empty` 等信息。
- 未确认边界：空 tile 是否进入未来 Stage2Input、是否进入播放器 XML、路径字段采用 `null`、缺省还是其他形式尚未冻结。
- 对后续实现的影响：不得把空 tile 写成零字节候选资产，也不得假设 solver 的最终处理方式。
- 对论文或实验表述的影响：可说明空 tile 作为元数据状态表达，而不是生成实际传输资产。

## D0B-6 DASH-style player manifest direction

- 决策编号：D0B-6
- 主题：DASH 风格自定义播放器资源清单方向
- 状态：DIRECTION_CONFIRMED_DETAILS_PENDING
- 背景：旧 `video_1.xml` 具有 DASH 风格组织元素，但阶段 0A 已确认其不是以标准 `MPD` 为根，也未验证完整 MPEG-DASH 规范兼容性。
- 已确认内容：新项目需要保留播放器资源描述层；新 XML 可以参考旧 XML 的 `AdaptationSet`、`Representation`、`SegmentTemplate` 等组织思想；准确表述为 DASH 风格自定义播放器资源清单 XML。
- 未确认边界：新 XML 具体字段、目录模板、资源路径规则、播放器兼容条件和消费契约尚未冻结。
- 对后续实现的影响：下一阶段应做播放器 XML 消费契约静态审查，不应直接生成完整 XML。
- 对论文或实验表述的影响：不能把未来 XML 与播放器兼容误写为已确认 XML schema，也不能把旧 `video_1.xml` 写成严格标准 MPEG-DASH MPD。

## D0B-7 old asset and mentor script reuse boundary

- 决策编号：D0B-7
- 主题：旧资产和导师脚本复用边界
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 0A 发现旧资产、旧 XML 和导师脚本包存在可参考证据，同时也存在未确认语义、硬编码路径和生成/删除风险。
- 已确认内容：`A1_ply/A2_drc` 属于早期 ASCII PLY 路径相关资产，不作为新 pipeline 正式复用目标；`A3_ply_binary` 可作为 binary PLY 目录组织和资产关系参考；`A5_drc_binary` 可作为 DRC 目录组织和资源对应关系参考；`A4_bin_binary` 当前不作为新数据准备 pipeline 优先复刻对象；`video_1.xml` 是旧 DASH 风格自定义播放器资源清单参考，不是新项目强制模板。导师脚本包仅作为静态参考资产，不整体复用，不直接运行。
- 未确认边界：旧资产具体生成 profile、旧参数、旧播放器消费逻辑和旧脚本实际执行路径仍未确认。
- 对后续实现的影响：后续只重点关注切块、binary PLY 转换、质量版本、Draco 编码和必要元数据生成相关逻辑，且需要重新设计可复现新管线。
- 对论文或实验表述的影响：旧资产可作为历史参考和审查证据，不能自动写成本项目正式实验资产。

## D0B-8 project state document maintenance rule

- 决策编号：D0B-8
- 主题：项目状态文档维护规则
- 状态：RESOLVED_USER_CONFIRMED
- 背景：本项目会跨阶段、跨对话、跨协作者推进，需要稳定的交接入口。
- 已确认内容：每次后续阶段任务完成后必须更新 `PROJECT_STATE_CURRENT.zh-CN.md`；若新增或修改研究者确认的决策，必须同步更新 `DECISION_LOG.zh-CN.md`；只有数据准备边界、资产语义、provenance 规则或核心输入输出契约发生变化时，才更新 `DATA_PREP_CONTRACT.zh-CN.md`；所有项目说明文档仅维护中文版本。
- 未确认边界：具体阶段编号和未来文档拆分方式可随项目推进调整。
- 对后续实现的影响：任何实现或审查任务收尾时都应检查是否需要更新状态、决策或契约。
- 对论文或实验表述的影响：文档记录将作为实验资产语义与决策依据的可追溯来源。

## D0D-1 G128 single-frame pilot provisional grid profile

- 决策编号：D0D-1
- 主题：G128 单帧 pilot provisional grid profile
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 0C 已比较 G54 与 G128 在少量帧 provisional envelope 下对 frame 1051 的占用情况。研究者随后确认先以 G128 作为单帧 pilot 的 provisional grid profile，并要求阶段 0D 对完整 Longdress 序列进行 raw-coordinate envelope 与 occupancy 验证。
- 已确认内容：`G128 = 4 x 8 x 4`，仅作为 `longdress_vox10_1051.ply` / frame 1051 单帧 pilot 的 provisional grid profile。
- 未确认边界：全序列正式 envelope、正式 grid origin、正式 cell_size、正式 `tile_id`、正式边界规则、是否适用于全序列正式资产生成均未冻结。
- 对后续实现的影响：可以围绕 G128 做全序列 raw-coordinate occupancy 验证和单帧 pilot 准备；在研究者审阅并确认前，不能将 G128 写成正式最终 grid，也不能启动正式切块或批量资产生成。
- 对论文或实验表述的影响：可以表述为 pilot 阶段的 provisional grid profile 已由研究者确认；不能表述为最终实验网格参数或全序列正式资产网格已确定。

## D1A-1 frame 1051 pilot fixed raw-coordinate grid profile

- 决策编号：D1A-1
- 主题：frame 1051 pilot fixed raw-coordinate grid profile
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 0D 已完成 Longdress 1051-1350 全 300 帧 raw-coordinate envelope 扫描，完整 envelope 为 `(0, 0, 0)` 到 `(481, 1023, 660)`。研究者随后确认阶段 1A 使用该 envelope 派生的 G128 profile 生成 frame 1051 pilot baseline。
- 已确认内容：`profile_id = longdress_raw_g128_fullseq_pilot_v1`，`grid_origin = (0, 0, 0)`，`grid_max = (481, 1023, 660)`，`grid_dimensions = 4 x 8 x 4`，`cell_size = (120.25, 127.875, 165)`，`tile_id_format = gx_<ix>_gy_<iy>_gz_<iz>`，边界规则为每轴 `[min, max)` 且坐标恰好等于全局 max 时归入最后一个 cell。
- 未确认边界：该决定只冻结 frame 1051 pilot 的 grid profile；不自动等于全序列最终 grid、官方世界坐标、物理米制网格或最优实验网格。低 PDL 采样、Draco profile、XML schema、Stage2Input 字段仍未冻结。
- 对后续实现的影响：阶段 1A 可以据此对 frame 1051 执行受控空间分块并生成 `PDL = 1.0` binary PLY baseline；不得据此启动批量帧资产或低 PDL / DRC / XML 生成。
- 对论文或实验表述的影响：可以表述为 frame 1051 pilot baseline 的固定 raw-coordinate grid profile；不能表述为最终全序列实验 grid 已确定。

## D1A-2 frame 1051 PDL=1.0 binary PLY baseline asset scope

- 决策编号：D1A-2
- 主题：frame 1051 `PDL = 1.0` binary PLY baseline asset scope
- 状态：RESOLVED_USER_CONFIRMED
- 背景：`PDL = 1.0` 已由 D0B-3 确认为完整原始点集；阶段 1A 是首次真实单帧 pilot 资产生成，需保持范围足够窄并可验证。
- 已确认内容：阶段 1A 只生成 `longdress_vox10_1051.ply` 中非空 tile 的 `PDL = 1.0` binary little-endian PLY，记录 frame-level metadata，并运行独立验证脚本。空 tile 不生成实际 PLY 文件，只在 metadata 中记录。
- 未确认边界：`PDL = 0.2 / 0.4 / 0.6 / 0.8`、降采样算法、Draco DRC、BIN、XML、player manifest、正式 asset catalog、Stage2Input 和批量帧资产均不在阶段 1A 范围内。
- 对后续实现的影响：后续应先审阅 frame 1051 baseline 的分块统计与加载可行性，再冻结低 PDL 采样规则并生成多质量 binary PLY。
- 对论文或实验表述的影响：可表述为单帧 pilot 的 level-1 baseline 已生成并验证；不能表述为完整多质量资产集、完整压缩资产集或最终 Stage2 数据集已完成。

## D1B-1 low-PDL sampling traceability and pending selection

- 决策编号：D1B-1
- 主题：低 PDL 采样语义追溯与待决选择
- 状态：SUPERSEDED_BY_D1C
- 背景：阶段 1A 已完成 frame 1051 的 `PDL = 1.0` binary PLY baseline；进入低 PDL 资产生成前，需要追溯既有 `pcv-distance-quality-calibration` 中 `PDL = {0.2, 0.4, 0.6, 0.8}` 的真实采样语义，并判断其是否适合迁移到 tile-local pipeline。
- 已获得的 calibration / legacy evidence：calibration 正式渲染路径使用 `buildNestedQualityGeometry`，对完整 PLY 的 Three.js geometry 使用 seeded permutation prefix sampling；点数规则为 `Math.max(1, Math.floor(sourcePointCount * qualityLevel))`；配置 seed 为 `20260530`，实际 `quality_seed` 由 source path 派生；正式 run 是 full-cloud rendering evidence，不是 isolated tile calibration。旧 A3 binary 质量组点数比例接近 `0.8/0.6/0.4`，但有限内容检查未支持逐级嵌套。
- 后续状态：阶段 1C 已由研究者确认最终 low-PDL 采样规则；本条作为阶段 1B 追溯记录保留，实际执行以 D1C-1 至 D1C-5 为准。
- tile-local 与 frame-global 的取舍：tile-local 更适合 Stage2 的 tile-level independent candidate semantics，但属于 calibration 采样规则的 derived adaptation；frame-global 更接近 calibration 的 full-cloud scope，但每个 tile 的实际保留比例可能偏离目标 PDL。
- 对后续实现的影响：后续实现不得回到 D1B 的待决状态；必须按 D1C 冻结规则创建多质量 binary PLY，并独立验证 nested property、点数比例和属性保真。
- 对论文或实验表述的影响：可以将既有 calibration 表述为 full-cloud distance-quality calibrated evidence；tile-local 低 PDL 资产若采用同类算法，只能表述为 derived adaptation，不能写成 tile-level calibrated PDL。

## D1C-1 tile-local low-PDL sampling scope

- 决策编号：D1C-1
- 主题：tile-local low-PDL 采样作用域
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 1B 比较了 frame-global sampling 后再切块与 tile-local sampling。Stage2 将 tile 视为独立质量候选对象，因此需要让每个非空 tile 的低 PDL 候选具有清晰的 tile-local 语义。
- 已确认内容：正式 low-PDL 资产生成采用 `tile-local sampling`。每个非空 tile 的 `PDL = 1.0` binary PLY 是该 tile 的 source point set，`PDL = 0.2 / 0.4 / 0.6 / 0.8` 均在 tile 内独立生成。不采用 frame-global sampling 后再切块作为当前默认正式路径。
- 未确认边界：未来可将 frame-global sampling 作为额外对照或敏感性分析，但不属于当前正式 pipeline；是否推广到多帧或全序列仍待后续阶段确认。
- 对实现的影响：下一阶段的多质量 PLY 生成脚本必须以每个非空 tile 的 `PDL = 1.0` PLY 为输入单位，不得先对完整 frame 采样再切块。
- 对论文与实验表述的影响：tile-local 低 PDL 资产是 calibration sampling rule 的 tile-local derived adaptation，不是 tile-level calibrated quality evidence。

## D1C-2 seeded nested permutation prefix sampling

- 决策编号：D1C-2
- 主题：seeded nested permutation prefix sampling
- 状态：RESOLVED_USER_CONFIRMED
- 背景：calibration 正式渲染路径使用 seeded Fisher-Yates permutation，并对不同 quality level 使用同一 permutation 的不同长度前缀。该语义可迁移为 tile-local 采样规则。
- 已确认内容：同一非空 tile 内，对 `PDL = 1.0` source point index 生成一次确定性 Fisher-Yates permutation；低 PDL 使用该 permutation 的不同长度前缀；选中的 source indices 在写出前按升序排序。必须满足 `0.2 subset 0.4 subset 0.6 subset 0.8 subset 1.0`。
- 未确认边界：本决策不生成真实 PLY，也不验证视觉质量；未来实现仍需验证二进制 PLY 属性保真。
- 对实现的影响：不得为不同 PDL 独立重新 shuffle；同一 tile 的所有低 PDL 必须共享一个 permutation。
- 对论文与实验表述的影响：可表述为确定性嵌套采样规则已冻结；不能表述为完成 tile-level visual calibration。

## D1C-3 tile identity based seed derivation

- 决策编号：D1C-3
- 主题：基于 tile identity 的 seed 派生规则
- 状态：RESOLVED_USER_CONFIRMED
- 背景：calibration 的 `seedForSource` 使用 base seed 与完整 PLY 相对路径派生 quality seed。当前 pipeline 的 source unit 改为 tile，因此需要稳定 tile identity。
- 已确认内容：base seed 固定为 `20260530`。每个非空 tile 的 permutation seed 由 `sampling_profile_id`、`dataset_id`、`frame_id`、`grid_profile_id`、`tile_id` 派生。`target_pdl` / `quality_level` 不参与 seed identity 或 seed derivation。
- 未确认边界：新 tile seed 不要求、也不得声称与 calibration 中完整 frame PLY 的 `quality_seed` 数值相同。
- 对实现的影响：同一 tile 的所有 PDL 必须共享同一个 derived quality seed；seed identity 不能包含 PDL、输出文件名、生成时间戳、绝对本地路径或随机 UUID。
- 对论文与实验表述的影响：应表述为 derived adaptation of calibration seedForSource semantics，而不是直接复用 full-cloud source path seed。

## D1C-4 target point count and source-order rule

- 决策编号：D1C-4
- 主题：目标点数与 source-order 输出规则
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 1B 已确认 calibration 使用 `Math.max(1, Math.floor(sourcePointCount * qualityLevel))`，且 selected indices 在输出前升序排序。
- 已确认内容：对非空 tile，`p < 1.0` 时 `n_p = max(1, floor(N*p))`；`p = 1.0` 时 `n_p = N`。输出点记录必须按 source tile PLY 的相对顺序写出，即 selected source indices 升序。
- 未确认边界：本决策不定义坐标、颜色属性写出实现，也不定义 DRC 或 XML。
- 对实现的影响：不得按三维坐标排序、不得按颜色排序、不得按 permutation 顺序写出、不得在输出时随机重排。
- 对论文与实验表述的影响：可说明 target PDL 是目标比例；小 tile 因最小保底可能产生高于目标的 actual ratio。

## D1C-5 target PDL and actual retained ratio metadata rule

- 决策编号：D1C-5
- 主题：target PDL 与 actual retained ratio metadata 规则
- 状态：RESOLVED_USER_CONFIRMED
- 背景：小 tile 使用 `max(1, floor(N*p))` 时，实际保留比例可能不等于 target PDL，需要在 metadata 中避免歧义。
- 已确认内容：未来每个非空 tile、每个 PDL 的 metadata 必须至少记录 `sampling_profile_id`、`sampling_scope`、`dataset_id`、`frame_id`、`grid_profile_id`、`tile_id`、`target_pdl`、`source_point_count`、`retained_point_count`、`actual_retained_ratio`、`base_seed`、`seed_identity`、`derived_quality_seed`、`sampling_method`、`permutation_algorithm`、`source_order_policy`、`nested_group_id` 和 `provenance`。必须同时记录 `target_pdl` 与 `actual_retained_ratio`。
- 未确认边界：正式 asset catalog schema 与 Stage2Input 字段仍未冻结。
- 对实现的影响：metadata 不得只记录 PDL 标签；若实际比例高于 target PDL，必须如实记录。
- 对论文与实验表述的影响：`actual_retained_ratio` 是 derived ratio，不是 decoder latency、端到端网络开销或 tile-level 主观质量阈值。

## D1D-1 multi-PDL root PDL=1.0 baseline copy policy

- 决策编号：D1D-1
- 主题：multi-PDL root 中 `PDL = 1.0` 的 baseline 逐字节复制策略
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 1A 已生成并独立验证 frame 1051、G128、40 个非空 tile 的 `PDL = 1.0` binary PLY baseline。阶段 1D 在新的 multi-PDL root 中生成五档 binary PLY 时，需要避免重新切块或重新序列化 `PDL = 1.0` 导致 provenance 与字节级可追溯性变复杂。
- 已确认内容：阶段 1D 的 `artifacts/pilot_1051_g128_tilelocal_pdl5_v1/` 中，每个非空 tile 的 `pdl_1.0.ply` 必须逐字节复制阶段 1A baseline root 中对应 tile 的 `pdl_1.0.ply`。metadata 中必须记录 `provenance_kind = byte_exact_copy_of_stage1a_baseline`，并保留 baseline root、baseline tile identity 与 baseline SHA-256 等来源信息。
- 未确认边界：本决策不冻结 Draco DRC 生成、XML schema、正式 asset catalog schema、Stage2Input 字段、多帧或全序列资产范围，也不改变 D1C-1 至 D1C-5 已冻结的低 PDL sampling semantics。
- 对实现的影响：生成脚本不得从原始 ASCII PLY 重新生成 multi-PDL root 中的 `PDL = 1.0` 文件，不得重新序列化或改写其 header、record order、浮点表示或颜色值；验证脚本必须逐字节确认 multi-PDL root 的 `PDL = 1.0` 文件与 baseline 对应文件一致。
- 对论文与实验表述的影响：可以将阶段 1D 的 `PDL = 1.0` 资产表述为阶段 1A baseline 的 byte-exact copy；低 PDL 资产仍是 calibration sampling rule 的 tile-local derived adaptation，不是 tile-level calibrated visual-quality evidence。该决策不意味着已经完成 DRC、播放器 XML、Stage2Input 或批量实验。

## D2A-1 composite DRC delivery candidate semantics

- 决策编号：D2A-1
- 主题：Stage2 delivery representation candidate 的资产语义与当前编码范围
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 1D 已生成 frame 1051 的五档 binary PLY source assets，但这些 PLY 只是 source/reference/round-trip baseline，不应继续被表述为最终 Stage2 delivery quality candidate space。后续真实 delivery candidate 需要结合 source point-density 与 Draco codec profile。
- 已确认内容：`PDL` 当前定位为 `source_pdl`，仅表示 tile-local nested sampling 后的 source point-density axis。后续 Stage2 delivery candidate 是 composite representation variant，其逻辑 identity 至少包含 `dataset_id`、`frame_id`、`grid_profile_id`、`tile_id`、`source_pdl`、`codec_id = draco`、point-cloud mode、`cl` 与 `qp`。当前 active pilot candidate family 为：`source_pdl ∈ {0.2,0.4,0.6,0.8,1.0}`、`codec = Draco`、point-cloud mode required、`cl = 10`、`qp ∈ {8,10,12}`。阶段 2A 曾记录的 `qc=6` 保留为历史 candidate family 说明；阶段 2B.1 后，`qc` 不进入当前 active variant identity、file name、generation command 或 metadata。对每个非空 tile，后续预期 DRC candidate 数为 `5 × 3 = 15`；frame 1051 的 40 个非空 tile 对应后续完整 pilot corpus 预计为 `600` 个 DRC 文件。PLY 用于 source/reference/round-trip validation baseline；DRC 是后续 delivery representation candidate；BIN 当前项目范围明确排除。
- 未确认边界：全量 actual encoding success、全量 round-trip fidelity、DRC file bytes、decode cost `D(i,v)`、DRC-aware `Q_base(i,v)`、Pareto pruning、lookup projection 和 solver-side variant-aware contract 均未确认。当前 CLI help 确认 `-point_cloud`、`-cl` 与 `-qp` 可观察；RGB compression-control / color quantization CLI 属于 future investigation。
- 对实现的影响：后续 DRC corpus 不应按 PLY-only distance lookup 预先删减，应先保留完整 pilot candidate family 进入受控 round-trip probe 与后续 corpus 生成。metadata 必须能追溯 source PLY、`source_pdl`、Draco profile 与 encoder provenance。
- 对论文与实验表述的影响：可以表述为 data-prep 侧已冻结第一版 composite DRC candidate family；不能表述为已生成 DRC corpus、已验证 codec profile、已获得 `R(i,v)` / `D(i,v)` / `Q_base(i,v)` evidence 或已完成 solver-side lookup/pruning contract。

## D2B-1 Draco round-trip point-order and RGB validation semantics

- 决策编号：D2B-1
- 主题：Draco round-trip 的 point-order 与 RGB 验证语义
- 状态：RESOLVED_USER_CONFIRMED
- 背景：阶段 2B 的真实 Draco probe 已完成 2 个代表性非空 tile、5 个 `source_pdl`、3 个 `qp` 的 30 个 DRC 与 30 个 decoded PLY。旧 validator 将 decoded PLY record order 作为硬性不变量，并按相同 point index 比较 RGB；实际 Draco point-cloud decode 可以重排点记录，因此该旧 contract 不能作为 delivery asset 正确性条件。
- 已确认内容：decoded point order 不要求保留；point order 不作为 DRC delivery asset 的正确性不变量。geometry 使用 order-independent bidirectional point-set validation。RGB 必须满足 exact triplet multiset preservation；对高置信 mutual-nearest spatial correspondence 点对，RGB 必须 exact match。无 point identity 条件下的 ambiguity 必须记录，不得被过度表述为全局逐点绑定证明。
- 当前 active codec variant 说明：阶段 2B/2B.1 的实际 probe 使用 `source_pdl × qp`，`cl = 10` 固定，`qp ∈ {8,10,12}`；当前 native encoder help 未暴露 `-qc`，因此 `qc` 不进入当前 variant identity、file name、generation command 或 metadata 作为已生效参数。RGB compression-control / color quantization CLI 属于 future investigation。
- 未确认边界：本决策不证明所有量化碰撞或空间歧义区域的 color-to-geometry identity；不完成 RGB compression-control 研究；不生成全量 600 DRC corpus；不测得 target-side `D(i,v)` 或 DRC-aware `Q_base(i,v)`；不冻结 lookup projection、Pareto pruning 或 Stage2 solver contract。
- 对实现的影响：Draco round-trip validator 不得再用同 index 比较作为失败条件；必须验证 decoded vertex count、PLY schema、双向几何点集 fidelity、RGB multiset、high-confidence local RGB association、provenance 与 `qp` effect。若出现 geometry point-set、RGB multiset、provenance 或 `qp` effect 失败，仍必须以非零状态失败。
- 对论文与实验表述的影响：可以表述为阶段 2B.1 在 order-independent validation contract 下确认当前 30-variant probe 的几何点集与 RGB 值保真；不能表述为 Draco 保留 point order、qc 已验证、颜色压缩机制已优化、所有歧义点的颜色-几何绑定均已无条件证明，或已完成最终 DRC corpus / Stage2 evidence。
