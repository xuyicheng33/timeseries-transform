/**
 * 可视化对比页面
 * 功能：多模型曲线对比和评估指标展示
 */

import { useState, useEffect, useCallback, useRef } from 'react'
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
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  LineChartOutlined,
  DownloadOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

import type { Result, Metrics, CompareResponse, DownsampleAlgorithm } from '@/types'
import { getResults } from '@/api/results'
import { compareResults } from '@/api/visualization'
import { formatMetric } from '@/utils/format'
import { APP_CONFIG } from '@/config/app'
import { DOWNSAMPLE_ALGORITHM_OPTIONS, METRIC_NAMES } from '@/constants'

const { Title, Text } = Typography

// 颜色配置
const CHART_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#48b8d0',
]

export default function Visualization() {
  // ============ 状态定义 ============
  const [results, setResults] = useState<Result[]>([])
  const [resultsLoading, setResultsLoading] = useState(false)

  // 选中的结果
  const [selectedResultIds, setSelectedResultIds] = useState<number[]>([])

  // 降采样配置
  const [maxPoints, setMaxPoints] = useState(APP_CONFIG.VISUALIZATION.DEFAULT_POINTS)
  const [algorithm, setAlgorithm] = useState<DownsampleAlgorithm>('lttb')

  // 对比数据
  const [compareData, setCompareData] = useState<CompareResponse | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)

  // ECharts 实例引用
  const chartRef = useRef<ReactECharts>(null)

  // ============ 数据获取 ============
  const fetchResults = useCallback(async () => {
    setResultsLoading(true)
    try {
      const data = await getResults()
      setResults(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setResultsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchResults()
  }, [fetchResults])

  // ============ 对比功能 ============
  const handleCompare = async () => {
    if (selectedResultIds.length === 0) {
      message.warning('请至少选择一个结果')
      return
    }

    setCompareLoading(true)
    try {
      const data = await compareResults({
        result_ids: selectedResultIds,
        max_points: maxPoints,
        algorithm,
      })
      setCompareData(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setCompareLoading(false)
    }
  }

  // ============ 图表配置 ============
  const getChartOption = (): EChartsOption => {
    if (!compareData?.chart_data?.series?.length) {
      return {}
    }

    const series = compareData.chart_data.series.map((s, index) => ({
      name: s.name,
      type: 'line' as const,
      data: s.data,
      smooth: false,
      symbol: 'none',
      lineStyle: {
        width: s.name.startsWith('True') ? 2 : 1.5,
        type: s.name.startsWith('True') ? 'solid' as const : 'solid' as const,
      },
      color: s.name.startsWith('True') ? '#333' : CHART_COLORS[index % CHART_COLORS.length],
    }))

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

  // ============ 导出图表 ============
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

  const getMetricsTableData = (): MetricsTableRow[] => {
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
  }

  // 找出每个指标的最优值
  const getBestValues = () => {
    const data = getMetricsTableData()
    if (data.length === 0) return {}

    const best: Record<string, number> = {}
    const metricKeys: (keyof Metrics)[] = ['mse', 'rmse', 'mae', 'r2', 'mape']

    metricKeys.forEach((key) => {
      const values = data.map((d) => d[key]).filter((v) => v !== undefined)
      if (values.length > 0) {
        // R² 越大越好，其他越小越好
        best[key] = key === 'r2' ? Math.max(...values) : Math.min(...values)
      }
    })

    return best
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
        const best = getBestValues()
        const isBest = best[key] === value
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
        <Title level={4} style={{ margin: 0 }}>
          📈 可视化对比
        </Title>
        <Text type="secondary">选择多个预测结果进行曲线对比和指标分析</Text>
      </Card>

      {/* 配置区域 */}
      <Card style={{ marginBottom: 16 }}>
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
                {results.map((result) => (
                  <Select.Option key={result.id} value={result.id}>
                    {result.name} ({result.model_name})
                  </Select.Option>
                ))}
              </Select>
            </Space>
          </Col>
        </Row>

        <Divider />

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

      {/* 图表区域 */}
      <Card
        style={{ marginBottom: 16 }}
        title="曲线对比"
        extra={
          compareData && (
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleCompare}
                loading={compareLoading}
              >
                刷新
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => handleExportChart('png')}
              >
                导出 PNG
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => handleExportChart('jpg')}
              >
                导出 JPG
              </Button>
            </Space>
          )
        }
      >
        {compareLoading ? (
          <div style={{ textAlign: 'center', padding: 100 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">加载中...</Text>
            </div>
          </div>
        ) : compareData?.chart_data?.series?.length ? (
          <div>
            {compareData.chart_data.downsampled && (
              <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                数据已降采样（原始 {compareData.chart_data.total_points.toLocaleString()} 点 → {maxPoints} 点）
              </Text>
            )}
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
      </Card>

      {/* 指标对比表格 */}
      {compareData?.metrics && Object.keys(compareData.metrics).length > 0 && (
        <Card title="指标对比">
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            <span style={{ color: '#52c41a', fontWeight: 'bold' }}>绿色加粗</span> 表示该指标的最优值
          </Text>
          <Table<MetricsTableRow>
            columns={metricsColumns}
            dataSource={getMetricsTableData()}
            pagination={false}
            scroll={{ x: 900 }}
            size="middle"
          />
        </Card>
      )}
    </div>
  )
}

