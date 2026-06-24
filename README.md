# pcv-stage2-data-prep

本仓库面向硕士课题 Work1 Stage2 的真实数据准备、资产元数据整理与单帧 pilot 支持。目标是在 Stage1 给定 `Budget_total` 后，为 Stage2 提供可追溯的 tile 级多质量候选资产与元数据依据。

当前已完成阶段 0A-0D：外部资产只读审查、数据准备契约、frame 1051 grid probe、播放器 XML 消费契约静态审查，以及 Longdress 全序列 raw-coordinate envelope / G128 occupancy 验证。

阶段 1A 已完成 frame 1051 的 `PDL = 1.0` binary little-endian PLY baseline：基于已确认的 `longdress_raw_g128_fullseq_pilot_v1` profile 生成非空 tile 的 baseline binary PLY，并完成独立验证。真实生成资产位于 Git ignored 的 `artifacts/` 路径，不进入仓库。

后续推进节奏为：先单帧 pilot，再少量帧验证，再进入批处理。当前尚未生成低 PDL 质量版本、Draco DRC、BIN、播放器 XML、Stage2Input 或批量帧资产。

原始点云、批量 tile PLY、DRC、BIN、缓存、日志、压缩包和其他大体积资产不进入 Git。必要时仅在仓库中记录可审查的小型说明、审查报告、契约、决策记录或未来人工确认后的 manifest 说明。

本仓库不修改既有 solver、距离标定项目、原始 Longdress 数据目录、旧处理结果目录或导师脚本包目录。

当前不提前承诺低 PDL 采样规则、Draco 参数、XML schema、decode-time 测量方法或最终 Stage2 数据格式。frame 1051 pilot grid profile 不等于官方世界坐标、物理米制网格或最终全序列实验网格。

主要文档入口：

- `docs/PROJECT_STATE_CURRENT.zh-CN.md`
- `docs/DATA_PREP_CONTRACT.zh-CN.md`
- `docs/DECISION_LOG.zh-CN.md`
- `docs/PILOT_GRID_PROFILE.zh-CN.md`
- `docs/PILOT_BINARY_BASELINE_CURRENT.zh-CN.md`
- `docs/ASSET_AUDIT_CURRENT.zh-CN.md`
