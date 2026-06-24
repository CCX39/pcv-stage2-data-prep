# 项目当前状态

## 1. 项目名称与研究上下文

项目名称：`pcv-stage2-data-prep`

本仓库服务于硕士课题 Work1 Stage2 的真实数据准备工作。Stage2 在 Stage1 给定 `Budget_total` 后，为每个空间 tile 选择离散质量档位。本项目未来需要提供可追溯的 tile 级多质量资产、资产元数据和 pilot 证据，但当前仍处于文档、契约与小规模验证准备阶段。

## 2. 项目职责与边界

本仓库负责记录数据准备契约、决策日志、当前状态、资产审查结论和后续 pilot 支持材料。未来可承载可复现的数据准备代码，但当前阶段不实现任何生成管线。

本仓库不修改 `pcv-stage2-allocation`、`pcv-distance-quality-calibration`、原始 Longdress 数据目录、旧处理结果目录或导师脚本包目录。原始点云、批量 tile PLY、DRC、BIN、缓存、日志和其他大体积资产不进入 Git。

## 3. 当前阶段

阶段 0D：全序列 raw-coordinate envelope 扫描与 G128 全序列占用验证

阶段 0D 已完成。本阶段完成了 Longdress 1051-1350 全 300 帧 raw-coordinate envelope 扫描与 G128 occupancy 验证；未实现正式切块，不生成正式 PLY、DRC、BIN、XML、manifest、asset catalog 或 Stage2Input，也未运行旧播放器、导师脚本或 Draco 工具。

## 4. 已完成工作

- 阶段 0A：原始 Longdress、旧处理结果、导师脚本包与旧 XML 的只读审查。
- 阶段 0A.1：研究者补录旧 DASH 风格资产组织、A1/A2 ASCII 路径弃用、binary PLY 优先等历史说明。
- 阶段 0B：已建立数据准备契约、决策日志和状态文档。
- 阶段 0C：已完成 frame 1051 为 pilot 的受控 raw-coordinate grid probe，并静态审查旧播放器对 DASH 风格自定义 XML 的消费路径。
- 阶段 0D：已完成 Longdress 全序列 raw-coordinate envelope 扫描，并在完整 envelope 下验证 G128 全序列 occupancy。

## 5. 当前已确认决策

- 第一轮真实资产 pilot 源帧为 8i Longdress 的 `longdress_vox10_1051.ply`，`frame_id = 1051`。
- 后续新数据准备管线采用全序列共享、固定的空间坐标网格方向。
- 新管线使用均匀空间划分，不采用人体语义分割。
- `G128 = 4 x 8 x 4` 已被研究者确认为 frame 1051 单帧 pilot 的 provisional grid profile；该决定不等于全序列正式最终 grid 已冻结。
- 新项目保留五个 PDL 档位：`{0.2, 0.4, 0.6, 0.8, 1.0}`，其中 `PDL = 1.0` 为完整原始点集。
- 新中间点云资产只使用 binary little-endian PLY。
- DRC 必须由对应质量档位的 binary PLY 生成。
- 空 tile 不生成实际 binary PLY 或 DRC，但必须在元数据中记录空 tile 状态。
- 后续需要 DASH 风格自定义播放器资源清单 XML，但其 schema 与消费契约尚未冻结。
- 旧资产和导师脚本包仅作静态参考，不整体复用、不直接运行。

## 6. 当前未确认或待冻结事项

- 最终网格维度 `Nx × Ny × Nz`、grid origin、全序列空间包络、cell size、边界归属规则和 `tile_id` 编码。
- 工作性 vertical axis 与 Longdress 坐标尺度解释。
- 低 PDL 采样算法、是否嵌套降采样、随机种子、确定性排序和点数取整规则。
- Draco encoder 版本、调用方式、几何量化、颜色量化、compression level、误差容忍和解码验证规则。
- 空 tile 是否进入 Stage2Input 或播放器 XML，以及路径字段表达方式。
- asset catalog / asset metadata、player manifest XML 与 Stage2Input JSON 的具体字段和关联规则。
- `r_bytes`、`d_ms`、visibility、screen_area、distance_norm 等字段的正式 provenance 和生成规则。

## 7. 已有资产与关键证据

