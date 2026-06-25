# Stage2 composite DRC variant 理论接口交接说明

## 1. 问题背景与术语消歧

当前数据准备项目已经生成 frame 1051 的五档 tile-local binary PLY source assets，但尚未生成 DRC。阶段 2A 冻结了后续 DRC pilot candidate family 的数据准备侧语义，并将其对 Stage2 理论接口的影响记录在本文档中。

当前存在两个容易混淆的概念：

```text
source_pdl / ρ：
点密度比例，
取值为 0.2、0.4、0.6、0.8、1.0。

Q_base(i, v)：
tile i 在 composite representation variant v 下的基础质量收益。
```

后续理论与 solver-side 文档不应继续用同一个 `q` 同时表示 PDL 和 `q_{i,j}` 的基础质量收益。建议使用：

```text
ρ 或 source_pdl：点密度轴。
v：具体 representation variant。
Q_base(i, v)：variant 的基础视觉质量收益。
R(i, v)：对应 DRC encoded file size。
D(i, v)：目标端侧条件下的 decode cost。
```

本轮在当前数据准备仓库中未找到 `work1_stage2.md`。该文件应视为当前数据准备仓库之外的理论基线文档；本文档仅根据研究者已确认的模型语义与阶段 2A 接口问题记录交接事项，不替代对 solver 文档的正式修订。本轮不修改 `work1_stage2.md`，也不修改 Stage2 solver 仓库。

## 2. 从 PDL-only quality level 到 composite variant

当前 PLY-only distance calibration 只比较 nested-PDL PLY，没有测量 Draco geometry quantization、color quantization、DRC bytes、DRC decode cost 或 DRC round-trip visual quality。

因此，当前 calibration 只能提供：

```text
distance -> PDL sensitivity / PDL reference evidence
```

不能直接提供：

```text
distance -> final composite DRC variant 的已验证映射
```

阶段 2A 数据准备侧确认的后续 raw candidate set 可表达为：

```text
V_i^raw =
{
  v = (source_pdl, codec profile)
  | source_pdl ∈ {0.2,0.4,0.6,0.8,1.0},
    qp ∈ {8,10,12},
    cl=10,
    qc=6,
    point-cloud mode required,
    asset available for tile i
}
```

`v` 不要求天然全序；不能只通过 `variant_id`、PDL 数值或 qp 数值判断哪个 variant 一定“更高质量”。例如：

```text
pdl_0.8_qp12
pdl_1.0_qp8
```

在实际 DRC bytes、decode cost 与 rendered quality 上可能不可直接比较。它们需要在 DRC corpus、round-trip verification、file size、decode cost 与质量证据建立后再进入 solver-side 语义冻结。

## 3. MCKP 与拉格朗日框架仍然适用

candidate 从 5 个 PDL 扩展为约 15 个 composite variants，不会破坏当前分块可分解框架。后续固定乘子下的单 tile 选择可抽象为：

```text
v_i*(λ)
=
argmax over v in V_i(d_i)
[
  spatial_weight_i × Q_base(i, v)
  - η D(i, v)
  - λ R(i, v)
]
```

MCKP 与固定 `λ` 下的单 tile candidate scan 不要求候选具有全序质量等级。只要每次求解开始前，每个 tile 的 candidate set `V_i(d_i)` 固定，且 tie-breaking 规则确定，总数据需求关于 `λ` 的单调不增性质与一维乘子搜索结构仍可保留。

主体复杂度仍为：

```text
O(I_max × sum_i |V_i(d_i)|)
```

若每个参与 tile 有 15 个候选，则只是 `M` 从约 5 增加到约 15，并不回到指数级全组合枚举。

理论边界仍需保留：该方法仍是面向原始整数 MCKP 的低复杂度可行整数近似结构；不因 candidate 变为 composite variants 而自动获得全局最优性。

## 4. 当前 lookup cap 语义问题

当前 PLY-only calibration 的核心结果更接近：

```text
在特定 distance / view / renderer 条件下，
满足阈值的最低可接受 source_pdl reference。
```

它不自动等价于：

```text
candidate quality upper cap
```

后续 solver-side 需要明确区分至少两个概念：

```text
ρ_min_acceptable(d)：
满足当前 PLY-only threshold 的最低 source_pdl reference。

ρ_max_useful(d)：
继续提高 source_pdl 是否仍具有可观边际收益的上限，
这一概念不能仅由“最低可接受 PDL”直接推出。
```

