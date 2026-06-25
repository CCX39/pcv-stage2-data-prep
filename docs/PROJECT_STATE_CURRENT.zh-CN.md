# 项目当前状态

## 1. 项目名称与研究上下文

项目名称：`pcv-stage2-data-prep`

本仓库服务于硕士课题 Work1 Stage2 的真实数据准备工作。Stage2 在 Stage1 给定 `Budget_total` 后，为每个空间 tile 选择离散质量档位。本项目未来需要提供可追溯的 tile 级多质量资产、资产元数据和 pilot 证据，但当前仍处于文档、契约与小规模验证准备阶段。

## 2. 项目职责与边界

本仓库负责记录数据准备契约、决策日志、当前状态、资产审查结论、probe 结果、单帧 pilot 生成代码和验证报告。

本仓库不修改 `pcv-stage2-allocation`、`pcv-distance-quality-calibration`、原始 Longdress 数据目录、旧处理结果目录或导师脚本包目录。原始点云、批量 tile PLY、DRC、BIN、缓存、日志和其他大体积资产不进入 Git。

阶段 1A 生成的 `PDL = 1.0` baseline 保存在 Git ignored 的 `artifacts/pilot_1051_g128_raw_v1/`。阶段 1D 生成的五档 binary PLY pilot 资产保存在 Git ignored 的 `artifacts/pilot_1051_g128_tilelocal_pdl5_v1/`。仓库仅提交生成代码、配置、验证代码和中文文档，不提交真实 PLY 资产。

## 3. 当前阶段

阶段 1D：frame 1051 五档 binary PLY 真实生成与完整验证

阶段 1A 已完成并验证 frame 1051 的 `PDL = 1.0` binary PLY baseline。

阶段 1B 已完成低 PDL 采样语义追溯与 tile-local 适配分析。

阶段 1B.1 已完成 README 文档导航与交接可读性维护。README 现作为仓库根目录的项目入口，集中说明项目定位、当前状态、推荐阅读顺序、文档职责、本地资产目录边界与 Git 协作方式。该阶段本身没有新增、修改或冻结任何研究决策；其后阶段 1C 已将 low-PDL 采样规则冻结为 D1C-1 至 D1C-5。

阶段 1C 已完成 tile-local low-PDL sampling profile 冻结与参考实现一致性验证：five-level PDL 规则已版本化，seed、nested property、count rounding、source-order policy 与 metadata 规则已明确，reference vectors 与独立验证脚本已通过。本阶段未生成 `PDL = 0.2 / 0.4 / 0.6 / 0.8` 的真实 tile PLY，未生成 DRC、BIN、XML、asset catalog、Stage2Input、多帧或全序列资产；未运行 calibration 正式实验、导师脚本、旧播放器或 Draco 工具。

阶段 1D 已完成 frame 1051、G128、40 个非空 tile 的五档 binary PLY 真实生成与完整验证。新 root `artifacts/pilot_1051_g128_tilelocal_pdl5_v1/` 覆盖 128 个 theoretical tile，其中 40 个非空 tile 各生成 `PDL = 0.2 / 0.4 / 0.6 / 0.8 / 1.0` 五个 binary little-endian PLY，88 个空 tile 不生成 PLY。`PDL = 1.0` 文件逐字节复制阶段 1A baseline，低 PDL 文件按阶段 1C sampling profile 生成并通过独立验证。本阶段未生成 DRC、BIN、XML、asset catalog、Stage2Input、多帧或全序列资产；未运行导师脚本、旧播放器、Draco 工具或 calibration 正式实验。

## 4. 已完成工作

- 阶段 0A：原始 Longdress、旧处理结果、导师脚本包与旧 XML 的只读审查。
- 阶段 0A.1：研究者补录旧 DASH 风格资产组织、A1/A2 ASCII 路径弃用、binary PLY 优先等历史说明。
- 阶段 0B：已建立数据准备契约、决策日志和状态文档。
- 阶段 0C：已完成 frame 1051 为 pilot 的受控 raw-coordinate grid probe，并静态审查旧播放器对 DASH 风格自定义 XML 的消费路径。
- 阶段 0D：已完成 Longdress 全序列 raw-coordinate envelope 扫描，并在完整 envelope 下验证 G128 全序列 occupancy。
- 阶段 1A：已完成 frame 1051 fixed-grid `PDL = 1.0` binary PLY baseline 生成与独立验证。
- 阶段 1B：已完成低 PDL 采样语义追溯、旧质量资产有限检查和 tile-local / frame-global 适配分析。
- 阶段 1B.1：已完成 README 文档导航与项目交接可读性维护。
- 阶段 1C：已完成 tile-local low-PDL sampling profile 冻结、reference vectors 创建和 Python 参考验证脚本一致性验证。
- 阶段 1D：已完成 frame 1051 五档 binary PLY pilot 资产生成与独立验证。

