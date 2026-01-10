/**
 * 可视化对比页面
 * 功能：多模型曲线对比、评估指标展示、误差分析、雷达图
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  Card,
  Select,
  Button,
  Space,
  Table,
  InputNumber,
  Slider,
  Row,
  Col,
  Typography,
  Divider,
  Empty,
  Spin,
  Alert,
  message,
  Tabs,
  Tooltip,
  Tag,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  LineChartOutlined,
  DownloadOutlined,
  ReloadOutlined,
  WarningOutlined,
  RadarChartOutlined,
  BarChartOutlined,
  FileExcelOutlined,
  FilterOutlined,
  TrophyOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

import type { 
  Result, 
  Dataset,
  Metrics, 
  CompareResponse, 
  DownsampleAlgorithm,
  ErrorAnalysisResponse,
  RadarChartResponse,
  RangeMetricsResponse,
} from '@/types'
import { getAllResults } from '@/api/results'
import { getAllDatasets } from '@/api/datasets'
import { 
  compareResults, 
  analyzeErrors, 
  getRadarChart,
  calculateRangeMetrics,
  exportCompareCSV,
} from '@/api/visualization'
import { formatMetric } from '@/utils/format'
import { APP_CONFIG } from '@/config/app'
import { DOWNSAMPLE_ALGORITHM_OPTIONS, METRIC_NAMES } from '@/constants'
import ConfigComparison from '@/components/ConfigComparison'

const { Title, Text } = Typography

// 颜色配置
const CHART_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#48b8d0',
]

// 雷达图指标配置
const RADAR_INDICATORS = [
  { name: 'MSE', key: 'mse_score', max: 1 },
  { name: 'RMSE', key: 'rmse_score', max: 1 },
  { name: 'MAE', key: 'mae_score', max: 1 },
  { name: 'R²', key: 'r2_score', max: 1 },
  { name: 'MAPE', key: 'mape_score', max: 1 },
]

export default function Visualization() {
  // ============ 状态定义 ============
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [results, setResults] = useState<Result[]>([])
  const [datasetsLoading, setDatasetsLoading] = useState(false)
  const [resultsLoading, setResultsLoading] = useState(false)

  // 筛选条件
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | undefined>(undefined)
  
  // 选中的结果
  const [selectedResultIds, setSelectedResultIds] = useState<number[]>([])

  // 降采样配置
  const [maxPoints, setMaxPoints] = useState(APP_CONFIG.VISUALIZATION.DEFAULT_POINTS)
  const [algorithm, setAlgorithm] = useState<DownsampleAlgorithm>('lttb')

  // 对比数据
  const [compareData, setCompareData] = useState<CompareResponse | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)

  // 误差分析数据
  const [errorData, setErrorData] = useState<ErrorAnalysisResponse | null>(null)
  const [errorLoading, setErrorLoading] = useState(false)

  // 雷达图数据
  const [radarData, setRadarData] = useState<RadarChartResponse | null>(null)
  const [radarLoading, setRadarLoading] = useState(false)

  // 区间选择
  const [rangeStart, setRangeStart] = useState<number | null>(null)
  const [rangeEnd, setRangeEnd] = useState<number | null>(null)
  const [rangeMetrics, setRangeMetrics] = useState<RangeMetricsResponse | null>(null)
  const [rangeLoading, setRangeLoading] = useState(false)

  // 当前 Tab
  const [activeTab, setActiveTab] = useState('curve')

  // ECharts 实例引用
  const chartRef = useRef<ReactECharts>(null)
  const residualChartRef = useRef<ReactECharts>(null)
  const histogramChartRef = useRef<ReactECharts>(null)
  const radarChartRef = useRef<ReactECharts>(null)

  // ============ 数据获取 ============
  const fetchDatasets = useCallback(async () => {
    setDatasetsLoading(true)
    try {
      const data = await getAllDatasets()
      setDatasets(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setDatasetsLoading(false)
    }
  }, [])

  const fetchResults = useCallback(async () => {
    setResultsLoading(true)
    try {
      const data = await getAllResults(selectedDatasetId)
      setResults(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setResultsLoading(false)
    }
  }, [selectedDatasetId])

  useEffect(() => {
    fetchDatasets()
  }, [fetchDatasets])

  useEffect(() => {
    fetchResults()
    // 切换数据集时清空选择
    setSelectedResultIds([])
    setCompareData(null)
    setErrorData(null)
    setRadarData(null)
    setRangeMetrics(null)
  }, [fetchResults, selectedDatasetId])

  // 筛选后的结果列表
  const filteredResults = useMemo(() => {
    if (!selectedDatasetId) return results
    return results.filter(r => r.dataset_id === selectedDatasetId)
  }, [results, selectedDatasetId])

  // ============ 对比功能 ============
  const handleCompare = async () => {
    if (selectedResultIds.length === 0) {
      message.warning('请至少选择一个结果')
      return
    }

    setCompareLoading(true)
    setErrorLoading(true)
    setRadarLoading(true)

    try {
      // 并行请求所有数据
      const [compareRes, errorRes, radarRes] = await Promise.all([
        compareResults({
          result_ids: selectedResultIds,
          max_points: maxPoints,
          algorithm,
        }),
        analyzeErrors({
          result_ids: selectedResultIds,
        }),
        getRadarChart({
          result_ids: selectedResultIds,
          max_points: maxPoints,
          algorithm,
        }),
      ])

      setCompareData(compareRes)
      setErrorData(errorRes)
      setRadarData(radarRes)
      setRangeMetrics(null)
      setRangeStart(null)
      setRangeEnd(null)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setCompareLoading(false)
      setErrorLoading(false)
      setRadarLoading(false)
    }
  }

  // ============ 区间指标计算 ============
  const handleRangeMetrics = async () => {
    if (rangeStart === null || rangeEnd === null) {
      message.warning('请输入有效的区间范围')
      return
    }
    if (rangeStart >= rangeEnd) {
      message.warning('起始索引必须小于结束索引')
      return
    }
    if (selectedResultIds.length === 0) {
      message.warning('请先选择结果并开始对比')
      return
    }

    setRangeLoading(true)
    try {
      const data = await calculateRangeMetrics({
        result_ids: selectedResultIds,
        start_index: rangeStart,
        end_index: rangeEnd,
      })
      setRangeMetrics(data)
      message.success(`区间 [${rangeStart}, ${rangeEnd}] 指标计算完成`)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setRangeLoading(false)
    }
  }

  // ============ 导出功能 ============
  const handleExportCSV = async () => {
    if (selectedResultIds.length === 0) {
      message.warning('请先选择结果')
      return
    }

    try {
      const blob = await exportCompareCSV({
        result_ids: selectedResultIds,
        max_points: maxPoints,
        algorithm,
      })
      
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `comparison_export_${Date.now()}.csv`
      link.click()
      window.URL.revokeObjectURL(url)
      
      message.success('数据已导出')
    } catch {
      message.error('导出失败')
    }
  }

  const handleExportChart = (type: 'png' | 'jpg') => {
    const chartInstance = chartRef.current?.getEchartsInstance()
    if (!chartInstance) {
      message.error('图表未加载')
      return
    }

    const url = chartInstance.getDataURL({
      type: type === 'jpg' ? 'jpeg' : 'png',
      pixelRatio: 2,
      backgroundColor: '#fff',
    })

    const link = document.createElement('a')
    link.download = `visualization_compare.${type}`
    link.href = url
    link.click()

    message.success(`图表已导出为 ${type.toUpperCase()}`)
  }

  // ============ 图表配置 ============
  const getChartOption = (): EChartsOption => {
    if (!compareData?.chart_data?.series?.length) {
      return {}
    }

    const series = compareData.chart_data.series.map((s, index) => {
      const isTrueLine = s.name.startsWith('True')
      const seriesColor = isTrueLine ? '#333' : CHART_COLORS[index % CHART_COLORS.length]
      
      return {
        name: s.name,
        type: 'line' as const,
        data: s.data,
        smooth: false,
        symbol: 'none',
        lineStyle: {
          width: isTrueLine ? 2 : 1.5,
          type: 'solid' as const,
          color: seriesColor,
        },
        itemStyle: {
          color: seriesColor,
        },
      }
    })

    return {
      title: {
        text: '预测结果对比',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      legend: {
        data: series.map((s) => s.name),
        top: 30,
        type: 'scroll',
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true,
      },
      toolbox: {
        feature: {
          dataZoom: {
            yAxisIndex: 'none',
          },
          restore: {},
          saveAsImage: {
            name: 'visualization_compare',
          },
        },
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        },
        {
          type: 'slider',
          start: 0,
          end: 100,
        },
      ],
      xAxis: {
        type: 'value',
        name: '时间步',
        nameLocation: 'middle',
        nameGap: 30,
      },
      yAxis: {
        type: 'value',
        name: '值',
        nameLocation: 'middle',
        nameGap: 50,
      },
      series,
    }
  }

  // 残差图配置
  const getResidualChartOption = (): EChartsOption => {
    if (!errorData?.analyses?.length) {
      return {}
    }

    const series = errorData.analyses.map((analysis, index) => ({
      name: analysis.model_name,
      type: 'line' as const,
      data: analysis.residual_data.indices.map((idx, i) => [
        idx,
        analysis.residual_data.residuals[i],
      ]),
      smooth: false,
      symbol: 'none',
      lineStyle: {
        width: 1.5,
        color: CHART_COLORS[index % CHART_COLORS.length],
      },
      itemStyle: {
        color: CHART_COLORS[index % CHART_COLORS.length],
      },
    }))

    // 添加零线
    const allIndices = errorData.analyses.flatMap(a => a.residual_data.indices)
    const minIdx = Math.min(...allIndices)
    const maxIdx = Math.max(...allIndices)

    return {
      title: {
        text: '残差时序图 (预测值 - 真实值)',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      legend: {
        data: series.map((s) => s.name),
        top: 30,
        type: 'scroll',
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true,
      },
      toolbox: {
        feature: {
          dataZoom: { yAxisIndex: 'none' },
          restore: {},
          saveAsImage: { name: 'residual_chart' },
        },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100 },
      ],
      xAxis: {
        type: 'value',
        name: '时间步',
        nameLocation: 'middle',
        nameGap: 30,
      },
      yAxis: {
        type: 'value',
        name: '残差',
        nameLocation: 'middle',
        nameGap: 50,
      },
      series: [
        ...series,
        {
          name: '零线',
          type: 'line',
          data: [[minIdx, 0], [maxIdx, 0]],
          lineStyle: { type: 'dashed', color: '#999', width: 1 },
          symbol: 'none',
          silent: true,
        },
      ],
    }
  }

  // 误差分布直方图配置
  const getHistogramChartOption = (): EChartsOption => {
    if (!errorData?.analyses?.length) {
      return {}
    }

    const series = errorData.analyses.map((analysis, index) => ({
      name: analysis.model_name,
      type: 'bar' as const,
      data: analysis.distribution.histogram.map(h => h.count),
      itemStyle: {
        color: CHART_COLORS[index % CHART_COLORS.length],
        opacity: 0.7,
      },
      barGap: '0%',
    }))

    // 优先使用后端返回的统一 bin_edges 生成 x 轴标签
    // 这样确保所有模型的直方图 x 轴完全对齐
    let bins: string[]
    if (errorData.unified_bin_edges && errorData.unified_bin_edges.length > 1) {
      bins = []
      for (let i = 0; i < errorData.unified_bin_edges.length - 1; i++) {
        const start = errorData.unified_bin_edges[i]
        const end = errorData.unified_bin_edges[i + 1]
        bins.push(`${start.toFixed(2)}~${end.toFixed(2)}`)
      }
    } else {
      // 兼容旧版本：使用第一个模型的 histogram bins
      bins = errorData.analyses[0].distribution.histogram.map(
        h => `${h.bin_start.toFixed(2)}~${h.bin_end.toFixed(2)}`
      )
    }

    return {
      title: {
        text: '误差分布直方图',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      legend: {
        data: series.map((s) => s.name),
        top: 30,
        type: 'scroll',
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: bins,
        name: '误差区间',
        nameLocation: 'middle',
        nameGap: 30,
        axisLabel: { rotate: 45, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        name: '频数',
        nameLocation: 'middle',
        nameGap: 40,
      },
      series,
    }
  }

  // 雷达图配置
  const getRadarChartOption = (): EChartsOption => {
    if (!radarData?.results?.length) {
      return {}
    }

    const series = radarData.results.map((r, index) => ({
      name: r.model_name,
      type: 'radar' as const,
      data: [
        {
          value: [r.mse_score, r.rmse_score, r.mae_score, r.r2_score, r.mape_score],
          name: r.model_name,
          areaStyle: { opacity: 0.2 },
          lineStyle: { color: CHART_COLORS[index % CHART_COLORS.length] },
          itemStyle: { color: CHART_COLORS[index % CHART_COLORS.length] },
        },
      ],
    }))

    return {
      title: {
        text: '模型性能雷达图',
        subtext: '得分越高越好（已归一化）',
        left: 'center',
      },
      tooltip: { trigger: 'item' },
      legend: {
        data: radarData.results.map((r) => r.model_name),
        top: 50,
        type: 'scroll',
      },
      radar: {
        indicator: RADAR_INDICATORS.map(ind => ({ name: ind.name, max: ind.max })),
        center: ['50%', '60%'],
        radius: '60%',
      },
      series,
    }
  }

  // ============ 指标表格 ============
  interface MetricsTableRow {
    key: number
    name: string
    model_name: string
    mse: number
    rmse: number
    mae: number
    r2: number
    mape: number
  }

  const metricsTableData = useMemo((): MetricsTableRow[] => {
    if (!compareData?.metrics) return []

    return selectedResultIds
      .map((id) => {
        const result = results.find((r) => r.id === id)
        const metrics = compareData.metrics[id]
        if (!result || !metrics) return null

        return {
          key: id,
          name: result.name,
          model_name: result.model_name,
          mse: metrics.mse,
          rmse: metrics.rmse,
          mae: metrics.mae,
          r2: metrics.r2,
          mape: metrics.mape,
        }
      })
      .filter((item): item is MetricsTableRow => item !== null)
  }, [compareData?.metrics, selectedResultIds, results])

  // 找出每个指标的最优值（使用 useMemo 缓存，避免浮点精度问题）
  const bestValues = useMemo(() => {
    if (metricsTableData.length === 0) return {}

    const best: Record<string, number> = {}
    const metricKeys: (keyof Metrics)[] = ['mse', 'rmse', 'mae', 'r2', 'mape']

    metricKeys.forEach((key) => {
      const values = metricsTableData.map((d) => d[key]).filter((v) => v !== undefined)
      if (values.length > 0) {
        // R² 越大越好，其他越小越好
        best[key] = key === 'r2' ? Math.max(...values) : Math.min(...values)
      }
    })

    return best
  }, [metricsTableData])

  // 判断是否为最优值（使用容差比较避免浮点精度问题）
  const isBestValue = (key: keyof Metrics, value: number): boolean => {
    const bestValue = bestValues[key]
    if (bestValue === undefined) return false
    // 使用相对容差 1e-10 进行比较
    return Math.abs(value - bestValue) < Math.abs(bestValue) * 1e-10 + 1e-15
  }

  const metricsColumns: ColumnsType<MetricsTableRow> = [
    {
      title: '结果名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      fixed: 'left',
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 120,
    },
    ...(['mse', 'rmse', 'mae', 'r2', 'mape'] as const).map((key) => ({
      title: METRIC_NAMES[key],
      dataIndex: key,
      key,
      width: 120,
      render: (value: number) => {
        const isBest = isBestValue(key, value)
        return (
          <Text
            strong={isBest}
            style={{ color: isBest ? '#52c41a' : undefined }}
          >
            {formatMetric(value, key)}
          </Text>
        )
      },
    })),
  ]

  // ============ 渲染 ============
  return (
    <div style={{ padding: 24 }}>
      {/* 页面头部 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              📈 可视化对比
            </Title>
            <Text type="secondary">选择多个预测结果进行曲线对比和指标分析</Text>
          </Col>
          <Col>
            <Space>
              <Tooltip title="导出对比数据">
                <Button
                  icon={<FileExcelOutlined />}
                  onClick={handleExportCSV}
                  disabled={selectedResultIds.length === 0}
                >
                  导出 CSV
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 配置区域 */}
      <Card style={{ marginBottom: 16 }}>
        {/* 数据集筛选 */}
        <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <FilterOutlined />
              <Text>按数据集筛选：</Text>
              <Select
                placeholder="全部数据集"
                style={{ width: 200 }}
                value={selectedDatasetId}
                onChange={setSelectedDatasetId}
                allowClear
                loading={datasetsLoading}
                showSearch
                optionFilterProp="children"
              >
                {datasets.map((ds) => (
                  <Select.Option key={ds.id} value={ds.id}>
                    {ds.name}
                  </Select.Option>
                ))}
              </Select>
              {selectedDatasetId && (
                <Tag color="blue">
                  已筛选: {filteredResults.length} 个结果
                </Tag>
              )}
            </Space>
          </Col>
        </Row>

        {/* 结果选择 */}
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>选择结果（最多 {APP_CONFIG.VISUALIZATION.MAX_RESULTS} 个）：</Text>
              <Select
                mode="multiple"
                placeholder="请选择要对比的结果"
                style={{ width: '100%' }}
                value={selectedResultIds}
                onChange={(values) => {
                  if (values.length > APP_CONFIG.VISUALIZATION.MAX_RESULTS) {
                    message.warning(`最多选择 ${APP_CONFIG.VISUALIZATION.MAX_RESULTS} 个结果`)
                    return
                  }
                  setSelectedResultIds(values)
                }}
                loading={resultsLoading}
                optionFilterProp="children"
                showSearch
              >
                {filteredResults.map((result) => (
                  <Select.Option key={result.id} value={result.id}>
                    {result.name} ({result.model_name})
                  </Select.Option>
                ))}
              </Select>
            </Space>
          </Col>
        </Row>

        <Divider />

        {/* 降采样配置和操作按钮 */}
        <Row gutter={[24, 16]} align="middle">
          <Col>
            <Space>
              <Text>降采样算法：</Text>
              <Select
                value={algorithm}
                onChange={setAlgorithm}
                style={{ width: 150 }}
              >
                {DOWNSAMPLE_ALGORITHM_OPTIONS.map((opt) => (
                  <Select.Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Select.Option>
                ))}
              </Select>
            </Space>
          </Col>
          <Col flex="auto">
            <Space style={{ width: '100%' }}>
              <Text>最大点数：</Text>
              <Slider
                min={APP_CONFIG.VISUALIZATION.MIN_POINTS}
                max={APP_CONFIG.VISUALIZATION.MAX_POINTS}
                value={maxPoints}
                onChange={setMaxPoints}
                style={{ width: 200 }}
              />
              <InputNumber
                min={APP_CONFIG.VISUALIZATION.MIN_POINTS}
                max={APP_CONFIG.VISUALIZATION.MAX_POINTS}
                value={maxPoints}
                onChange={(v) => v && setMaxPoints(v)}
                style={{ width: 100 }}
              />
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<LineChartOutlined />}
              onClick={handleCompare}
              loading={compareLoading}
              disabled={selectedResultIds.length === 0}
            >
              开始对比
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Tab 视图 */}
      <Card style={{ marginBottom: 16 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'curve',
              label: (
                <span>
                  <LineChartOutlined />
                  曲线对比
                </span>
              ),
              children: (
                <>
                  {compareLoading ? (
                    <div style={{ textAlign: 'center', padding: 100 }}>
                      <Spin size="large" />
                      <div style={{ marginTop: 16 }}>
                        <Text type="secondary">加载中...</Text>
                      </div>
                    </div>
                  ) : compareData?.chart_data?.series?.length ? (
                    <div>
                      {/* 警告信息 */}
                      {compareData.skipped && compareData.skipped.length > 0 && (
                        <Alert
                          type="error"
                          icon={<WarningOutlined />}
                          showIcon
                          style={{ marginBottom: 16 }}
                          message={`${compareData.skipped.length} 个结果被跳过`}
                          description={
                            <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
                              {compareData.skipped.map((item) => (
                                <li key={item.id}>
                                  <Text strong>{item.name}</Text>：{item.reason}
                                </li>
                              ))}
                            </ul>
                          }
                        />
                      )}
                      {compareData.warnings && compareData.warnings.length > 0 && (
                        <Alert
                          type="warning"
                          icon={<WarningOutlined />}
                          showIcon
                          style={{ marginBottom: 16 }}
                          message={`${compareData.warnings.length} 个结果存在警告`}
                          description={
                            <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
                              {compareData.warnings.map((item) => (
                                <li key={item.id}>
                                  <Text strong>{item.name}</Text>：{item.message}
                                </li>
                              ))}
                            </ul>
                          }
                        />
                      )}
                      {compareData.chart_data.downsampled && (
                        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                          数据已降采样（原始 {compareData.chart_data.total_points.toLocaleString()} 点 → {maxPoints} 点）
                        </Text>
                      )}
                      <Space style={{ marginBottom: 16 }}>
                        <Button icon={<DownloadOutlined />} onClick={() => handleExportChart('png')}>
                          导出 PNG
                        </Button>
                        <Button icon={<DownloadOutlined />} onClick={() => handleExportChart('jpg')}>
                          导出 JPG
                        </Button>
                      </Space>
                      <ReactECharts
                        ref={chartRef}
                        option={getChartOption()}
                        style={{ height: 500 }}
                        notMerge
                      />
                    </div>
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="请选择结果并点击「开始对比」"
                    />
                  )}
                </>
              ),
            },
            {
              key: 'error',
              label: (
                <span>
                  <BarChartOutlined />
                  误差分析
                </span>
              ),
              children: (
                <>
                  {errorLoading ? (
                    <div style={{ textAlign: 'center', padding: 100 }}>
                      <Spin size="large" />
                    </div>
                  ) : errorData?.analyses?.length ? (
                    <div>
                      {/* 误差统计卡片 */}
                      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                        {errorData.analyses.map((analysis, index) => (
                          <Col xs={24} sm={12} lg={8} xl={6} key={analysis.result_id}>
                            <Card
                              size="small"
                              title={
                                <Space>
                                  <div
                                    style={{
                                      width: 12,
                                      height: 12,
                                      borderRadius: '50%',
                                      backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                                    }}
                                  />
                                  {analysis.model_name}
                                </Space>
                              }
                            >
                              <Row gutter={[8, 4]}>
                                <Col span={12}><Text type="secondary">均值:</Text></Col>
                                <Col span={12}><Text>{analysis.distribution.mean.toFixed(4)}</Text></Col>
                                <Col span={12}><Text type="secondary">标准差:</Text></Col>
                                <Col span={12}><Text>{analysis.distribution.std.toFixed(4)}</Text></Col>
                                <Col span={12}><Text type="secondary">中位数:</Text></Col>
                                <Col span={12}><Text>{analysis.distribution.median.toFixed(4)}</Text></Col>
                                <Col span={12}><Text type="secondary">最小值:</Text></Col>
                                <Col span={12}><Text>{analysis.distribution.min.toFixed(4)}</Text></Col>
                                <Col span={12}><Text type="secondary">最大值:</Text></Col>
                                <Col span={12}><Text>{analysis.distribution.max.toFixed(4)}</Text></Col>
                              </Row>
                            </Card>
                          </Col>
                        ))}
                      </Row>

                      {/* 残差时序图 */}
                      <Card title="残差时序图" size="small" style={{ marginBottom: 16 }}>
                        <ReactECharts
                          ref={residualChartRef}
                          option={getResidualChartOption()}
                          style={{ height: 400 }}
                          notMerge
                        />
                      </Card>

                      {/* 误差分布直方图 */}
                      <Card title="误差分布直方图" size="small">
                        <ReactECharts
                          ref={histogramChartRef}
                          option={getHistogramChartOption()}
                          style={{ height: 400 }}
                          notMerge
                        />
                      </Card>
                    </div>
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="请先进行对比分析"
                    />
                  )}
                </>
              ),
            },
            {
              key: 'radar',
              label: (
                <span>
                  <RadarChartOutlined />
                  雷达图
                </span>
              ),
              children: (
                <>
                  {radarLoading ? (
                    <div style={{ textAlign: 'center', padding: 100 }}>
                      <Spin size="large" />
                    </div>
                  ) : radarData?.results?.length ? (
                    <Row gutter={[24, 24]}>
                      <Col xs={24} lg={14}>
                        <Card title="性能雷达图" size="small">
                          <ReactECharts
                            ref={radarChartRef}
                            option={getRadarChartOption()}
                            style={{ height: 450 }}
                            notMerge
                          />
                        </Card>
                      </Col>
                      <Col xs={24} lg={10}>
                        {/* 综合排名 */}
                        <Card
                          title={
                            <Space>
                              <TrophyOutlined style={{ color: '#faad14' }} />
                              综合排名
                            </Space>
                          }
                          size="small"
                          style={{ marginBottom: 16 }}
                        >
                          <Table
                            dataSource={radarData.overall_scores.map((s) => ({
                              key: s.result_id,
                              ...s,
                            }))}
                            columns={[
                              {
                                title: '排名',
                                dataIndex: 'rank',
                                key: 'rank',
                                width: 60,
                                render: (rank: number) => (
                                  <Tag color={rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : 'default'}>
                                    #{rank}
                                  </Tag>
                                ),
                              },
                              {
                                title: '模型',
                                dataIndex: 'model_name',
                                key: 'model_name',
                              },
                              {
                                title: '综合得分',
                                dataIndex: 'score',
                                key: 'score',
                                render: (score: number) => (
                                  <Text strong style={{ color: score > 0.7 ? '#52c41a' : score > 0.4 ? '#faad14' : '#ff4d4f' }}>
                                    {(score * 100).toFixed(1)}%
                                  </Text>
                                ),
                              },
                            ]}
                            pagination={false}
                            size="small"
                          />
                        </Card>

                        {/* 原始指标 */}
                        <Card title="原始指标值" size="small">
                          <Table
                            dataSource={radarData.results.map((r) => ({
                              key: r.result_id,
                              model: r.model_name,
                              mse: r.raw_metrics.mse,
                              rmse: r.raw_metrics.rmse,
                              mae: r.raw_metrics.mae,
                              r2: r.raw_metrics.r2,
                              mape: r.raw_metrics.mape,
                            }))}
                            columns={[
                              { title: '模型', dataIndex: 'model', key: 'model', width: 100 },
                              { title: 'MSE', dataIndex: 'mse', key: 'mse', render: (v: number) => v.toFixed(4) },
                              { title: 'RMSE', dataIndex: 'rmse', key: 'rmse', render: (v: number) => v.toFixed(4) },
                              { title: 'MAE', dataIndex: 'mae', key: 'mae', render: (v: number) => v.toFixed(4) },
                              { title: 'R²', dataIndex: 'r2', key: 'r2', render: (v: number) => v.toFixed(4) },
                              { title: 'MAPE', dataIndex: 'mape', key: 'mape', render: (v: number) => `${v.toFixed(2)}%` },
                            ]}
                            pagination={false}
                            size="small"
                            scroll={{ x: 500 }}
                          />
                        </Card>
                      </Col>
                    </Row>
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="请先进行对比分析"
                    />
                  )}
                </>
              ),
            },
            {
              key: 'range',
              label: (
                <span>
                  <FilterOutlined />
                  区间分析
                </span>
              ),
              children: (
                <div>
                  <Card title="区间指标计算" size="small" style={{ marginBottom: 16 }}>
                    <Row gutter={[16, 16]} align="middle">
                      <Col>
                        <Space>
                          <Text>起始索引：</Text>
                          <InputNumber
                            min={0}
                            value={rangeStart}
                            onChange={(v) => setRangeStart(v)}
                            placeholder="0"
                            style={{ width: 120 }}
                          />
                        </Space>
                      </Col>
                      <Col>
                        <Space>
                          <Text>结束索引：</Text>
                          <InputNumber
                            min={0}
                            value={rangeEnd}
                            onChange={(v) => setRangeEnd(v)}
                            placeholder="1000"
                            style={{ width: 120 }}
                          />
                        </Space>
                      </Col>
                      <Col>
                        <Button
                          type="primary"
                          onClick={handleRangeMetrics}
                          loading={rangeLoading}
                          disabled={!compareData || rangeStart === null || rangeEnd === null}
                        >
                          计算区间指标
                        </Button>
                      </Col>
                      {compareData?.chart_data?.total_points && (
                        <Col>
                          <Text type="secondary">
                            数据总点数: {compareData.chart_data.total_points.toLocaleString()}
                          </Text>
                        </Col>
                      )}
                    </Row>
                  </Card>

                  {rangeMetrics ? (
                    <Card
                      title={`区间 [${rangeMetrics.range_start}, ${rangeMetrics.range_end}] 指标对比`}
                      size="small"
                    >
                      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                        区间内有效点数: {rangeMetrics.total_points.toLocaleString()}
                      </Text>
                      <Table
                        dataSource={Object.entries(rangeMetrics.metrics).map(([id, metrics]) => {
                          const result = results.find((r) => r.id === Number(id))
                          return {
                            key: id,
                            name: result?.name || `ID:${id}`,
                            model_name: result?.model_name || '-',
                            ...metrics,
                          }
                        })}
                        columns={metricsColumns}
                        pagination={false}
                        scroll={{ x: 900 }}
                        size="small"
                      />
                    </Card>
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="请先进行对比分析，然后输入区间范围计算指标"
                    />
                  )}
                </div>
              ),
            },
            {
              key: 'config',
              label: (
                <span>
                  <ExperimentOutlined />
                  配置对比
                </span>
              ),
              children: (
                <ConfigComparison resultIds={selectedResultIds} />
              ),
            },
          ]}
        />
      </Card>

      {/* 指标对比表格 */}
      {compareData?.metrics && Object.keys(compareData.metrics).length > 0 && (
        <Card title="全量指标对比">
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            <span style={{ color: '#52c41a', fontWeight: 'bold' }}>绿色加粗</span> 表示该指标的最优值
          </Text>
          <Table<MetricsTableRow>
            columns={metricsColumns}
            dataSource={metricsTableData}
            pagination={false}
            scroll={{ x: 900 }}
            size="middle"
          />
        </Card>
      )}
    </div>
  )
}

