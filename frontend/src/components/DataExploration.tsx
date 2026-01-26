/**
 * 数据探索可视化组件
 * 提供分布图、箱线图、相关性热力图、趋势分析等
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Tabs,
  Select,
  Space,
  Spin,
  Empty,
  Row,
  Col,
  Statistic,
  Tag,
  Table,
  Tooltip,
  Slider,
  Switch,
  message,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

import {
  getColumnDistribution,
  getCorrelationMatrix,
  getTrendAnalysis,
  compareColumns,
  getDataOverview,
  type DistributionResponse,
  type CorrelationResponse,
  type TrendResponse,
  type CompareResponse,
  type OverviewResponse,
  type ColumnSummary,
} from '@/api/exploration'

const { Text, Title } = Typography

interface DataExplorationProps {
  datasetId: number
  datasetName: string
  columns: string[]
}

export default function DataExploration({ datasetId, datasetName, columns }: DataExplorationProps) {
  const [activeTab, setActiveTab] = useState('overview')
  const [loading, setLoading] = useState(false)

  // 概览数据
  const [overview, setOverview] = useState<OverviewResponse | null>(null)

  // 分布数据
  const [selectedColumn, setSelectedColumn] = useState<string>(columns[0] || '')
  const [distribution, setDistribution] = useState<DistributionResponse | null>(null)
  const [histogramBins, setHistogramBins] = useState(30)

  // 相关性数据
  const [correlation, setCorrelation] = useState<CorrelationResponse | null>(null)
  const [correlationMethod, setCorrelationMethod] = useState<'pearson' | 'spearman' | 'kendall'>(
    'pearson'
  )

  // 趋势数据
  const [trendColumn, setTrendColumn] = useState<string>(columns[0] || '')
  const [trendData, setTrendData] = useState<TrendResponse | null>(null)
  const [trendWindow, setTrendWindow] = useState(10)

  // 对比数据
  const [compareColumnsList, setCompareColumnsList] = useState<string[]>([])
  const [compareData, setCompareData] = useState<CompareResponse | null>(null)
  const [normalizeCompare, setNormalizeCompare] = useState(true)

  // 加载概览
  const loadOverview = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getDataOverview(datasetId)
      setOverview(data)
    } catch {
      message.error('加载数据概览失败')
    } finally {
      setLoading(false)
    }
  }, [datasetId])

  // 加载分布
  const loadDistribution = useCallback(async () => {
    if (!selectedColumn) return
    setLoading(true)
    try {
      const data = await getColumnDistribution(datasetId, selectedColumn, histogramBins)
      setDistribution(data)
    } catch {
      message.error('加载分布数据失败')
    } finally {
      setLoading(false)
    }
  }, [datasetId, selectedColumn, histogramBins])

  // 加载相关性
  const loadCorrelation = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getCorrelationMatrix(datasetId, undefined, correlationMethod)
      setCorrelation(data)
    } catch {
      message.error('加载相关性数据失败')
    } finally {
      setLoading(false)
    }
  }, [datasetId, correlationMethod])

  // 加载趋势
  const loadTrend = useCallback(async () => {
    if (!trendColumn) return
    setLoading(true)
    try {
      const data = await getTrendAnalysis(datasetId, trendColumn, { window: trendWindow })
      setTrendData(data)
    } catch {
      message.error('加载趋势数据失败')
    } finally {
      setLoading(false)
    }
  }, [datasetId, trendColumn, trendWindow])

  // 加载对比
  const loadCompare = useCallback(async () => {
    if (compareColumnsList.length < 2) return
    setLoading(true)
    try {
      const data = await compareColumns(datasetId, compareColumnsList, {
        normalize: normalizeCompare,
      })
      setCompareData(data)
    } catch {
      message.error('加载对比数据失败')
    } finally {
      setLoading(false)
    }
  }, [datasetId, compareColumnsList, normalizeCompare])

  // Tab 切换时加载数据
  useEffect(() => {
    if (activeTab === 'overview' && !overview) {
      loadOverview()
    } else if (activeTab === 'distribution' && selectedColumn) {
      loadDistribution()
    } else if (activeTab === 'correlation' && !correlation) {
      loadCorrelation()
    } else if (activeTab === 'trend' && trendColumn) {
      loadTrend()
    } else if (activeTab === 'compare' && compareColumnsList.length >= 2) {
      loadCompare()
    }
  }, [
    activeTab,
    overview,
    selectedColumn,
    correlation,
    trendColumn,
    compareColumnsList,
    loadOverview,
    loadDistribution,
    loadCorrelation,
    loadTrend,
    loadCompare,
  ])

  // 渲染概览
  const renderOverview = () => {
    if (!overview) return <Empty description="暂无数据" />

    const columnTableColumns: ColumnsType<ColumnSummary> = [
      { title: '列名', dataIndex: 'name', key: 'name', width: 150, ellipsis: true },
      {
        title: '类型',
        dataIndex: 'inferred_type',
        key: 'inferred_type',
        width: 100,
        render: (type: string) => {
          const colorMap: Record<string, string> = {
            numeric: 'blue',
            datetime: 'green',
            categorical: 'orange',
            text: 'default',
            boolean: 'purple',
          }
          return <Tag color={colorMap[type] || 'default'}>{type}</Tag>
        },
      },
      { title: '原始类型', dataIndex: 'dtype', key: 'dtype', width: 100 },
      {
        title: '缺失',
        key: 'missing',
        width: 120,
        render: (_, record) => (
          <span>
            {record.missing} ({(record.missing_ratio * 100).toFixed(1)}%)
          </span>
        ),
      },
      { title: '唯一值', dataIndex: 'unique', key: 'unique', width: 100 },
    ]

    return (
      <div>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="总行数" value={overview.basic_info.rows} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="总列数" value={overview.basic_info.columns} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="数值列" value={overview.numeric_columns.length} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="内存占用"
                value={overview.basic_info.memory_mb.toFixed(2)}
                suffix="MB"
              />
            </Card>
          </Col>
        </Row>

        <Card title="列信息" size="small" style={{ marginTop: 16 }}>
          <Table
            columns={columnTableColumns}
            dataSource={overview.column_summary}
            rowKey="name"
            size="small"
            pagination={false}
            scroll={{ y: 300 }}
          />
        </Card>
      </div>
    )
  }

  // 渲染分布图
  const renderDistribution = () => {
    if (!distribution) return <Empty description="请选择列查看分布" />

    if (distribution.type === 'categorical') {
      // 分类变量 - 柱状图
      const option: EChartsOption = {
        title: { text: `${distribution.column} 值分布`, left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: distribution.value_counts.map((v) => v.value),
          axisLabel: { rotate: 45, interval: 0 },
        },
        yAxis: { type: 'value', name: '数量' },
        series: [
          {
            type: 'bar',
            data: distribution.value_counts.map((v) => v.count),
            itemStyle: { color: '#5470c6' },
          },
        ],
        grid: { bottom: 80 },
      }

      return (
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Statistic title="总数" value={distribution.total_count} />
            </Col>
            <Col span={8}>
              <Statistic title="唯一值" value={distribution.unique_count} />
            </Col>
            <Col span={8}>
              <Statistic title="缺失" value={distribution.missing_count} />
            </Col>
          </Row>
          <ReactECharts option={option} style={{ height: 400 }} />
        </div>
      )
    }

    // 数值变量 - 直方图 + 箱线图
    const histogramOption: EChartsOption = {
      title: { text: `${distribution.column} 分布直方图`, left: 'center' },
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          const p = (params as { data: number; dataIndex: number }[])[0]
          const bin = distribution.histogram[p.dataIndex]
          return `区间: [${bin.bin_start.toFixed(2)}, ${bin.bin_end.toFixed(2)})<br/>数量: ${bin.count}<br/>占比: ${(bin.ratio * 100).toFixed(1)}%`
        },
      },
      xAxis: {
        type: 'category',
        data: distribution.histogram.map((b) => b.bin_start.toFixed(2)),
        axisLabel: { rotate: 45 },
      },
      yAxis: { type: 'value', name: '数量' },
      series: [
        {
          type: 'bar',
          data: distribution.histogram.map((b) => b.count),
          itemStyle: { color: '#91cc75' },
        },
      ],
      grid: { bottom: 80 },
    }

    const boxplotOption: EChartsOption = {
      title: { text: '箱线图', left: 'center' },
      tooltip: { trigger: 'item' },
      xAxis: { type: 'category', data: [distribution.column] },
      yAxis: { type: 'value' },
      series: [
        {
          type: 'boxplot',
          data: [
            [
              distribution.boxplot.min,
              distribution.boxplot.q1,
              distribution.boxplot.median,
              distribution.boxplot.q3,
              distribution.boxplot.max,
            ],
          ],
        },
        {
          type: 'scatter',
          data: distribution.boxplot.outliers.map((v) => [distribution.column, v]),
          itemStyle: { color: '#ee6666' },
        },
      ],
    }

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Statistic title="最小值" value={distribution.stats.min.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="最大值" value={distribution.stats.max.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="均值" value={distribution.stats.mean.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="标准差" value={distribution.stats.std.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="偏度" value={distribution.stats.skewness?.toFixed(4) || '-'} />
          </Col>
          <Col span={4}>
            <Statistic title="峰度" value={distribution.stats.kurtosis?.toFixed(4) || '-'} />
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={16}>
            <ReactECharts option={histogramOption} style={{ height: 350 }} />
          </Col>
          <Col span={8}>
            <ReactECharts option={boxplotOption} style={{ height: 350 }} />
          </Col>
        </Row>
      </div>
    )
  }

  // 渲染相关性热力图
  const renderCorrelation = () => {
    if (!correlation) return <Empty description="暂无相关性数据" />

    const heatmapData: [number, number, number | null][] = []
    correlation.matrix.forEach((row, i) => {
      row.forEach((val, j) => {
        heatmapData.push([j, i, val])
      })
    })

    const option: EChartsOption = {
      title: { text: `相关性矩阵 (${correlation.method})`, left: 'center' },
      tooltip: {
        formatter: (params: unknown) => {
          const p = params as { data: [number, number, number | null] }
          const val = p.data[2]
          return `${correlation.columns[p.data[0]]} vs ${correlation.columns[p.data[1]]}<br/>相关系数: ${val?.toFixed(4) || 'N/A'}`
        },
      },
      xAxis: {
        type: 'category',
        data: correlation.columns,
        axisLabel: { rotate: 45, interval: 0 },
      },
      yAxis: {
        type: 'category',
        data: correlation.columns,
      },
      visualMap: {
        min: -1,
        max: 1,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: [
            '#313695',
            '#4575b4',
            '#74add1',
            '#abd9e9',
            '#e0f3f8',
            '#ffffbf',
            '#fee090',
            '#fdae61',
            '#f46d43',
            '#d73027',
            '#a50026',
          ],
        },
      },
      series: [
        {
          type: 'heatmap',
          data: heatmapData,
          label: {
            show: correlation.columns.length <= 10,
            formatter: (params: unknown) => {
              const p = params as { data: [number, number, number | null] }
              return p.data[2]?.toFixed(2) || ''
            },
          },
        },
      ],
      grid: { bottom: 80, top: 60 },
    }

    return (
      <div>
        <ReactECharts option={option} style={{ height: 500 }} />
        {correlation.strong_correlations.length > 0 && (
          <Card title="强相关对" size="small" style={{ marginTop: 16 }}>
            <Space wrap>
              {correlation.strong_correlations.slice(0, 10).map((c, i) => (
                <Tooltip key={i} title={`相关系数: ${c.correlation.toFixed(4)}`}>
                  <Tag color={c.correlation > 0 ? 'red' : 'blue'}>
                    {c.column1} ↔ {c.column2}: {c.correlation.toFixed(2)}
                  </Tag>
                </Tooltip>
              ))}
            </Space>
          </Card>
        )}
      </div>
    )
  }

  // 渲染趋势图
  const renderTrend = () => {
    if (!trendData) return <Empty description="请选择列查看趋势" />

    const option: EChartsOption = {
      title: { text: `${trendColumn} 趋势分析`, left: 'center' },
      tooltip: { trigger: 'axis' },
      legend: { data: ['原始数据', '移动平均', '趋势线'], bottom: 0 },
      xAxis: { type: 'value', name: '索引' },
      yAxis: { type: 'value' },
      series: [
        {
          name: '原始数据',
          type: 'line',
          data: trendData.raw_data,
          symbol: 'none',
          lineStyle: { width: 1, opacity: 0.5 },
        },
        {
          name: '移动平均',
          type: 'line',
          data: trendData.moving_avg,
          symbol: 'none',
          lineStyle: { width: 2 },
        },
        {
          name: '趋势线',
          type: 'line',
          data: trendData.trend_line,
          symbol: 'none',
          lineStyle: { width: 2, type: 'dashed' },
        },
      ],
      dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    }

    const trendColor =
      trendData.stats.trend_direction === 'increasing'
        ? 'green'
        : trendData.stats.trend_direction === 'decreasing'
          ? 'red'
          : 'default'

    return (
      <div>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Statistic title="最小值" value={trendData.stats.min.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="最大值" value={trendData.stats.max.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="均值" value={trendData.stats.mean.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="标准差" value={trendData.stats.std.toFixed(4)} />
          </Col>
          <Col span={4}>
            <Statistic title="斜率" value={trendData.stats.trend_slope.toExponential(2)} />
          </Col>
          <Col span={4}>
            <Card size="small">
              <Text>趋势方向</Text>
              <div>
                <Tag color={trendColor} style={{ marginTop: 8 }}>
                  {trendData.stats.trend_direction === 'increasing'
                    ? '↑ 上升'
                    : trendData.stats.trend_direction === 'decreasing'
                      ? '↓ 下降'
                      : '→ 平稳'}
                </Tag>
              </div>
            </Card>
          </Col>
        </Row>
        <ReactECharts option={option} style={{ height: 400 }} />
      </div>
    )
  }

  // 渲染对比图
  const renderCompare = () => {
    if (!compareData || compareData.series.length === 0) {
      return <Empty description="请选择至少2列进行对比" />
    }

    const option: EChartsOption = {
      title: { text: '多列对比', left: 'center' },
      tooltip: { trigger: 'axis' },
      legend: { data: compareData.series.map((s) => s.name), bottom: 0 },
      xAxis: { type: 'value', name: '索引' },
      yAxis: { type: 'value', name: normalizeCompare ? '归一化值' : '原始值' },
      series: compareData.series.map((s) => ({
        name: s.name,
        type: 'line',
        data: s.data.filter((d) => d[1] !== null),
        symbol: 'none',
      })),
      dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    }

    return (
      <div>
        <ReactECharts option={option} style={{ height: 400 }} />
        <Card title="统计对比" size="small" style={{ marginTop: 16 }}>
          <Table
            columns={[
              { title: '列名', dataIndex: 'column', key: 'column' },
              {
                title: '最小值',
                dataIndex: 'min',
                key: 'min',
                render: (v: number) => v.toFixed(4),
              },
              {
                title: '最大值',
                dataIndex: 'max',
                key: 'max',
                render: (v: number) => v.toFixed(4),
              },
              {
                title: '均值',
                dataIndex: 'mean',
                key: 'mean',
                render: (v: number) => v.toFixed(4),
              },
              {
                title: '标准差',
                dataIndex: 'std',
                key: 'std',
                render: (v: number) => v.toFixed(4),
              },
              { title: '有效数', dataIndex: 'valid_count', key: 'valid_count' },
            ]}
            dataSource={compareData.stats}
            rowKey="column"
            size="small"
            pagination={false}
          />
        </Card>
      </div>
    )
  }

  const tabItems = [
    {
      key: 'overview',
      label: '数据概览',
      children: <Spin spinning={loading}>{renderOverview()}</Spin>,
    },
    {
      key: 'distribution',
      label: '分布分析',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <span>选择列:</span>
            <Select
              value={selectedColumn}
              onChange={(v) => {
                setSelectedColumn(v)
                setDistribution(null)
              }}
              style={{ width: 200 }}
              options={columns.map((c) => ({ label: c, value: c }))}
            />
            <span>分箱数:</span>
            <Slider
              value={histogramBins}
              onChange={setHistogramBins}
              min={5}
              max={100}
              style={{ width: 150 }}
            />
            <span>{histogramBins}</span>
          </Space>
          <Spin spinning={loading}>{renderDistribution()}</Spin>
        </div>
      ),
    },
    {
      key: 'correlation',
      label: '相关性分析',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <span>计算方法:</span>
            <Select
              value={correlationMethod}
              onChange={(v) => {
                setCorrelationMethod(v)
                setCorrelation(null)
              }}
              style={{ width: 150 }}
              options={[
                { label: 'Pearson', value: 'pearson' },
                { label: 'Spearman', value: 'spearman' },
                { label: 'Kendall', value: 'kendall' },
              ]}
            />
          </Space>
          <Spin spinning={loading}>{renderCorrelation()}</Spin>
        </div>
      ),
    },
    {
      key: 'trend',
      label: '趋势分析',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <span>选择列:</span>
            <Select
              value={trendColumn}
              onChange={(v) => {
                setTrendColumn(v)
                setTrendData(null)
              }}
              style={{ width: 200 }}
              options={columns.map((c) => ({ label: c, value: c }))}
            />
            <span>移动平均窗口:</span>
            <Slider
              value={trendWindow}
              onChange={setTrendWindow}
              min={2}
              max={100}
              style={{ width: 150 }}
            />
            <span>{trendWindow}</span>
          </Space>
          <Spin spinning={loading}>{renderTrend()}</Spin>
        </div>
      ),
    },
    {
      key: 'compare',
      label: '多列对比',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <span>选择列 (2-5列):</span>
            <Select
              mode="multiple"
              value={compareColumnsList}
              onChange={(v) => {
                if (v.length <= 5) {
                  setCompareColumnsList(v)
                  setCompareData(null)
                }
              }}
              style={{ width: 400 }}
              options={columns.map((c) => ({ label: c, value: c }))}
              maxTagCount={3}
            />
            <span>归一化:</span>
            <Switch
              checked={normalizeCompare}
              onChange={(v) => {
                setNormalizeCompare(v)
                setCompareData(null)
              }}
            />
          </Space>
          <Spin spinning={loading}>{renderCompare()}</Spin>
        </div>
      ),
    },
  ]

  return (
    <Card
      title={
        <Space>
          <Title level={5} style={{ margin: 0 }}>
            📊 数据探索
          </Title>
          <Text type="secondary">{datasetName}</Text>
        </Space>
      }
      size="small"
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </Card>
  )
}
