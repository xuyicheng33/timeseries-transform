# 15分钟训练表合并方法说明（station_id=41，气象取均值，忽略风向）

这份说明用于把两类原始 CSV：

- 气象实测：`weatherdata/powerforecast_fd_weatherdata_YYYYMMDD.csv`
- 功率（预测/实测/容量）：`shortforecast/powerforecast_short_YYYYMMDD.csv`

合并成一张可用于“15分钟短期功率预测/校正”的训练表（监督学习样本表）。

本包中已经包含一个可复现的小样例（原始行 + 合并后的行），见同目录下：

- `example_weatherdata_rows.csv`
- `example_shortforecast_rows.csv`
- `example_merged_row.csv`

对应的整表（你将发给专家的合并表）是：

- `train_15m_station41_simple_v4.csv`（与本说明同目录）

---

## 1. 训练表每一行代表什么

对每个电站（这里固定 `station_id=41`），在每个 15 分钟时刻 `t`（例如 `00:15:00`）构造一行样本：

- **特征（X）**：只使用 `t` 及之前可获得的数据（气象过去 15 分钟平均、当前/上一刻实际功率、以及截至 `t` 时刻可用的原系统预测）。
- **标签（y）**：`t+15分钟` 时刻的实际功率。

因此这是一张“预测提前量 = 15分钟”的训练样本表。

---

## 2. 使用到的原始字段（两张表）

### 2.1 气象表（weatherdata）

关键字段：

- `stationid`：电站 ID
- `datatime`：气象观测时间（你这批数据是 **每5分钟** 一条）
- `temperature, humidity, pressure`：温湿压
- `ws_10, ws_30, ws_50, ws_70, ws_hub`：不同高度风速

说明：本版本**忽略风向**字段 `wd_*`（后续需要可再加入，用 sin/cos 方式更合理）。

### 2.2 功率表（shortforecast）

关键字段：

- `stationid`：电站 ID
- `forecast_fromtime`：这次预测“生成/起报”的时间点
- `forecastvaluetime`：预测对应的“目标时刻”
- `forecastvalue`：在 `forecastvaluetime` 的预测功率（原系统输出）
- `actualvaluetime`：实际功率记录时间（常比整点有几秒偏差）
- `actualvalue`：实际功率
- `runningcapacity`：运行/可用容量（功率上限相关）

---

## 3. 过滤规则（为什么只做 station_id=41）

数据里 `stationid` 同时出现了 `41` 和 `0`。通常 `0` 更像占位/无效站点。

本训练表先做最干净的一版：**只保留 `stationid=41`**。

如需多站点合并，只要把过滤条件去掉即可。

---

## 4. 时间对齐规则（核心）

### 4.1 定义 15 分钟格点

定义所有 `t` 都落在：`00/15/30/45` 分钟的整点。

### 4.2 实际功率（actual）对齐到 15 分钟

因为 `actualvaluetime` 有秒级偏差（如 `00:14:23`、`00:28:58`），不能直接当作整点。

做法：把 `actualvaluetime` **就近四舍五入**到最近的 15 分钟格点，作为该条实际功率所属的 `t`。

然后对同一 `t` 可能出现的多条 `actualvalue`，取**中位数**作为该 `t` 的实际功率：

> `actual(t) = median( all actualvalue aligned to t )`

（用中位数是为了更稳健，减少重复/异常记录的影响。）

---

## 5. 气象特征：过去15分钟均值（只用历史，不穿越）

对于每个样本时刻 `t`，取气象窗口 `(t-15min, t]` 内的 5 分钟观测点。

在你这批数据里，通常正好是 3 个时间点：

- `t-10min`
- `t-5min`
- `t`

对每个气象字段（温湿压、各高度风速）做均值：

> `x_weather(t) = mean( weather(t), weather(t-5), weather(t-10) )`

如果缺少任意一个点（例如某次缺测），该样本行会被丢弃（避免引入不一致的特征）。

---

## 6. 标签与功率相关特征（15分钟预测）

对每个 `t`：

- `time = t`
- `time_plus_15m = t + 15min`

训练标签（要预测的真实答案）：

- `actual_plus_15m = actual(time_plus_15m)`

功率滞后特征（用于捕捉惯性/趋势）：

- `actual_now = actual(time)`
- `actual_minus_15m = actual(time - 15min)`

