# pcv-stage2-data-prep

本仓库面向硕士课题 Work1 Stage2 的真实数据准备、资产元数据整理与后续单帧 pilot 支持。目标是在 Stage1 给定 `Budget_total` 后，为 Stage2 提供可追溯的 tile 级多质量候选资产与元数据依据。

当前已完成阶段 0A：原始 Longdress、旧处理结果、导师脚本包与旧 XML/MPD 的只读审查。当前阶段 0B 正在建立数据准备契约、决策记录和项目状态基线。

后续推进节奏为：先单帧 pilot，再少量帧验证，再进入批处理。当前不实现真实切块、压缩、quality assets、manifest、Stage2Input 或批量实验。

原始点云、批量 tile PLY、DRC、BIN、缓存、日志、压缩包和其他大体积资产不进入 Git。必要时仅在仓库中记录可审查的小型说明、审查报告、契约、决策记录或未来人工确认后的 manifest 说明。

本仓库不修改既有 solver、距离标定项目、原始 Longdress 数据目录、旧处理结果目录或导师脚本包目录。

当前不提前承诺具体 tile grid 数值、低 PDL 采样规则、Draco 参数、XML schema、decode-time 测量方法或最终 Stage2 数据格式。

主要文档入口：

- `docs/PROJECT_STATE_CURRENT.zh-CN.md`
- `docs/DATA_PREP_CONTRACT.zh-CN.md`
- `docs/DECISION_LOG.zh-CN.md`
- `docs/ASSET_AUDIT_CURRENT.zh-CN.md`
