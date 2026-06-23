# 阶段 0A 外部资产、旧处理结果与 MPD/XML 只读审查

## 1. 审查范围、时间与边界

- 审查日期：2026-06-23（Asia/Shanghai）。
- 当前仓库路径：`E:\Miunaaaa\0-work\code\pcv-stage2-data-prep`。
- Git branch：`main`。
- Git remote URL：`https://github.com/CCX39/pcv-stage2-data-prep.git`。
- 原始 Longdress 数据目录：`E:\Miunaaaa\0-work\data\8i\longdress\longdress\Ply`。
- 旧处理结果目录：`E:\Miunaaaa\0-work\code\vv\pythonProject\static\data\video_data\video_1`。
- 导师脚本包目录：`E:\Miunaaaa\0-work\code\MENTOR_SCRIPT_PACKAGE_vv_preprocess`。
- 单独 MPD/XML 文件：`E:\Miunaaaa\0-work\code\vv\pythonProject\static\xml\video_1.xml`。

本阶段仅进行了目录遍历、文件名分析、静态脚本阅读、文本配置阅读、PLY header 读取、XML 静态解析和小型元信息统计。未运行任何外部处理脚本，未生成、复制、压缩、切块或批量处理任何点云资产，未修改外部目录与文件。

## 2. 原始 Longdress 数据审查

### 2.1 直接观察到

- 目录存在，顶层直接包含 PLY 文件，未观察到子目录。
- 文件数量：300 个文件，扩展名统计为 `.ply` 300 个。
- 文件命名模式：`longdress_vox10_####.ply`，例如 `longdress_vox10_1051.ply`、`longdress_vox10_1200.ply`、`longdress_vox10_1350.ply`。
- 可识别帧号范围：1051 到 1350；在该闭区间内未发现缺号。
- PLY 文件大小范围：16,718,093 到 20,838,494 字节；平均约 18,952,105 字节。代表样例：`longdress_vox10_1051.ply` 为 17,216,785 字节，`longdress_vox10_1200.ply` 为 18,236,492 字节，`longdress_vox10_1350.ply` 为 18,352,361 字节。
- 300 个 PLY header 的 `format` 均为 `format ascii 1.0`。
- 300 个 PLY header 均只观察到 `element vertex ...` 一个元素类型；未观察到 face 或其他元素类型。
- 顶点数按帧变化：最小 733,580，最大 916,250，平均约 834,315。
- 属性字段一致：`x/y/z` 为 `float`，`red/green/blue` 为 `uchar`；未观察到法向量或 alpha 字段。

代表性 PLY header 摘要（`longdress_vox10_1051.ply`，仅到 `end_header`）：

```text
ply
format ascii 1.0
comment Version 2, Copyright 2017, 8i Labs, Inc.
comment frame_to_world_scale 0.179523
comment frame_to_world_translation -45.2095 7.18301 -54.3561
comment width 1023
element vertex 765821
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
end_header
```

### 2.2 合理推测但尚未验证

- 文件名中的 `vox10` 可能与数据集的体素化或分辨率标识有关，但本次只读审查未找到本地说明文件可直接确认其语义。
- PLY header 中的 `frame_to_world_scale`、`frame_to_world_translation` 和 `width` 是可直接观察到的元数据字段；它们可能与坐标变换有关，但本次审查未找到足以解释坐标轴方向或物理单位的本地说明。

### 2.3 无法确认

- 原始数据集坐标轴方向：未确认。
- 原始坐标单位或物理米解释：未确认。
- `frame_to_world_scale` 是否可直接用于当前 Stage2 的物理尺度：未确认。
- 原始数据是否已有官方 tile 规则、质量档位或 Draco 参数：未确认。

## 3. 旧处理结果目录审查

### 3.1 直接观察到

- 目录存在，顶层为 `GOF_1` 到 `GOF_60` 共 60 个 GoF 目录。
- 递归统计：5220 个目录，29952 个文件。
- 扩展名统计：

| 扩展名 | 文件数 | 字节总数 |
|---|---:|---:|
| `.ply` | 20852 | 31341178326 |
| `.drc` | 8065 | 3955371145 |
| `.bin` | 1035 | 1818120832 |

