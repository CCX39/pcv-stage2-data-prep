# 播放器 Manifest 消费契约静态审查

## 1. 审查范围与只读边界

审查日期：2026-06-23。

本轮只读审查以下外部路径：

```text
OLD_PLAYER_ROOT = E:\Miunaaaa\0-work\code\vv\pythonProject
OLD_PLAYER_XML_PATH = E:\Miunaaaa\0-work\code\vv\pythonProject\static\xml\video_1.xml
OLD_ASSETS_ROOT = E:\Miunaaaa\0-work\code\vv\pythonProject\static\data\video_data\video_1
```

本轮未运行旧播放器、旧预处理脚本、导师脚本、Draco encoder 或 Draco decoder；未修改旧播放器代码、旧 XML 或旧资源目录；未生成、修改或验证新的 XML。

## 2. XML 文件与播放器入口定位

代码直接证实：

- 当前 Flask 后端入口文件为 `E:\Miunaaaa\0-work\code\vv\pythonProject\app.py`。
- `app.py` 定义 `/mpd/<video_id>` 路由，将 `video_id` 拼成 `static/xml/<video_id>.xml` 并以 `application/xml` 返回。
- `app.py` 定义 `/gof_v10` 路由，通过 POST JSON 请求中的字段定位旧资源并以 multipart stream 返回。
- `templates/index.html` 是一个非常简单的模板，包含展示 XML 内容与下载链接示例；本轮未发现其中存在实际 XML 解析逻辑。
- `app_oldver.py` 保留多个历史 `/gof_v*` 路由，可作为历史演化参考，但当前根目录下的主运行入口是 `app.py`。

根据代码与文件关系的合理推测：

- 旧播放器或前端可能通过 `/mpd/1` 或类似 URL 获取 `static/xml/video_1.xml`，再决定向 `/gof_v10` 请求资源。

当前无法确认：

- 当前实际使用的前端客户端是否在其他项目目录中。
- 前端是否解析 `video_1.xml` 的 `AdaptationSet`、`Representation`、`SegmentTemplate`、`Frame` 或 `Cell` 字段。

## 3. 直接观察到的 XML 消费路径

代码直接证实的路径：

```text
GET /mpd/<video_id>
-> app.py
-> static/xml/<video_id>.xml
-> send_from_directory(..., mimetype='application/xml')
```

该路径只定位并返回 XML 文件；在 `app.py` 中未观察到 `xml.etree.ElementTree`、DOM parser 或针对 XML tag/attribute 的读取逻辑。

`/gof_v10` 的资源消费路径：

```text
POST /gof_v10
JSON: video_id, gof_id, as_id, rep_id
-> static/data/video_data/video_<video_id>/GOF_<gof_id>/
-> 根据 as_id 选择 A3_ply_binary / A4_bin_binary / A5_drc_binary
-> 根据 rep_id 选择排序后的 R* representation 文件夹
-> 按硬编码 frame/cell 循环读取文件
```

这条路径消费的是请求 JSON、文件系统目录和文件名约定，不是直接消费 XML 字段。

## 4. XML tag / attribute 消费表

