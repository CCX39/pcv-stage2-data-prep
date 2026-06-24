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
| D1B-1 | low-PDL sampling traceability and pending selection | PENDING_USER_DECISION | 已追溯 low-PDL 采样证据，但最终采样作用域、嵌套、seed 与取整规则仍待研究者确认。 |

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
- 状态：PENDING_USER_DECISION
- 背景：阶段 1A 已完成 frame 1051 的 `PDL = 1.0` binary PLY baseline；进入低 PDL 资产生成前，需要追溯既有 `pcv-distance-quality-calibration` 中 `PDL = {0.2, 0.4, 0.6, 0.8}` 的真实采样语义，并判断其是否适合迁移到 tile-local pipeline。
- 已获得的 calibration / legacy evidence：calibration 正式渲染路径使用 `buildNestedQualityGeometry`，对完整 PLY 的 Three.js geometry 使用 seeded permutation prefix sampling；点数规则为 `Math.max(1, Math.floor(sourcePointCount * qualityLevel))`；配置 seed 为 `20260530`，实际 `quality_seed` 由 source path 派生；正式 run 是 full-cloud rendering evidence，不是 isolated tile calibration。旧 A3 binary 质量组点数比例接近 `0.8/0.6/0.4`，但有限内容检查未支持逐级嵌套。
- 尚未由研究者确认的最终采样规则：是否采用 tile-local 或 frame-global；是否强制 nested property；seed 如何由 frame/tile/profile 派生；小 tile 是否使用 `max(1, floor(N * p))`；是否同时记录 target PDL 与 actual retained ratio。
- tile-local 与 frame-global 的取舍：tile-local 更适合 Stage2 的 tile-level independent candidate semantics，但属于 calibration 采样规则的 derived adaptation；frame-global 更接近 calibration 的 full-cloud scope，但每个 tile 的实际保留比例可能偏离目标 PDL。
- 对后续实现的影响：下一阶段在研究者确认前不得直接生成 `PDL = 0.2 / 0.4 / 0.6 / 0.8` 资产；确认后应只对 frame 1051 非空 tile 生成多质量 binary PLY，并独立验证 nested property、点数比例和属性保真。
- 对论文或实验表述的影响：可以将既有 calibration 表述为 full-cloud distance-quality calibrated evidence；tile-local 低 PDL 资产若采用同类算法，只能表述为 derived adaptation，不能写成 tile-level calibrated PDL。