- 未在旧处理结果目录内直接观察到 `.xml`、`.mpd`、`.json`、`.csv`、`.txt`、日志、配置、README 或脚本文件；该目录内仅观察到 `.ply`、`.drc`、`.bin`。
- 每个 GoF 目录下直接观察到相同的五类子目录：`A1_ply`、`A2_drc`、`A3_ply_binary`、`A4_bin_binary`、`A5_drc_binary`。
- 代表性层级示例：
  - `GOF_1\A1_ply\R1\frame_0\frame_0_cell_0.ply`
  - `GOF_1\A3_ply_binary\R2_0.8\frame_0\frame_0_cell_0.ply`
  - `GOF_1\A2_drc\R1_qp12qc8\frame_0\frame_0_cell_0.drc`
  - `GOF_1\A4_bin_binary\R1_cl10qp10qc4\cell_0.bin`
  - `GOF_1\A5_drc_binary\R1_cl10qp12qc6\frame_0\frame_0_cell_0.drc`
- `A1_ply` 下观察到四个表示层级目录：`R1`、`R2_0.8`、`R3_0.6`、`R4_0.4`；每个层级各 3600 个 PLY 文件。
- `A3_ply_binary` 下同样观察到 `R1`、`R2_0.8`、`R3_0.6`、`R4_0.4`；每个层级各 1613 个 PLY 文件。
- `A2_drc` 下观察到 `R1_qp12qc8` 和 `R2_qp10qc6`；每个层级各 1613 个 DRC 文件。
- `A4_bin_binary` 下观察到 `R1_cl10qp10qc4`、`R2_0.8_cl10qp10qc6`、`R3_0.4_cl10qp10qc4`；每个层级各 345 个 BIN 文件。
- `A5_drc_binary` 下观察到 `R1_cl10qp12qc6`、`R2_cl10qp10qc6`、`R3_0.4_cl10qp10qc4`；每个层级各 1613 个 DRC 文件。
- 文件名中直接观察到 `GOF_*`、`frame_*`、`cell_*`、`R1`、`R2_0.8`、`R3_0.6`、`R4_0.4`、`qp*`、`qc*`、`cl*` 等字符串。
- 可识别 tile ID 格式：旧资产文件名使用线性 `cell_0` 到 `cell_11`，XML 中也有 `cellNum="12"` 和 `Cell id="0"` 到 `Cell id="11"`。
- `A1_ply` 每个 `GOF/representation/frame` 组合下直接观察到 12 个 PLY，对应 `cell_0` 到 `cell_11`。
- `A1_ply` 中直接确认 7948 个 170 字节 PLY，其 header 为 `element vertex 0`，可视为零点 tile PLY 文件。
- `A1_ply\R1\frame_0\frame_0_cell_0.ply` 是 ASCII PLY，header 中 `element vertex 227188`；`A1_ply\R1\frame_0\frame_0_cell_1.ply` 是 ASCII PLY，header 中 `element vertex 0`。
- `A3_ply_binary\R1\frame_0\frame_0_cell_0.ply` 是 `binary_little_endian 1.0`，header 中 `element vertex 227188`；对应空 tile `frame_0_cell_1.ply` 未在 `A3_ply_binary\R1\frame_0` 中出现。
- 按 `GOF/frame/cell` 键比较，`A3_ply_binary\R1` 与 `A2_drc\R1_qp12qc8` 有 1613/1613 个键重合；`A3_ply_binary\R2_0.8` 与 `A2_drc\R2_qp10qc6` 有 1613/1613 个键重合；`A3_ply_binary\R4_0.4` 与 `A5_drc_binary\R3_0.4_cl10qp10qc4` 有 1613/1613 个键重合。

### 3.2 合理推测但尚未验证