| XML tag / attribute | XML 中观察到 | `app.py` 运行时直接消费证据 | 备注 |
| --- | --- | --- | --- |
| 根元素 `info` | 直接观察到 | 未观察到 | XML 根元素为自定义 `info`，不是标准 `MPD` 根元素。 |
| `info@frames` | `300` | 未观察到 | `/gof_v10` 未读取 XML，frame 循环硬编码为 5。 |
| `info@gof` | `60` | 未观察到 | `/gof_v10` 使用请求 JSON 中的 `gof_id`。 |
| `info@baseURL` | 直接观察到 | 未观察到 | `app.py` 未读取。 |
| `info@videoDuration` | 直接观察到 | 未观察到 | `app.py` 未读取。 |
| `info@frameRate` | `30` | 未观察到 | `app.py` 未读取。 |
| `info@cellNum` | `12` | 未观察到 | `/gof_v10` 硬编码 `cells_per_frame = 12`。 |
| `info@video_id_in_path` | `video_1` | 未观察到 | `/gof_v10` 使用请求 JSON 中的 `video_id`。 |
| `info@qualityLevels` | `4` | 未观察到 | `rep_id` 按目录排序选择，不从 XML 读取。 |
| `GoF@id` | 直接观察到 | 未观察到 | `/gof_v10` 使用请求 JSON 中的 `gof_id`。 |
| `AdaptationSet@id` | 观察到 `3/4/5` | 未观察到直接 XML 读取；但 `as_id` 请求字段采用相同编号约定 | 代码把 `as_id=3/4/5` 映射到 A3/A4/A5 目录。 |
| `AdaptationSet@mimeType` | 直接观察到 | 未观察到 | `app.py` 自行按 `as_id` 设定 MIME。 |
| `Representation@id` | 直接观察到 | 未观察到直接 XML 读取；但 `rep_id` 请求字段采用 1-based index | 代码按 `R*` 文件夹数字排序后用 `rep_id - 1` 选目录。 |
| `Representation@qualityLabel` | 直接观察到 | 未观察到 | 当前后端不解释质量标签。 |
| `Representation@avgGoFBitrate` | 直接观察到 | 未观察到 | 未见运行时消费。 |
| `Representation@avgOverallBitrate` | 直接观察到 | 未观察到 | 未见运行时消费。 |
| `Representation@maxFramePointsInRep` | 直接观察到 | 未观察到 | 未见运行时消费。 |
| `SegmentTemplate@media` | 直接观察到 | 未观察到 | `/gof_v10` 重新拼接路径，不读取模板字符串。 |
| `SegmentTemplate@duration` | 直接观察到 | 未观察到 | 未见运行时消费。 |
| `Frame@id` | 直接观察到 | 未观察到 | `/gof_v10` 使用 `range(5)` 生成 frame id。 |
| `Frame@points` | 直接观察到 | 未观察到 | 未见运行时消费。 |
| `Cell@id` | 直接观察到 | 未观察到 | `/gof_v10` 使用 `range(12)` 生成 cell id。 |
| `Cell@points` | 直接观察到 | 未观察到 | 未见运行时消费。 |
| `Cell@size` | 直接观察到 | 未观察到 | 未见运行时消费。 |

补充观察：`calculate_bitrates_from_mpd.py` 会用 `xml.etree.ElementTree` 解析 MPD/XML，并读取 `info@frameRate`、`info@gof`、`info@video_id_in_path`、`AdaptationSet`、`Representation`、`SegmentTemplate@media`、`Frame`、`Cell@size` 等字段。但该文件是码率统计工具，不是当前播放器运行时入口；本阶段未运行它。

## 5. 资源路径构造与目录依赖

代码直接证实，`/gof_v10` 构造基础目录：

```text
static/data/video_data/video_<video_id>/GOF_<gof_id>
```

`as_id` 映射：

| as_id | 目录 | 文件类型 | multipart trans_mode |
| ---: | --- | --- | ---: |
| 3 | `A3_ply_binary` | `.ply` | 1 |
| 4 | `A4_bin_binary` | `.bin` | 2 |
| 5 | `A5_drc_binary` | `.drc` | 2 |

Representation 选择：

```text
列出 AS 目录下以 R 开头的文件夹
提取 R 后的数字
按数字升序排序
rep_id 作为 1-based index 选择文件夹
```

A4 路径：

```text
<rep_base_dir>/cell_<cell_id>.bin
```

A3 / A5 路径：

```text
<rep_base_dir>/frame_<frame_id>/frame_<frame_id>_cell_<cell_id>.<ply|drc>
```

`frames_per_gof = 5` 与 `cells_per_frame = 12` 在 `app.py` 中硬编码。

## 6. Representation / quality / codec 选择行为

代码直接证实：

- 后端不读取 `Representation@qualityLabel` 来选择质量档位。
- 后端不读取 `SegmentTemplate@media` 来构造路径。
- 后端不读取 `mimeType` 来决定文件类型，而是由 `as_id` 分支内部设定。
- `rep_id` 不是直接匹配 XML `Representation@id`，而是作为排序后 `R*` 文件夹列表的 1-based index。
- 若文件不存在，循环会跳过该文件；若完全没有找到文件，仍返回只有最终 boundary 的 multipart 响应，并打印 warning。

根据代码与 XML 的合理推测：

