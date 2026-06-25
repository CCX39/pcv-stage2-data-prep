# pcv-stage2-data-prep

## 项目定位

本仓库面向硕士课题 Work1 Stage2 的真实点云数据准备、tile 级资产生成与可追溯元数据建设。Stage2 在 Stage1 给定 `Budget_total` 后，为每个空间 tile 选择离散质量档位；本仓库负责准备真实或可追溯的 tile 级候选资产与相关证据。

本仓库不负责修改既有 solver，不修改 `pcv-stage2-allocation`、`pcv-distance-quality-calibration`、原始 Longdress 数据目录、旧处理结果目录或导师脚本包目录。项目说明文档仅维护中文版本。

当前仓库不是完整 Stage2 实验仓库，也尚未完成所有 PDL 质量资产、Draco DRC、播放器 XML、Stage2Input 或全序列批处理。

## 当前状态快照

- 阶段 0A / 0A.1：完成外部原始数据、旧资产、导师脚本与旧 XML 的只读审查，并补录研究者对旧 DASH 风格资产组织、A1/A2 ASCII 路径弃用和 binary PLY 优先等历史说明。
- 阶段 0B：建立数据准备契约、决策日志与项目状态基线。
- 阶段 0C / 0D：完成 G128 grid probe、播放器资源消费审查，以及完整 300 帧 raw-coordinate envelope 扫描。
- 阶段 1A：完成 frame 1051 在 G128 profile 下的 `PDL = 1.0` binary little-endian tile PLY baseline，并完成独立验证。
- 阶段 1B：完成低 PDL 采样语义追溯。
- 阶段 1B.1：完成 README 文档导航与交接可读性维护。
- 阶段 1C：完成 tile-local low-PDL sampling profile 冻结与参考实现验证。

当前尚未完成：

- `PDL = 0.2 / 0.4 / 0.6 / 0.8` 的真实 tile 资产尚未实际生成。
- Draco DRC。
- 播放器 XML / DASH 风格自定义资源清单。
- 正式 asset catalog。
- Stage2Input JSON。
- 多帧或全序列批量资产。
- decode-time benchmark。

## 推荐阅读顺序

新对话、新协作者或新 Codex 会话建议先读：

1. `README.md`
2. `docs/PROJECT_STATE_CURRENT.zh-CN.md`
3. `docs/DATA_PREP_CONTRACT.zh-CN.md`
4. `docs/DECISION_LOG.zh-CN.md`

准备实现下一步 low-PDL 资产生成的人建议先读：

1. `docs/PILOT_GRID_PROFILE.zh-CN.md`
2. `docs/PILOT_BINARY_BASELINE_CURRENT.zh-CN.md`
3. `docs/PILOT_SAMPLING_PROFILE.zh-CN.md`
4. `docs/SAMPLING_REFERENCE_VALIDATION_CURRENT.zh-CN.md`
5. `docs/PDL_SAMPLING_AUDIT.zh-CN.md`
6. `docs/DATA_PREP_CONTRACT.zh-CN.md`
7. `docs/DECISION_LOG.zh-CN.md`

## 文档导航

### 项目控制与交接

| 文档 | 职责 | 适用场景 | 状态定位 |
| --- | --- | --- | --- |
| `docs/PROJECT_STATE_CURRENT.zh-CN.md` | 当前阶段、已完成工作、待决事项和下一步建议 | 换新对话、换协作者、恢复项目时的首要交接文档 | 必须随每个阶段结束更新 |
| `docs/DATA_PREP_CONTRACT.zh-CN.md` | 数据准备边界、资产语义、provenance 术语与职责分离 | 判断某项工作是否越界、是否应进入版本化契约 | 仅在边界或核心契约变化时更新 |
| `docs/DECISION_LOG.zh-CN.md` | 研究者确认决策与待确认决策记录 | 查找 confirmed / pending decision | 决策变化时同步更新 |
| `docs/PROJECT_CONTEXT_FOR_AUDIT.zh-CN.md` | 阶段 0A 审查的研究背景与边界 | 理解最早只读审查的限制 | 历史背景文件，不修改 |

### 外部资产与旧系统审查

| 文档 | 职责 | 适用场景 | 状态定位 |
| --- | --- | --- | --- |
| `docs/ASSET_AUDIT_CURRENT.zh-CN.md` | 原始 Longdress、旧资产、导师脚本包与旧 XML 的只读审查 | 追溯外部资产、旧目录和旧 XML 的证据来源 | 阶段 0A 审查报告 |
| `docs/PLAYER_MANIFEST_CONSUMER_AUDIT.zh-CN.md` | 旧播放器对 DASH 风格自定义 XML 的静态消费审查 | 讨论未来播放器资源清单 XML 前阅读 | 阶段 0C 审查报告 |