- `GOF_*` 目录与 `frame_0` 到 `frame_4` 子目录共同暗示旧资产以 5 帧为一个 GoF 组织，但 GoF 作为当前 Stage2 决策单位仍未确认。
- `R2_0.8`、`R3_0.6`、`R4_0.4` 等目录名可能表示某种降采样比例或质量标签，但不能仅凭文件名确认其等同于 PDL `{0.2, 0.4, 0.6, 0.8, 1.0}`。
- `qp`、`qc`、`cl` 字符串可能对应 Draco 命令参数，但本次审查未在旧目录内发现可核验的配置文件或命令日志。
- A3 binary PLY 与 A2/A5 DRC 在路径键上可对应，说明存在压缩前后关系的强命名证据；但是否由对应 tile PLY 直接生成、使用何种 Draco 版本和参数，仍未由旧目录本身直接确认。
- `A4_bin_binary` 可能是按 GoF 聚合的二进制封装资产，因为其文件位于 representation 目录下并命名为 `cell_*.bin`，不再按 `frame_*` 分层；但封装格式与用途未由旧目录说明文件直接确认。

### 3.3 无法确认

- 旧 tile ID 是否跨帧、跨 GoF 对应同一稳定空间区域：无法确认。
- 旧 tile 的空间边界、坐标 origin、cell size、边界归属规则：无法确认。
- 旧质量档位与 PDL 的真实关系：无法确认。
- 是否存在嵌套降采样：无法确认。
- DRC 是否全部从对应 tile PLY 直接生成：无法确认。
- Draco 工具版本、命令、几何量化、颜色属性编码等完整参数：无法确认。
- `A1_ply`、`A2_drc`、`A3_ply_binary`、`A4_bin_binary`、`A5_drc_binary` 的命名含义和最终用途：无法确认。
- 旧处理结果目录内不存在 XML；单独的 `video_1.xml` 与旧目录有路径引用关系，但是否为该目录唯一或正式索引：无法确认。

## 4. 导师脚本包静态审查

### 4.1 直接观察到

- 脚本包存在，主要语言为 Python；同时包含少量 C/C++、CMake 文件、构建产物、XML、TXT 和 PNG。
- 未观察到顶层 README 或 requirements 文件；观察到 `.vscode`、`.idea` 和 CMake 构建目录。
- 可能的入口文件包括但不限于：
  - `sampling.py`、`sampling_expanded.py`
  - `asciiToBin\asciiTobin.py`、`asciiToBin\expand.py`
  - `segment tile\tiling.py`、`segment tile\segment_tile_xml.py`、`segment tile\segment_tile_xml_2.py`、`segment tile\segment_tile_xml_new.py`、`segment tile\multi_threads_seg_tile.py`
  - `encode\encoder.py`、`encode\encode_unboundle.py`、`encode\encoded_boundle.py`、`encode\decode_boundle.py`
  - `bitrate_generate\*.py`
  - `parse_ptcl_model\parse_time.py`、`parse_ptcl_model\collect.py`
  - `render\*.py`、`saliency\*.py`、`viewpoint\*.py`
- 多个脚本硬编码 `/home/xyn/0research/dataset/longdress/longdress/...` 绝对路径。
- 多个脚本会创建输出目录或写文件，例如 `os.makedirs(...)`、`Path.mkdir(...)`、`PlyData(...).write(...)`、`tree.write(...)`、`json.dump(...)`、`open(..., 'w'/'wb')`。
- `segment tile\tiling.py` 静态代码中存在基于全局 AABB 的切块逻辑：读取 PLY，计算 `global_min/global_max`，用 `np.floor((points - global_min) * inv_cell_size)` 计算索引，并用 `np.clip` 限制边界；入口示例中 `cell_dims = [3, 3, 3]`。
- `segment tile\segment_tile_xml_new.py` 等脚本存在另一套逻辑：`gof_length = 5`、`TOTAL_FRAMES = 1800`、`FRAMES_TO_PROCESS = 300`、`cell_dims = [2, 2, 2]`，会复制 GoF 以扩展序列，并生成 `global_metadata.xml`、`spatial_position.xml` 或质量级 XML。
- `sampling.py` 中存在 `downsample_voxel_sizes = {'high': 0.2, 'medium': 0.3, 'low': 0.4, 'very_low': 0.5}`；`sampling_expanded.py` 中存在 `downsample_ratios = {'high': 0.8, 'medium': 0.7, 'low': 0.5, 'very_low': 0.4}`。
- `encode\encoder.py`、`encode\encode_unboundle.py`、`encode\encoded_boundle.py` 等脚本静态包含 `draco_encoder`、`draco_decoder` 调用，并出现 `-cl`、`-qp`、`-qc` 参数。
- `encode\encoder.py` 和 `encode\encode_unboundle.py` 中观察到两组配置名：`high_quality` 与 `low_quality`；其静态配置分别包括 `cl=7, qp=14, qc=8` 和 `cl=8, qp=10, qc=6`。
- `encode\encoded_boundle.py` 会将多个 DRC 写入 `.bin`，并记录空帧标志；也会修改 XML 树中的 `CompressedVersion` 元素，写 `compression_stats.json`，并可能运行解压测试。
- `encode\encoder_expanded.py` 中存在当文件数超过预期时 `os.remove(file_path)` 删除多余 `.drc` 或 `.ply` 的逻辑，也存在复制文件补齐帧数的逻辑。
- `parse_ptcl_model\parse_time.py` 中存在 decode-time benchmark 代码：未压缩 PLY 使用 Open3D 读取计时，压缩 DRC 使用 `draco_decoder` 解码到临时 PLY 后计时；该脚本会写 XML 和图表。

