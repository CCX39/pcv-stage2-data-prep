项目名称：pcv-stage2-data-prep

研究背景：
Work1 Stage2 在 Stage1 给定 Budget_total 后，为每个空间 tile
选择离散质量档位。数据准备项目未来需要提供真实或可追溯的
tile 级多质量资产与元数据，但当前仅开展只读资产审查。

当前阶段：
只审查原始 Longdress 数据、旧处理结果和导师脚本包。
不生成、不复制、不压缩、不运行批处理。

后续可能需要的资产：
原始 PLY、tile PLY、多 PDL 版本、DRC、点数、文件字节数、
tile bbox、tile center、资产 manifest。

关键语义边界：
- tile 规则、质量档位语义、Draco 参数、XML 用途目前均未确认。
- r_bytes 后续可对应 DRC 文件字节数，但不等于真实网络总开销。
- d_ms 未 benchmark 前不得描述为真实解码时延。
- visibility、screen_area、distance_norm 是相机状态相关特征，
  不应自动作为静态 tile 元数据。
- 必须区分 measured、calibrated、derived、proxy、synthetic。
- 不得修改 pcv-stage2-allocation、pcv-distance-quality-calibration、
  原始 Longdress 目录或旧资产目录。