## 5. 当前已确认决策

- 第一轮真实资产 pilot 源帧为 8i Longdress 的 `longdress_vox10_1051.ply`，`frame_id = 1051`。
- 后续新数据准备管线采用全序列共享、固定的空间坐标网格方向。
- 新管线使用均匀空间划分，不采用人体语义分割。
- `longdress_raw_g128_fullseq_pilot_v1` 已冻结为 frame 1051 pilot 的 fixed raw-coordinate grid profile。
- 该 profile 使用 `grid_origin = (0, 0, 0)`、`grid_max = (481, 1023, 660)`、`grid_dimensions = 4 x 8 x 4`、`cell_size = (120.25, 127.875, 165)` 和 `tile_id_format = gx_<ix>_gy_<iy>_gz_<iz>`。
- 上述 profile 只冻结 frame 1051 pilot 真实资产生成规则，不等于全序列最终实验 grid、官方世界坐标或物理米制网格。
- 新项目保留五个 PDL 档位：`{0.2, 0.4, 0.6, 0.8, 1.0}`，其中 `PDL = 1.0` 为完整原始点集。
- 阶段 1A 只生成 frame 1051 非空 tile 的 `PDL = 1.0` binary little-endian PLY baseline。
- `longdress_1051_g128_tilelocal_pdl5_v1` 已冻结为 frame 1051 G128 pilot 的 tile-local low-PDL sampling profile。
- 低 PDL 采用 tile-local deterministic seeded permutation prefix sampling。
- base seed 固定为 `20260530`；seed identity 字段为 `sampling_profile_id`、`dataset_id`、`frame_id`、`grid_profile_id`、`tile_id`，`target_pdl` / `quality_level` 不参与 seed identity。
- `p < 1.0` 时 retained point count 为 `max(1, floor(N*p))`；`p = 1.0` 时使用全部 `N` 点。
- 同一 tile 内必须满足 `0.2 subset 0.4 subset 0.6 subset 0.8 subset 1.0`，输出点记录按 source tile PLY 相对顺序写出。
- metadata 必须同时记录 `target_pdl` 与 `actual_retained_ratio`。
- 阶段 1D 确认在 multi-PDL root 中，`PDL = 1.0` 必须逐字节复制阶段 1A baseline，不重新切块或重新序列化。
- calibration 正式低质量渲染使用 seeded nested prefix sampling；这是 full-cloud rendering evidence，不是 tile-level isolated calibration。阶段 1C 的 tile-local profile 是该采样规则的 derived adaptation。
- 新中间点云资产只使用 binary little-endian PLY。
- DRC 必须由对应质量档位的 binary PLY 生成。
- 空 tile 不生成实际 binary PLY 或 DRC，但必须在元数据中记录空 tile 状态。
- 后续需要 DASH 风格自定义播放器资源清单 XML，但其 schema 与消费契约尚未冻结。
- 旧资产和导师脚本包仅作静态参考，不整体复用、不直接运行。

## 6. 当前未确认或待冻结事项