### 4.2 脚本可能做什么

- 可能执行 ASCII PLY 到 binary PLY 转换、扩展 300 帧到 1800 帧、降采样、切块、按 GoF 组织、生成 XML 元数据、Draco 编码、DRC/BIN 封装、解码测试、码率统计、渲染、LPIPS/saliency 相关计算、视点数据处理和 decode-time 测量。

### 4.3 脚本实际已确认做什么

- 本阶段没有运行任何脚本，因此不能确认脚本在当前机器、当前数据路径和当前依赖环境下实际成功执行过。
- 只能确认静态代码中存在上述读写、生成、复制、删除、压缩、解码和 XML 修改逻辑。

### 4.4 无法确认与风险

- 无法确认哪一个脚本或哪一次运行生成了旧处理结果目录。
- 无法从脚本包静态确认旧资产的 tile 规则；脚本中存在 `[3,3,3]`、`[2,2,2]` 等不同示例，而旧资产文件名显示 `cell_0` 到 `cell_11` 共 12 个线性 cell。
- 无法确认旧资产的坐标系、网格 origin、cell size、边界归属规则和跨帧稳定性。
- 无法确认旧质量 level 与 PDL 的真实语义；脚本中出现 `high/medium/low/very_low`、`0.8/0.7/0.5/0.4`、`R2_0.8` 等多种命名或比例，但没有统一说明文件。
- 无法确认随机种子、点数取整、采样确定性或嵌套采样。部分 viewpoint 脚本使用 `np.random.normal` 生成预测扰动，但这与 tile 资产降采样关系未确认。
- 无法确认旧 DRC 的 Draco 版本与完整参数。旧目录和 XML 中出现 `cl10qp...` 字符串，但当前读到的部分编码脚本配置不完全一致。
- 存在静默跳过或默认兜底行为风险：多处代码在目录不存在、文件缺失、异常或解析失败时 `continue`、打印警告或返回默认值。
- 存在覆盖或污染输出目录风险：多个脚本会写入固定输出路径、复制目录、删除多余文件、清理临时文件或修改 XML。

## 5. 单独 MPD/XML 文件审查

### 5.1 可从 XML 结构直接确认的内容

