# Draco CLI 工具链只读审查记录

## 1. 审查范围与 no-write 边界

阶段 2A 仅通过无输入命令审查本机 PATH 中的 `draco_encoder` 与 `draco_decoder`。本轮未执行任何带 `-i`、`-o`、PLY 路径或 DRC 路径的命令，未执行实际编码或解码，未生成、删除、修改或覆盖任何 PLY / DRC / BIN / XML 文件。

本轮目标是记录当前 CLI 可观察事实，并为后续受控 round-trip probe 准备文档证据。所有实际编码可执行性、round-trip fidelity、DRC 文件大小、decode cost 和渲染质量结论均尚未得到。

## 2. 命令定位与 executable 元信息

### `draco_encoder`

`Get-Command draco_encoder -All` 与 `where.exe draco_encoder` 解析到：

```text
E:\Miunaaaa\0-work\code\draco_encoder\draco-1.5.7\build\Release\draco_encoder.exe
```

文件元信息：

| 字段 | 值 |
| --- | --- |
| absolute path | `E:\Miunaaaa\0-work\code\draco_encoder\draco-1.5.7\build\Release\draco_encoder.exe` |
| file size bytes | `681472` |
| SHA-256 | `EF2BDDC544E46CBA1396037998055A51517D867E9374AD26A4C69947C47AC4C6` |
| Windows FileVersion | unavailable |
| Windows ProductVersion | unavailable |
| CompanyName / ProductName / OriginalFilename | unavailable |

### `draco_decoder`

`Get-Command draco_decoder -All` 与 `where.exe draco_decoder` 解析到：

```text
E:\Miunaaaa\0-work\code\draco_encoder\draco-1.5.7\build\Release\draco_decoder.exe
```

文件元信息：

| 字段 | 值 |
| --- | --- |
| absolute path | `E:\Miunaaaa\0-work\code\draco_encoder\draco-1.5.7\build\Release\draco_decoder.exe` |
| file size bytes | `398848` |
| SHA-256 | `CA931DFBBD7EA70311F6642147FF495EDD4682C120AF365F797CFACA2EFF3460` |
| Windows FileVersion | unavailable |
| Windows ProductVersion | unavailable |
| CompanyName / ProductName / OriginalFilename | unavailable |

路径目录名包含 `draco-1.5.7`，但 executable 自身未通过 Windows version metadata 或 `--version` 输出提供可审查版本号。本阶段不将目录名单独写成已由 executable 直接报告的版本。

## 3. 实际执行的无输入命令

| 命令 | exit code | 观察摘要 |
| --- | ---: | --- |
| `draco_encoder -h` | `0` | 输出 encoder usage 与 main options。 |
| `draco_encoder --help` | `1` | 输出同类 help 文本，但 exit code 为 1。 |
| `draco_encoder --version` | `1` | 未输出版本号；输出 help 文本。 |
| `draco_decoder -h` | `0` | 输出 decoder usage 与 main options。 |
| `draco_decoder --help` | `1` | 输出同类 help 文本，但 exit code 为 1。 |
| `draco_decoder --version` | `1` | 未输出版本号；输出 help 文本。 |
| `draco_decoder -?` | `0` | 输出 decoder help 文本。 |

## 4. Encoder help 中直接观察到的关键行

本轮只摘录与 input/output、point-cloud mode、`-cl`、`-qc`、`-qp` 相关的行：

```text
Usage: draco_encoder [options] -i input
-i <input>            input file name.
-o <output>           output file name.
-point_cloud          forces the input to be encoded as a point cloud.
-qp <value>           quantization bits for the position attribute, default=11.
-cl <value>           compression level [0-10], most=10, least=0, default=7.
```

同一 help 输出还出现了 `-qt`、`-qn`、`-qg`、`--skip`、`--metadata`、`-preserve_polygons` 等选项；本轮不解释这些选项是否适合当前点云 RGB 资产。

## 5. Decoder help 中直接观察到的关键行

```text
Usage: draco_decoder [options] -i input
-o <output>           output file name.
```

decoder help 中未观察到 point-cloud mode、`-cl`、`-qc`、`-qp` 相关选项；这符合 decoder 主要从输入 DRC 自身读取编码信息的直觉，但本轮不做实际解码验证。

## 6. CLI 确认状态

| 项目 | 当前状态 | 证据 |
| --- | --- | --- |
| encoder 可执行 | confirmed | `draco_encoder -h` exit code `0`。 |
| decoder 可执行 | confirmed | `draco_decoder -h` exit code `0`。 |
| input flag | confirmed | encoder / decoder help 均出现 `-i input`；encoder 还出现 `-i <input>`。 |
| output flag | confirmed | encoder / decoder help 均出现 `-o <output>`。 |
| point-cloud mode flag | confirmed | encoder help 出现 `-point_cloud`。 |
| `-pointcloud` spelling | not confirmed | help 未出现该拼写；不得写成已确认 CLI 写法。 |
| `-cl` | confirmed | encoder help 出现 `-cl <value>`，范围 `[0-10]`，default `7`。 |
| `-qp` | confirmed | encoder help 出现 `-qp <value>`，position attribute default `11`。 |
| `-qc` | CLI_UNRESOLVED | encoder help 未出现 `-qc`；本轮未执行实际编码命令验证其是否被接受。 |
| executable-reported version | CLI_UNRESOLVED | `--version` 未输出版本号，返回 help 文本。 |

## 7. 研究者确认的 pilot candidate family

研究者已确认后续第一版 DRC pilot candidate family：

```text
source_pdl ∈ {0.2, 0.4, 0.6, 0.8, 1.0}
codec = Draco
point-cloud mode = required
cl = 10
qc = 6
qp ∈ {8, 10, 12}
```

其中：

- `cl=10`、`qp={8,10,12}` 的 option 名称可由当前 encoder help 直接观察到；
- point-cloud mode 的当前 CLI 写法可由 help 确认为 `-point_cloud`；
- `qc=6` 是研究者确认的 pilot candidate family 成员，但当前 help 未显示 `-qc`，因此实际 CLI 拼写或是否可执行仍需阶段 2B round-trip probe 验证。

## 8. 尚未验证事项

本阶段尚未确认：

- `draco_encoder` 是否能成功编码当前 binary little-endian PLY tile；
- `-qc 6` 在当前 executable 中的实际可接受性；
- `-point_cloud -cl 10 -qp {8,10,12}` 与 `qc=6` 组合是否可成功执行；
- PLY -> DRC -> PLY round-trip correctness；
- 坐标与 RGB 属性 round-trip 后的解析与保真口径；
- DRC 文件大小；
- decoder runtime / `d_ms`；
- DRC-aware rendered quality 或 `Q_base(i, v)`。

## 9. 后续建议

阶段 2B 应先做受控 DRC round-trip probe：选择少量代表性 non-empty tile，覆盖 `source_pdl × qp` candidate family，验证当前安装 Draco CLI、`-point_cloud` 写法、`qc` 参数可用性、命名与 provenance，再决定是否进入完整 `40 × 15 = 600` 个 DRC 文件的 pilot corpus 生成。