### grid 与空间分块证据

| 文档 | 职责 | 适用场景 | 状态定位 |
| --- | --- | --- | --- |
| `docs/GRID_PROBE_CURRENT.zh-CN.md` | 5 帧 raw-coordinate grid probe 与 G54/G128 初步对比 | 回看 G128 成为 pilot 候选的早期证据 | 阶段 0C probe 记录 |
| `docs/FULL_SEQUENCE_ENVELOPE_SCAN_CURRENT.zh-CN.md` | 300 帧 raw-coordinate envelope 扫描与 G128 全序列占用验证 | 理解 frame 1051 pilot profile 的 full-sequence envelope 来源 | 阶段 0D 扫描记录 |

### pilot 资产生成与验证

| 文档 | 职责 | 适用场景 | 状态定位 |
| --- | --- | --- | --- |
| `docs/PILOT_GRID_PROFILE.zh-CN.md` | frame 1051 pilot fixed raw-coordinate grid profile | 生成或验证 frame 1051 pilot 资产前阅读 | 阶段 1A profile 说明 |
| `docs/PILOT_BINARY_BASELINE_CURRENT.zh-CN.md` | `PDL = 1.0` binary PLY baseline 的生成、验证与边界 | 检查已生成 baseline 的数量、格式与验证结果 | 阶段 1A 资产记录 |

### low-PDL 采样追溯与冻结规则

| 文档 | 职责 | 适用场景 | 状态定位 |
| --- | --- | --- | --- |
| `docs/PDL_SAMPLING_AUDIT.zh-CN.md` | calibration 项目低 PDL 采样语义追溯与 tile-local 适配分析 | 理解 1C 采样决策的证据来源 | 阶段 1B 审查报告，已被 D1C 决策承接 |
| `docs/PILOT_SAMPLING_PROFILE.zh-CN.md` | frame 1051 tile-local low-PDL sampling profile 的规则说明 | 实现多质量 binary PLY 生成前必须阅读 | 阶段 1C 冻结规则 |
| `docs/SAMPLING_REFERENCE_VALIDATION_CURRENT.zh-CN.md` | sampling profile、reference vectors 与 Python 验证结果 | 检查采样参考实现是否一致 | 阶段 1C 验证记录 |

## 代码、配置与本地资产

| 路径 | 说明 | Git 边界 |
| --- | --- | --- |
| `docs/` | 项目契约、决策、状态、审查记录和技术说明 | 版本化中文文档 |
| `configs/` | 存放已冻结的版本化 profile，例如 frame 1051 pilot grid profile | 可提交轻量配置 |
| `scripts/` | 存放只读扫描、pilot 生成与独立验证脚本 | 可提交代码；运行范围按阶段任务限定 |
| `artifacts/` | 存放真实生成资产，例如 `artifacts/pilot_1051_g128_raw_v1/` | Git ignored，不进入版本库 |
| `outputs/` | 存放本地 probe / scan 输出 | Git ignored，不进入版本库 |

binary PLY 文件大小只能作为生成资产的 measured 文件尺寸记录，不能直接写成 `r_bytes`。点数、PLY 文件大小或 DRC 文件大小不能写成 `d_ms` 或真实 decoder latency。

## 关键语义边界

1. 当前距离质量标定证据来自 full-cloud rendering 条件，不是 isolated tile calibration。
2. 当前冻结的 tile-local low-PDL sampling 属于 calibration sampling rule 的 derived adaptation，不应写成 tile-level calibrated quality evidence。
3. 当前 pilot 的 G128 profile 是经过 full-sequence raw-coordinate envelope 推导后，用于 frame 1051 资产生成的固定 profile；它不等于官方物理世界坐标网格，也不是已证明最优的最终全序列网格。
4. 当前已生成的真实点云资产只有 frame 1051、`PDL = 1.0` 的 binary PLY baseline；低 PDL 真实 tile PLY 尚未生成。
5. 真实大体积资产不进入 Git；Git 仓库只保存代码、配置、中文文档和可审查的轻量元信息。

## Git 协作规则

- Codex：完成阶段任务后创建一个本地 commit，不 push。
- 研究者：审查本地 commit 后手动执行 `git push origin main`。
- 任务开始前，`git status -sb` 应为：

```text
## main...origin/main
```

- Codex 本轮提交后，`git status -sb` 应为：

```text
## main...origin/main [ahead 1]
```