- 文件路径：`E:\Miunaaaa\0-work\code\vv\pythonProject\static\xml\video_1.xml`。
- 文件大小：2,184,410 字节。
- XML 声明：`<?xml version="1.0" encoding="UTF-8"?>`。
- 根元素：`info`，无命名空间。
- 根属性包括：`frames="300"`、`gof="60"`、`flag="0"`、`baseURL="http://172.31.179.127:5000"`、`videoDuration="PT10S"`、`frameRate="30"`、`cellNum="12"`、`video_id_in_path="video_1"`、`qualityLevels="4"`。
- 标签统计：`GoF` 60 个，`AdaptationSet` 180 个，`Representation` 600 个，`SegmentTemplate` 600 个，`Frame` 3000 个，`Cell` 36000 个。
- 基本 DASH 风格元素：存在 `AdaptationSet`、`Representation`、`SegmentTemplate`；不存在 `MPD` 根元素、`Period`、`SegmentList`、`BaseURL`、`Initialization`、`SegmentURL`。
- `AdaptationSet` 的 `contentType` 为 `pointcloud`，`mimeType` 包括 `application/ply`、`application/octet-stream`、`application/octet-stream+drc`。
- `Representation` 属性包括 `id`、`bandwidth`、`avgGoFBitrate`、`avgOverallBitrate`、`maxFramePointsInRep`，部分有 `qualityLabel`。
- `SegmentTemplate media` 引用相对路径，例如：
  - `data/video_data/video_1/GOF_$GoFID$/A3_ply_binary/R1/frame_$FrameID$/frame_$FrameID$_cell_$CellID$.ply`
  - `data/video_data/video_1/GOF_$GoFID$/A4_bin_binary/R1_cl10qp10qc4/cell_$CellID$.bin`
  - `data/video_data/video_1/GOF_$GoFID$/A5_drc_binary/R1_cl10qp12qc6/frame_$FrameID$/frame_$FrameID$_cell_$CellID$.drc`
- `Cell` 元素包含 `id`、`points`、`size`；示例中 `Cell id="1" points="0" size="0"` 与旧目录中的空 tile 现象一致。
- XML 直接引用 `A3_ply_binary`、`A4_bin_binary`、`A5_drc_binary`，未在 `SegmentTemplate` 中观察到对 `A1_ply` 或 `A2_drc` 的引用。

### 5.2 根据字段与目录关系的初步推测

- 该 XML 很可能是旧系统用于索引 `video_1` 资产的清单，因为其中的相对路径与 `OLD_ASSETS_ROOT` 的目录结构直接对应。
- 它使用 DASH 风格标签组织 pointcloud 资产，但根元素不是 `MPD`，且缺少 `Period` 等 MPEG-DASH 常见结构，因此不能直接断言它符合完整 MPEG-DASH MPD 规范。
- `duration="0.03333333"` 的 PLY/DRC template 与 30 FPS 单帧时长相符；`A4_bin_binary` 的 `duration="0.16666667"` 与 5 帧 GoF 时长相符。但这只是字段关系上的初步推测。
- `qualityLabel` 中的 `0.8`、`0.6`、`0.4`、`cl10qp...` 等字符串与旧目录名一致，但不能直接确认其为 PDL 或最终质量语义。

### 5.3 当前无法确认的用途或语义

- 无法确认该 XML 是 DASH 播放器资源索引、tile 描述索引、媒体分段清单、质量层级描述，或旧系统自定义清单中的哪一种正式用途。
- 无法确认其 `bandwidth`、`avgGoFBitrate`、`avgOverallBitrate` 是如何计算的。
- 无法确认 `baseURL` 指向的服务是否仍有效，或是否属于当前 Stage2 数据管线。
- 无法确认该 XML 是否应复用于新项目；也不能自动把它作为当前 Stage2 的正式 manifest。

## 6. 初步复用性判定

| 对象 | 判定 | 理由 |
|---|---|---|
| 原始 Longdress 数据组织方式 | 可直接作为参考资产，但仍需后续验证 | 原始 PLY 文件组织清晰、帧号连续、header 可读，可作为后续真实数据来源参考；但坐标轴、物理单位和 Stage2 tile 规则未确认。 |
| 旧 tile/质量/DRC 资产 | 可部分复用，需要改造或补充验证 | 旧目录中存在可对应的 PLY、binary PLY、DRC、BIN 与空 tile 证据；但 tile 规则、quality level 语义、Draco 参数、生成脚本和可复现性未确认。 |
| 旧 XML/MPD | 可部分复用，需要改造或补充验证 | XML 与旧目录路径可直接对应，并包含 frame/cell/size/points 字段；但它不是标准 `MPD` 根结构，真实用途和新项目适配性未确认。 |
| 导师脚本包 | 当前不建议复用 | 脚本包包含硬编码路径、写输出、复制、删除、压缩、解码测试和 XML 修改逻辑；且存在多套不一致网格和质量示例。当前仅适合作为静态参考，不能直接运行或纳入管线。 |