- XML 中 `AdaptationSet@id=3/4/5` 与后端 `as_id=3/4/5` 目录映射存在同构关系。
- XML 中 `Representation@id` 与后端 `rep_id` 很可能被前端以相同编号传入，但本阶段未找到前端解析代码，不能确认。

当前无法确认：

- 前端是否依据 XML `qualityLabel`、`avgGoFBitrate`、`Cell@size` 或 `Cell@points` 做 representation selection。
- 旧播放器是否真正区分 bitrate-driven、quality-driven 或用户指定的质量选择。

## 7. 对 A3 / A4 / A5 的实际消费证据

代码直接证实：

- `A3_ply_binary`：`as_id == 3` 时被 `/gof_v10` 引用，按 frame 子目录读取 `frame_<frame_id>_cell_<cell_id>.ply`。
- `A4_bin_binary`：`as_id == 4` 时被 `/gof_v10` 引用，按 representation 根目录读取 `cell_<cell_id>.bin`。
- `A5_drc_binary`：`as_id == 5` 时被 `/gof_v10` 引用，按 frame 子目录读取 `frame_<frame_id>_cell_<cell_id>.drc`。

当前无法确认：

- A4 `.bin` 的内部封装格式。
- A5 `.drc` 是否总是由同名 A3/A3-like binary PLY 直接生成。
- XML 中 A3/A4/A5 的所有 representation 是否与旧资源目录全量一致。

## 8. 可迁移到新 manifest 的组织思想

可作为参考的组织思想：

- 用 manifest 层显式区分资源类别，例如 PLY、BIN、DRC。
- 用 `AdaptationSet` 表达资源类型或编码类型，用 `Representation` 表达质量或编码 profile 的候选。
- 用模板化路径描述 GoF、frame、cell/tile 的文件关系。
- 在 manifest 中记录每帧、每 cell/tile 的点数和文件尺寸，便于播放器或调度层查询。

这些只能作为组织思想参考，不能直接视为新项目的 XML schema。

## 9. 当前不能继承或不能确认的旧逻辑

不能直接继承：

- 旧 XML 的根元素 `info` 与字段集合不能直接冻结为新 schema。
- 旧 `12` cell 设定不能直接继承到新 fixed grid。
- 旧 `R*` 文件夹排序与 `rep_id` 的关系不能直接写成新 quality-level 契约。
- `qualityLabel` 中的 `0.8`、`0.6`、`0.4`、`cl`、`qp`、`qc` 等字符串不能直接写成已确认 PDL 或 Draco 参数。
- `/gof_v10` 缺文件自动跳过并可能返回空 multipart 的行为不适合直接作为新数据准备验证规则。

当前无法确认：

- 旧 XML 是否被完整 DASH 播放器消费，或只是自定义资源清单。
- 当前实际前端是否解析 XML 并如何把 XML 字段映射到 `/gof_v10` 请求 JSON。
- GoF 长度、frame id 与 cell id 是否应在新项目中沿用旧的 5-frame / 12-cell 假设。

## 10. 对未来新 XML 设计的约束与待决问题

对未来设计的约束：

- 新 XML 应先定义明确消费方：旧播放器兼容层、未来播放器，或仅作为资源清单。
- 新 XML 不应承担 asset catalog、provenance 记录与 Stage2Input 三种职责。
- 若 XML 需要驱动资源请求，应避免让运行时代码同时依赖 XML 模板和另一套硬编码路径规则。
- 若继续使用 `AdaptationSet` / `Representation` / `SegmentTemplate` 思想，应明确哪些 tag/attribute 被播放器实际读取。
- 新 fixed grid 若超过旧 12 cell，必须先确认播放器资源层能否接受新的 tile/cell 数量和 id 编码。

待决问题：

1. 未来播放器是由 XML `SegmentTemplate@media` 驱动路径，还是由 API JSON 字段和后端硬编码路径驱动。
2. `AdaptationSet` 是否继续用于区分 PLY、DRC、BIN，还是改为区分 codec/profile。
3. `Representation` 是否直接对应 PDL，是否记录 Draco profile，以及是否需要 bitrate 字段。
4. 空 tile 是否进入 XML；若进入，路径字段如何表达。
5. 新 XML 与 asset catalog / Stage2Input 之间如何建立引用关系，而不是混为一个文件。