容量（可做约束/归一化，也可当特征）：

- `running_capacity = runningcapacity(time_plus_15m)`（同样可能有多条，取中位数）

---

## 7. “原系统预测值”是怎么合并的（避免用未来信息）

原始数据里，同一个 `forecastvaluetime`（目标时刻）会有很多条预测，差别在于 `forecast_fromtime`（起报时间）不同。

我们希望在训练表的每一行 `t` 上，只使用**截至 t 时刻已经发布过的预测**，不能偷看未来才发布的预测。

因此对每一行：

- 目标时刻固定：`target = time_plus_15m`
- 在所有满足 `forecastvaluetime == target` 的预测里，选择 `forecast_fromtime <= time` 的**最新一条**（最大的 `forecast_fromtime`）

写入两列：

- `forecast_plus_15m`：选中的 `forecastvalue`（同一键可能多条，取中位数）
- `forecast_issue_time`：选中的 `forecast_fromtime`（方便专家检查“用了哪次起报的预测”）

### 为什么不是“固定取 15 分钟前的预测”？

如果强行规定 `forecast_fromtime == time`（也就是“刚好 t 时刻生成的预测”），在你这批数据里大多数 `t` 根本没有对应的起报时间（预测通常是按批次生成，不是每 15 分钟生成一次）。

所以更贴近真实线上逻辑的是：“用当时能拿到的最新预测”，而不是“必须 15 分钟前刚好出了一版预测”。

---

## 8. 输出训练表字段（`train_15m_station41_simple_v4.csv`）

每列含义如下（数值均保留两位小数）：

- `station_id`：电站 ID（41）
- `time`：样本时刻 `t`
- `time_plus_15m`：目标时刻 `t+15分钟`
- `actual_plus_15m`：目标时刻实际功率（标签 y）
- `actual_now`：当前时刻实际功率
- `actual_minus_15m`：上一刻（15分钟前）实际功率
- `forecast_plus_15m`：截至 `time` 可用的、对 `time_plus_15m` 的原系统预测功率
- `forecast_issue_time`：上述预测来自哪次起报（`forecast_fromtime`）
- `running_capacity`：目标时刻容量
- `temperature, humidity, pressure`：过去15分钟气象均值
- `ws10, ws30, ws50, ws70, ws_hub`：过去15分钟各高度风速均值

---

## 9. 样例：用原始行推导出一行训练样本（可逐项核对）

样例选择：

- `station_id = 41`
- `time = 2024-11-21 00:15:00`
- `time_plus_15m = 2024-11-21 00:30:00`

### 9.1 气象均值如何得到

见 `example_weatherdata_rows.csv`（3 条 5 分钟观测）：

- `00:05`、`00:10`、`00:15`

例如温度：

- `(7.63 + 6.87 + 6.76) / 3 = 7.0866... => 7.09`

湿度：

- `(82.00 + 84.33 + 85.04) / 3 = 83.79`

气压：

- `(1043.43 + 1030.98 + 1003.88) / 3 = 1026.096... => 1026.10`

其它风速同理，得到训练表中的 `temperature/humidity/pressure/ws*`。

### 9.2 实际功率、容量、原预测如何得到

见 `example_shortforecast_rows.csv`（同一批次文件 `DPDFDC_DQ_20241121_0000.WPD`）：

- `actual_now` 来自 `forecastvaluetime=00:15` 这一时刻对应的 `actualvalue=-0.10047 => -0.10`
- `actual_plus_15m` 来自 `forecastvaluetime=00:30` 这一时刻对应的 `actualvalue=0.334898 => 0.33`
- `running_capacity` 来自目标时刻对应记录的 `runningcapacity=96 => 96.00`
- `forecast_plus_15m` 取 `forecastvaluetime=00:30` 的 `forecastvalue=3.08`
- `forecast_issue_time=2024-11-21 00:00:00` 表示这条预测是 `00:00` 这次起报发布的（且在 `00:15` 时刻已可用）

> 注意：实际功率的记录时间 `actualvaluetime` 有秒级偏差（例如 `00:14:23`、`00:28:58`），这也是我们要做 15 分钟对齐的原因。

### 9.3 合并后的结果行

见 `example_merged_row.csv`，应能逐项对应上面推导的值。