## 7. 对后续单帧 pilot 的影响

### 7.1 已有证据足以支持的事项

- 原始 Longdress 目录存在 300 个 ASCII PLY，帧号 1051 到 1350 连续。
- 原始 PLY 中可直接读取 `x/y/z` 与 RGB 字段和每帧顶点数。
- 旧资产目录存在 60 个 `GOF_*`，每个 GoF 下存在 PLY、DRC、BIN 三类资产。
- 旧资产和 `video_1.xml` 中可直接观察到线性 `cell_0` 到 `cell_11` 的编号。
- 旧目录中存在明确零点 tile PLY 文件，样例和批量 header 均显示 `element vertex 0`。
- `video_1.xml` 能与 `A3_ply_binary`、`A4_bin_binary`、`A5_drc_binary` 建立明确相对路径关系。
- 后续若需要静态资产元数据，可优先考虑从文件 header、文件大小、XML 中的 `points/size` 和实际文件字节数交叉验证。

### 7.2 当前仍不能冻结的事项

- tile 规则：未确认。
- 是否使用跨帧固定世界坐标网格：未确认。
- 旧 tile ID 是否跨帧稳定：未确认。
- quality level 与 PDL 的关系：未确认。
- 是否采用嵌套降采样：未确认。
- Draco profile、版本、命令和量化参数：未确认。
- MPD/XML 是否需要进入新数据管线：未确认。
- 决策时间单位是 frame、代表帧还是 GoF：未确认。
- `r_bytes` 的正式口径：未确认。后续可优先使用对应 DRC 编码文件实际字节数，但这不等于真实端到端网络传输总开销。
- `d_ms` 的 benchmark、derived estimate 或 proxy 策略：未确认。点数、PLY 文件大小或 DRC 文件大小不能直接写成真实 decoder latency。
- 相机相关字段生成方式：未确认。`visibility`、`screen_area`、`distance_norm` 是相机状态相关 derived 特征，不应自动作为静态 tile 字段。

### 7.3 当前不应过早实现的内容

- 不应开始批量切块、批量降采样或批量质量版本生成。
- 不应开始 Draco 批量编码、解码测试或压缩参数搜索。
- 不应生成 Stage2Input JSON 或正式 manifest。
- 不应把旧 XML 直接转换为新项目输入格式。
- 不应把旧资产中的 `0.8/0.6/0.4` 直接写成 PDL。
- 不应把点数、PLY 大小、DRC 大小直接写成 measured decode latency。
- 不应在未确认坐标系和 tile 稳定性前实现相机可见性、screen area 或 distance_norm 生成。
- 不应运行导师脚本包中的切块、压缩、解码、复制、清理或 XML 生成脚本。

## 8. 需要研究者确认的问题

1. tile 是否采用全序列共享世界坐标网格。
2. 旧 tile ID 是否跨帧稳定。
3. 旧质量档位是否真对应 PDL `{0.2, 0.4, 0.6, 0.8, 1.0}`。
4. 是否存在嵌套降采样。
5. DRC 是否从对应 tile PLY 直接生成。
6. Draco 参数与版本是否可恢复。
7. MPD/XML 的真实用途，以及其是否值得在新项目中复用。
8. 后续 Stage2 的决策单位是单帧、代表帧还是 GoF 聚合。
9. decode-time 后续采用真实 benchmark、derived estimate 还是明确 proxy。
10. Longdress 原始坐标轴与尺度解释。
11. 旧资产与现有 `pcv-stage2-allocation` Stage2Input 之间是否存在真正可复用的映射关系。
12. 旧目录中的 `A1_ply`、`A2_drc`、`A3_ply_binary`、`A4_bin_binary`、`A5_drc_binary` 分别对应哪一次处理流程和哪类播放器/实验用途。
13. `video_1.xml` 中 `bandwidth`、`avgGoFBitrate`、`avgOverallBitrate` 的计算公式和单位。
14. 旧 XML 中 `baseURL="http://172.31.179.127:5000"` 是否只是旧播放器部署地址，还是仍有研究含义。