- 是否将 `longdress_raw_g128_fullseq_pilot_v1` 推广为后续少量帧或全序列实验 grid。
- 工作性 vertical axis 与 Longdress 坐标尺度解释。
- Draco encoder 版本、调用方式、几何量化、颜色量化、compression level、误差容忍和解码验证规则。
- 空 tile 是否进入 Stage2Input 或播放器 XML，以及路径字段表达方式。
- asset catalog / asset metadata、player manifest XML 与 Stage2Input JSON 的具体字段和关联规则。
- `r_bytes`、`d_ms`、visibility、screen_area、distance_norm 等字段的正式 provenance 和生成规则。
- 是否将 frame 1051 tile-local sampling profile 推广到后续少量帧或全序列实验。
- frame 1051 五档 binary PLY 是否进入后续播放器加载 sanity check、Draco pilot 或轻量 metadata/catalog 设计。

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
- 阶段 0D 中 frame 1051 在完整 envelope 下的 G128 non-empty tile count 为 `40`，maximum tile point share 为 `0.057920`。这些结果已用于阶段 1A frame 1051 pilot profile，但不等于全序列最终实验 grid。
- 阶段 1A 使用 `configs/pilot_grid_profile.longdress_1051_g128_raw_v1.json` 生成 frame 1051 `PDL = 1.0` binary PLY baseline。
- 阶段 1A 生成资产本地目录：`artifacts/pilot_1051_g128_raw_v1/`。
- 阶段 1A source vertex count 为 `765821`；生成 binary PLY 文件数为 `40`；独立验证确认点数守恒、空 tile 无 PLY、所有输出 PLY 为 `binary_little_endian 1.0`，并确认 source / output canonical record digest 一致。
- 阶段 1B 追溯 `pcv-distance-quality-calibration`：正式 run 使用 `buildNestedQualityGeometry` 对完整 PLY geometry 做 seeded permutation prefix sampling；低质量点数规则为 `Math.max(1, Math.floor(sourcePointCount * qualityLevel))`。
- 阶段 1B 对旧 `GOF_1/A3_ply_binary/frame_0/cell_0` 质量组做有限只读检查：`R2_0.8` 是 `R1` 子集，但 `R3_0.6` 不是 `R2_0.8` 子集，`R4_0.4` 不是 `R3_0.6` 子集；旧质量资产不能用来冻结新 pipeline 的嵌套 PDL 语义。
- 阶段 1B.1 已将 `README.md` 更新为仓库根目录导航入口，覆盖项目定位、当前状态、推荐阅读顺序、文档职责、代码与本地资产边界、关键语义边界和 Git 协作规则。
- 阶段 1C 新增 sampling profile：`configs/pilot_sampling_profile.longdress_1051_g128_tilelocal_pdl5_v1.json`。
- 阶段 1C 新增参考验证脚本：`scripts/validate_tilelocal_sampling_reference.py`。
- 阶段 1C 新增 synthetic reference vectors：`tests/fixtures/tilelocal_sampling_reference_vectors.json`，不包含真实 PLY 数据或视觉质量证据。
- 阶段 1C 验证命令已通过：`python scripts\validate_tilelocal_sampling_reference.py --sampling-profile "configs\pilot_sampling_profile.longdress_1051_g128_tilelocal_pdl5_v1.json" --reference-vectors "tests\fixtures\tilelocal_sampling_reference_vectors.json"`。
- 阶段 1D 新增生成脚本：`scripts/generate_pilot_multquality_binary_tiles.py`。
- 阶段 1D 新增独立验证脚本：`scripts/validate_pilot_multquality_binary_tiles.py`。
- 阶段 1D 生成资产本地目录：`artifacts/pilot_1051_g128_tilelocal_pdl5_v1/`。
- 阶段 1D 生成结果：source vertex count 为 `765821`；128 个 theoretical tile 中 40 个非空、88 个空；生成 PLY 文件数为 `200`，其中低 PDL PLY 为 `160`，`PDL = 1.0` byte-exact baseline copy 为 `40`。
- 阶段 1D 按 PDL 汇总的输出点数为：`0.2 -> 153148`、`0.4 -> 306313`、`0.6 -> 459477`、`0.8 -> 612642`、`1.0 -> 765821`。
- 阶段 1D 验证命令已通过：`python scripts\validate_pilot_multquality_binary_tiles.py`。验证确认五档文件齐全、空 tile 无 PLY、`PDL = 1.0` 与 baseline 逐字节一致、低 PDL selected indices 与独立推导一致、nested property 成立、binary records 与 source records 完全一致、metadata 与实际文件一致。
- 导师脚本包路径：`E:\Miunaaaa\0-work\code\MENTOR_SCRIPT_PACKAGE_vv_preprocess`。该脚本包仅作为静态参考资产。

## 8. 不可越过的边界

- 不生成 DRC、BIN、XML、player manifest、正式 asset catalog 或 Stage2Input。
- 不生成其他 frame 或全序列资产，直到研究者确认下一阶段范围。
- 不运行导师脚本、旧播放器、Draco encoder 或 decoder。
- 不把 frame 1051 pilot profile 写成官方世界坐标、物理米制网格、最优 grid 或最终全序列实验 grid。
- 不冻结 Draco 参数。
- 不冻结 XML tag/schema。
- 不修改阶段 0A 审查结论。
- 不把旧目录命名中的质量标签、Draco 参数或 XML 字段自动写成已证实事实。
- 不创建英文版重复文档。

## 9. 下一阶段建议

下一阶段建议先审阅 frame 1051 五档 binary PLY pilot 资产的文件级统计、metadata、provenance 和可加载性，再选择受控后续方向。候选工作可以包括可视化或播放器加载 sanity check、轻量 metadata 字段候选整理、Draco encoder 版本与参数讨论，或明确 Stage2Input 与 player manifest XML 是否以及何时消费这些 pilot 资产。

下一阶段仍不应直接批量生成全序列资产、直接生成正式 DRC 批量资产、直接生成 XML、直接生成正式 asset catalog 或直接生成 Stage2Input，除非研究者先冻结对应范围与契约。

## 10. 文档与仓库维护规则

- 每次后续阶段任务完成后，必须更新 `docs/PROJECT_STATE_CURRENT.zh-CN.md`。
- 若本阶段新增或修改研究者确认的决策，必须同步更新 `docs/DECISION_LOG.zh-CN.md`。
- 只有数据准备边界、资产语义、provenance 规则或核心输入输出契约发生变化时，才更新 `docs/DATA_PREP_CONTRACT.zh-CN.md`。
- 所有项目说明文档仅维护中文版本，无需专门创建英文对应文件。
- 提交前必须使用 `git diff` 和 `git status` 检查改动范围。