- 原始 Longdress 数据目录：`E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply`。
- 原始目录中观察到 300 个 ASCII PLY，帧号 1051 到 1350 连续。
- 阶段 0A 代表性 header 显示原始 PLY 包含 `x/y/z` 与 RGB 字段，但坐标轴方向和物理尺度未确认。
- 旧处理结果目录：`E:\Miunaaaa\0-work\code\vv\pythonProject\static\data\video_data\video_1`。
- 旧目录包含 `A1_ply`、`A2_drc`、`A3_ply_binary`、`A4_bin_binary`、`A5_drc_binary` 等历史资产层级。
- 旧 `video_1.xml` 路径：`E:\Miunaaaa\0-work\code\vv\pythonProject\static\xml\video_1.xml`。
- 旧 XML 是 DASH 风格自定义播放器资源清单参考；它不是已验证的严格标准 MPEG-DASH MPD，也不是新项目强制模板。
- 阶段 0C 对 frames `1051, 1125, 1200, 1275, 1350` 完成 raw-coordinate bbox probe；5 帧 bbox 并集 provisional envelope 为 min `(27, 3, 22)`、max `(459, 1012, 570)`。
- 阶段 0C 对 frame 1051 的候选 profile 进行 occupancy probe：G54 有 25 个非空 tile，最大 tile point share 为 `0.121253`；G128 有 46 个非空 tile，最大 tile point share 为 `0.049999`。G54/G128 均只是候选 probe profile，最终 grid 尚未冻结。
- 阶段 0C 静态审查显示，旧后端 `app.py` 的 `/mpd/<video_id>` 只负责返回 `static/xml/<video_id>.xml`；`/gof_v10` 主要消费 JSON 字段 `video_id`、`gof_id`、`as_id`、`rep_id` 并按目录规则读取 A3/A4/A5 资产，未在后端直接解析 XML tag/attribute。
- 阶段 0D 完成 1051-1350 全 300 帧 raw-coordinate envelope 扫描；完整 envelope 为 min `(0, 0, 0)`、max `(481, 1023, 660)`，对应 derived provisional G128 `cell_size = (120.25, 127.875, 165)`。
- 阶段 0D 在完整 envelope 下验证 G128 occupancy：每帧 non-empty tile count 的 min / median / mean / max 为 `37 / 45 / 44.48 / 53`；128 个 theoretical tile 中有 20 个从未激活。
- 阶段 0D 中 frame 1051 在完整 envelope 下的 G128 non-empty tile count 为 `40`，maximum tile point share 为 `0.057920`。完整 envelope 与 cell_size 仍是 derived provisional 参数，尚需研究者审阅后才可考虑冻结正式 grid profile。
- 导师脚本包路径：`E:\Miunaaaa\0-work\code\MENTOR_SCRIPT_PACKAGE_vv_preprocess`。该脚本包仅作为静态参考资产。

## 8. 不可越过的边界

- 不复制、切块、转换或保存正式点云资产。
- 不生成 binary PLY、DRC、BIN、XML、JSON manifest、asset catalog 或 Stage2Input。
- 不运行导师脚本、旧播放器、Draco encoder 或 decoder。
- 不冻结具体 `Nx × Ny × Nz`。
- 不冻结 Draco 参数。
- 不冻结 XML tag/schema。
- 不修改阶段 0A 审查结论。
- 不把旧目录命名中的质量标签、Draco 参数或 XML 字段自动写成已证实事实。
- 不创建英文版重复文档。

## 9. 下一阶段建议

研究者应审阅阶段 0D 的全序列 envelope 与 G128 全序列占用结果，决定是否冻结正式 pilot grid profile。

下一阶段应优先回答：是否接受 full-sequence raw-coordinate envelope `(0, 0, 0)` 到 `(481, 1023, 660)`，是否接受 G128 full-sequence provisional `cell_size = (120.25, 127.875, 165)`，是否需要调整 grid 或边界规则，以及 never-active tile 在 metadata / player manifest XML / Stage2Input 中如何表达。

研究者确认后，再进入单帧正式切块与 level-1 binary PLY 基线生成准备。下一阶段仍不应直接批量生成多质量 PLY、批量 Draco 编码或完整 XML 生成。

## 10. 文档与仓库维护规则

- 每次后续阶段任务完成后，必须更新 `docs/PROJECT_STATE_CURRENT.zh-CN.md`。
- 若本阶段新增或修改研究者确认的决策，必须同步更新 `docs/DECISION_LOG.zh-CN.md`。
- 只有数据准备边界、资产语义、provenance 规则或核心输入输出契约发生变化时，才更新 `docs/DATA_PREP_CONTRACT.zh-CN.md`。
- 所有项目说明文档仅维护中文版本，无需专门创建英文对应文件。
- 提交前必须使用 `git diff` 和 `git status` 检查改动范围。