当前 `j_max_dist(d)` 与：

```text
M_i(d) = {1, ..., j_max_dist(d)}
```

在 composite variant space 中存在以下问题：

1. variant 不再天然构成按 quality level 排列的前缀集合；
2. PLY-only lookup 没有验证 qp 对应的 Draco loss；
3. 若把当前 PLY lookup 直接作为 DRC hard cap，可能错误排除实际仍有价值的 composite variant；
4. 当前 lookup 结果可以暂时作为 PDL reference、soft utility prior 或未来候选过滤研究的输入，但不能在没有 DRC evidence 的情况下直接称为 composite DRC variant hard cap。

后续 solver-side 需要选择并验证的方向包括：

```text
A. 作为 hard candidate filter；
B. 作为 source_pdl lower-bound / reference；
C. 作为 soft utility modulation；
D. 作为 G(d) 的辅助输入；
E. 其他明确的 hybrid rule。
```

此项尚未冻结。本轮不修改现有 solver lookup contract；当前数据准备项目不应把 DRC corpus 预先按 lookup cap 删减。

## 5. 局部增量修正的 variant-aware 问题

当前以：

```text
j > j_i
```

定义“升级”的表达只适用于质量档位天然全序的情况。在 composite variant space 中，局部修正应在后续 solver-side 改写为：

```text
当前 tile i 选择 v_i。

对任意其他可用 variant：
v ∈ V_i(d_i), v != v_i

ΔR_i(v) = R(i, v) - R(i, v_i)
ΔUhat_i(v) = Uhat(i, v) - Uhat(i, v_i)
```

只将以下候选视为 residual-budget upgrade：

```text
0 < ΔR_i(v) <= B_res
且
ΔUhat_i(v) > 0
```

并按：

```text
ΔUhat_i(v) / ΔR_i(v)
```

选择候选。

不再用 `v` 的编号更大、PDL 更大或 qp 更大来定义“升级”。每一次 variant switch 后，应以新的 current variant 为基准重新计算该 tile 的可行增量。

资源更低但净效用更高的 variant，不属于 residual-budget upgrade；它属于固定 `λ` 选择或其他明确修正机制的候选，不应被局部“升级”步骤错误处理。

## 6. Pareto pruning 的位置与条件

offline candidate pruning 的正确位置是：

```text
DRC corpus 生成、round-trip verification、
R / D / Q_base 或明确 proxy 得到后，
在每个 tile 的候选集合内执行。
```

对同一 tile 的两个 composite variants `a` 与 `b`，若：

```text
R(i, a) <= R(i, b)
D(i, a) <= D(i, b)
Q_base(i, a) >= Q_base(i, b)
```

且至少一个不等式严格成立，则可将 `b` 记为被 `a` Pareto-dominated 的候选。

必须强调：

- Pareto pruning 不能仅靠 PDL 或 qp 标签执行；
- 不能在 DRC 未生成、未验证、`Q_base` 与 `D` 尚无 measured / accepted proxy 时提前执行；
- pruning 是离线 candidate-set reduction，不是在线拉格朗日求解步骤；
- pruning 后每个参与 Stage2 的 tile 仍必须保留至少一个可用 delivery candidate。

## 7. 数据准备为什么不被阻塞

lookup cap 的重解释、variant-aware local repair、Pareto pruning、solver-side `variant_id` 接口调整，属于 Stage2 理论与实现接口问题。

它们不阻塞当前 data-prep project 继续进行以下工作：

1. 生成完整的 `PDL × qp` DRC raw candidate corpus；
2. 验证 PLY -> DRC -> PLY round-trip correctness；
3. 记录每个 DRC asset 的 `source_pdl` 与 codec profile provenance；
4. 采集 DRC encoded file size；
5. 为后续 target-side decode cost / quality evidence 建立数据基础。

当前 data-prep 不负责：

- 决定最终 online candidate filtering；
- 决定 distance lookup 的 hard / soft 语义；
- 决定最终 `Q_base` 估计方法；
- 决定最终 `D(i, v)` 的端侧 benchmark 口径；
- 修改 Stage2 solver。

因此，solver-side 理论问题不阻塞当前 DRC data-prep，但会阻塞把 lookup / pruning 直接写入最终 Stage2 solver contract。进入正式 solver contract 前，需要补齐 DRC evidence，并由研究者确认 lookup projection、candidate filtering、variant-aware repair 与 Pareto pruning 的最终规则。
