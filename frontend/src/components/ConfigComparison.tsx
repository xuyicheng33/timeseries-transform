/**
 * 配置对比分析组件
 * 功能：超参数敏感性分析、控制变量对比、调参建议
 */

import { useState, useEffect, useMemo } from 'react'
import {
  Card,
  Tabs,
  Table,
  Select,
  Button,
  Space,
  Row,
  Col,
  Typography,
  Tag,
  Alert,
  Empty,
  Spin,
  Progress,
  Descriptions,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ExperimentOutlined,
  BarChartOutlined,
  BulbOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

import type {
  ConfigCompareResponse,
  ControlledCompareResponse,
  SensitivityResponse,
  ParameterAnalysis,
  SensitivityItem,
} from '@/types/comparison'
import {
  analyzeConfigurations,
  controlledComparison,
  analyzeSensitivity,
} from '@/api/comparison'

const { Text } = Typography

// 图表颜色
const CHART_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#48b8d0',
]

// 指标配置
const METRIC_OPTIONS = [
  { value: 'rmse', label: 'RMSE' },
  { value: 'mse', label: 'MSE' },
  { value: 'mae', label: 'MAE' },
  { value: 'r2', label: 'R²' },
  { value: 'mape', label: 'MAPE' },
]

interface ConfigComparisonProps {
  resultIds: number[]
  onClose?: () => void
}

export default function ConfigComparison({ resultIds }: ConfigComparisonProps) {
  // ============ 状态 ============
  const [activeTab, setActiveTab] = useState('overview')
  
  // 配置分析数据
  const [configData, setConfigData] = useState<ConfigCompareResponse | null>(null)
  const [configLoading, setConfigLoading] = useState(false)
  
  // 控制变量对比
  const [controlledData, setControlledData] = useState<ControlledCompareResponse | null>(null)
  const [controlledLoading, setControlledLoading] = useState(false)
  const [selectedParameter, setSelectedParameter] = useState<string>('')
  
  // 敏感性分析
  const [sensitivityData, setSensitivityData] = useState<SensitivityResponse | null>(null)
  const [sensitivityLoading, setSensitivityLoading] = useState(false)
  const [targetMetric, setTargetMetric] = useState('rmse')

  // ============ 数据获取 ============
  useEffect(() => {
    if (resultIds.length > 0) {
      fetchConfigAnalysis()
    }
  }, [resultIds])

  const fetchConfigAnalysis = async () => {
    setConfigLoading(true)
    try {
      const data = await analyzeConfigurations(resultIds)
      setConfigData(data)
      
      // 自动选择第一个可分析的参数
      if (data.parameters.length > 0) {
        setSelectedParameter(data.parameters[0].parameter_name)
      }
    } catch {
      message.error('配置分析失败')
    } finally {
      setConfigLoading(false)
    }
  }

  const fetchControlledComparison = async () => {
    if (!selectedParameter) {
      message.warning('请选择要分析的参数')
      return
    }
    
    setControlledLoading(true)
    try {
      const data = await controlledComparison(resultIds, selectedParameter)
      setControlledData(data)
    } catch {
      message.error('控制变量对比失败')
    } finally {
      setControlledLoading(false)
    }
  }

  const fetchSensitivityAnalysis = async () => {
    setSensitivityLoading(true)
    try {
      const data = await analyzeSensitivity(resultIds, targetMetric)
      setSensitivityData(data)
    } catch {
      message.error('敏感性分析失败')
    } finally {
      setSensitivityLoading(false)
    }
  }

  // ============ 可用参数列表 ============
  const availableParameters = useMemo(() => {
    if (!configData) return []
    return configData.parameters.map(p => ({
      value: p.parameter_name,
      label: p.parameter_label,
    }))
  }, [configData])

  // ============ 图表配置 ============
  
  // 参数敏感性柱状图
  const getSensitivityBarOption = (): EChartsOption => {
    if (!configData?.parameters.length) return {}
    
    const sortedParams = [...configData.parameters].sort(
      (a, b) => b.sensitivity_score - a.sensitivity_score
    )
    
    return {
      title: {
        text: '参数敏感性排名',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const data = params[0]
          return `${data.name}<br/>敏感性得分: ${(data.value * 100).toFixed(1)}%`
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: sortedParams.map(p => p.parameter_label),
        axisLabel: { rotate: 30 },
      },
      yAxis: {
        type: 'value',
        name: '敏感性得分',
        max: 1,
        axisLabel: {
          formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
        },
      },
      series: [{
        type: 'bar',
        data: sortedParams.map((p, i) => ({
          value: p.sensitivity_score,
          itemStyle: {
            color: CHART_COLORS[i % CHART_COLORS.length],
          },
        })),
        label: {
          show: true,
          position: 'top',
          formatter: (params: any) => `${(params.value * 100).toFixed(1)}%`,
        },
      }],
    }
  }

  // 控制变量对比图
  const getControlledChartOption = (): EChartsOption => {
    if (!controlledData?.chart_data) return {}
    
    const { x_axis, series } = controlledData.chart_data
    
    return {
      title: {
        text: `${controlledData.parameter_label} 对性能的影响`,
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        top: 30,
        data: series.map(s => s.name),
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 70,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        name: x_axis.name,
        data: x_axis.data.map(String),
      },
      yAxis: {
        type: 'value',
        name: '指标值',
      },
      series: series.map((s, i) => ({
        name: s.name,
        type: x_axis.is_numeric ? 'line' : 'bar',
        data: s.data,
        itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
        smooth: true,
      })),
    }
  }

  // 敏感性雷达图
  const getSensitivityRadarOption = (): EChartsOption => {
    if (!sensitivityData?.sensitivities.length) return {}
    
    const indicators = sensitivityData.sensitivities.slice(0, 6).map(s => ({
      name: s.parameter_label,
      max: 1,
    }))
    
    return {
      title: {
        text: '参数敏感性雷达图',
        left: 'center',
      },
      tooltip: {
        trigger: 'item',
      },
      radar: {
        indicator: indicators,
        center: ['50%', '55%'],
        radius: '65%',
      },
      series: [{
        type: 'radar',
        data: [{
          value: sensitivityData.sensitivities.slice(0, 6).map(s => s.sensitivity_score),
          name: `对 ${METRIC_OPTIONS.find(m => m.value === targetMetric)?.label} 的敏感性`,
          areaStyle: { opacity: 0.3 },
          lineStyle: { color: CHART_COLORS[0] },
          itemStyle: { color: CHART_COLORS[0] },
        }],
      }],
    }
  }

  // ============ 表格列定义 ============
  const parameterColumns: ColumnsType<ParameterAnalysis> = [
    {
      title: '参数',
      dataIndex: 'parameter_label',
      key: 'parameter_label',
      width: 120,
      render: (label: string) => <Text strong>{label}</Text>,
    },
    {
      title: '敏感性',
      dataIndex: 'sensitivity_score',
      key: 'sensitivity_score',
      width: 150,
      sorter: (a, b) => b.sensitivity_score - a.sensitivity_score,
      render: (score: number) => (
        <Space>
          <Progress
            percent={Math.round(score * 100)}
            size="small"
            style={{ width: 80 }}
            strokeColor={score > 0.3 ? '#ff4d4f' : score > 0.1 ? '#faad14' : '#52c41a'}
          />
          <Tag color={score > 0.3 ? 'red' : score > 0.1 ? 'orange' : 'green'}>
            {score > 0.3 ? '高' : score > 0.1 ? '中' : '低'}
          </Tag>
        </Space>
      ),
    },
    {
      title: '取值数量',
      key: 'value_count',
      width: 100,
      render: (_, record) => record.values.length,
    },
    {
      title: '取值范围',
      key: 'values',
      render: (_, record) => (
        <Space wrap size={4}>
          {record.values.slice(0, 5).map((v, i) => (
            <Tag key={i}>{String(v.value)}</Tag>
          ))}
          {record.values.length > 5 && <Tag>+{record.values.length - 5}</Tag>}
        </Space>
      ),
    },
  ]

  const sensitivityColumns: ColumnsType<SensitivityItem> = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_, __, index) => (
        <Tag color={index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'volcano' : 'default'}>
          #{index + 1}
        </Tag>
      ),
    },
    {
      title: '参数',
      dataIndex: 'parameter_label',
      key: 'parameter_label',
      width: 120,
    },
    {
      title: '敏感性得分',
      dataIndex: 'sensitivity_score',
      key: 'sensitivity_score',
      width: 150,
      render: (score: number) => (
        <Progress
          percent={Math.round(score * 100)}
          size="small"
          strokeColor={score > 0.3 ? '#ff4d4f' : score > 0.1 ? '#faad14' : '#52c41a'}
        />
      ),
    },
    {
      title: '最优值',
      dataIndex: 'best_value',
      key: 'best_value',
      width: 100,
      render: (value: any) => (
        <Tag color="green" icon={<CheckCircleOutlined />}>
          {String(value)}
        </Tag>
      ),
    },
    {
      title: '最优指标',
      dataIndex: 'best_metric',
      key: 'best_metric',
      width: 120,
      render: (metric: number) => metric.toFixed(6),
    },
  ]

  // ============ 渲染 ============
  if (resultIds.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="请选择要分析的结果"
      />
    )
  }

  return (
    <div>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'overview',
            label: (
              <span>
                <ExperimentOutlined />
                配置概览
              </span>
            ),
            children: (
              <Spin spinning={configLoading}>
                {configData ? (
                  <div>
                    {/* 警告信息 */}
                    {configData.warnings.length > 0 && (
                      <Alert
                        type="warning"
                        showIcon
                        style={{ marginBottom: 16 }}
                        message={`${configData.warnings.length} 个警告`}
                        description={
                          <ul style={{ margin: 0, paddingLeft: 20 }}>
                            {configData.warnings.map((w, i) => (
                              <li key={i}>{w}</li>
                            ))}
                          </ul>
                        }
                      />
                    )}

                    {/* 统计信息 */}
                    <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                      <Col span={8}>
                        <Card size="small">
                          <Statistic
                            title="分析结果数"
                            value={configData.total_results}
                            suffix="个"
                          />
                        </Card>
                      </Col>
                      <Col span={8}>
                        <Card size="small">
                          <Statistic
                            title="可分析参数"
                            value={configData.parameters.length}
                            suffix="个"
                          />
                        </Card>
                      </Col>
                      <Col span={8}>
                        <Card size="small">
                          <Statistic
                            title="最敏感参数"
                            value={configData.parameters[0]?.parameter_label || '-'}
                            valueStyle={{ fontSize: 16 }}
                          />
                        </Card>
                      </Col>
                    </Row>

                    {/* 敏感性柱状图 */}
                    {configData.parameters.length > 0 && (
                      <Card title="参数敏感性分析" size="small" style={{ marginBottom: 16 }}>
                        <ReactECharts
                          option={getSensitivityBarOption()}
                          style={{ height: 300 }}
                          notMerge
                        />
                      </Card>
                    )}

                    {/* 参数详情表格 */}
                    <Card title="参数详情" size="small">
                      <Table
                        columns={parameterColumns}
                        dataSource={configData.parameters}
                        rowKey="parameter_name"
                        pagination={false}
                        size="small"
                      />
                    </Card>
                  </div>
                ) : (
                  <Empty description="暂无数据" />
                )}
              </Spin>
            ),
          },
          {
            key: 'controlled',
            label: (
              <span>
                <BarChartOutlined />
                控制变量对比
              </span>
            ),
            children: (
              <div>
                {/* 参数选择 */}
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space>
                    <Text>选择要分析的参数：</Text>
                    <Select
                      value={selectedParameter}
                      onChange={setSelectedParameter}
                      style={{ width: 200 }}
                      options={availableParameters}
                      placeholder="选择参数"
                    />
                    <Button
                      type="primary"
                      onClick={fetchControlledComparison}
                      loading={controlledLoading}
                      disabled={!selectedParameter}
                    >
                      开始分析
                    </Button>
                  </Space>
                </Card>

                <Spin spinning={controlledLoading}>
                  {controlledData ? (
                    <div>
                      {/* 配置不一致警告 */}
                      {!controlledData.config_consistent && (
                        <Alert
                          type="warning"
                          showIcon
                          style={{ marginBottom: 16 }}
                          message="其他参数不完全一致"
                          description={
                            <span>
                              以下参数存在差异：{controlledData.inconsistent_params.join('、')}。
                              已自动过滤为基准配置的结果，对比结论更可靠。
                            </span>
                          }
                        />
                      )}

                      {/* 基准配置 */}
                      <Card
                        title={
                          <Space>
                            <InfoCircleOutlined />
                            基准配置（其他参数的共同值）
                          </Space>
                        }
                        size="small"
                        style={{ marginBottom: 16 }}
                      >
                        <Descriptions column={4} size="small">
                          {Object.entries(controlledData.baseline_config).map(([key, value]) => (
                            <Descriptions.Item key={key} label={key}>
                              <Tag>{String(value)}</Tag>
                            </Descriptions.Item>
                          ))}
                        </Descriptions>
                      </Card>

                      {/* 对比图表 */}
                      <Card title="参数影响分析" size="small" style={{ marginBottom: 16 }}>
                        <ReactECharts
                          option={getControlledChartOption()}
                          style={{ height: 400 }}
                          notMerge
                        />
                      </Card>

                      {/* 详细数据 */}
                      <Card title="详细数据" size="small">
                        <Table
                          dataSource={controlledData.variations}
                          rowKey="parameter_value"
                          pagination={false}
                          size="small"
                          columns={[
                            {
                              title: controlledData.parameter_label,
                              dataIndex: 'parameter_value',
                              key: 'parameter_value',
                              render: (v: any) => <Tag color="blue">{String(v)}</Tag>,
                            },
                            {
                              title: '结果数',
                              dataIndex: 'result_count',
                              key: 'result_count',
                            },
                            {
                              title: 'RMSE',
                              key: 'rmse',
                              render: (_, r) => r.metrics.rmse?.toFixed(4) || '-',
                            },
                            {
                              title: 'MAE',
                              key: 'mae',
                              render: (_, r) => r.metrics.mae?.toFixed(4) || '-',
                            },
                            {
                              title: 'R²',
                              key: 'r2',
                              render: (_, r) => r.metrics.r2?.toFixed(4) || '-',
                            },
                            {
                              title: 'MAPE',
                              key: 'mape',
                              render: (_, r) => r.metrics.mape ? `${r.metrics.mape.toFixed(2)}%` : '-',
                            },
                          ]}
                        />
                      </Card>
                    </div>
                  ) : (
                    <Empty description="请选择参数并开始分析" />
                  )}
                </Spin>
              </div>
            ),
          },
          {
            key: 'sensitivity',
            label: (
              <span>
                <ThunderboltOutlined />
                敏感性分析
              </span>
            ),
            children: (
              <div>
                {/* 指标选择 */}
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space>
                    <Text>目标指标：</Text>
                    <Select
                      value={targetMetric}
                      onChange={setTargetMetric}
                      style={{ width: 150 }}
                      options={METRIC_OPTIONS}
                    />
                    <Button
                      type="primary"
                      onClick={fetchSensitivityAnalysis}
                      loading={sensitivityLoading}
                    >
                      分析敏感性
                    </Button>
                  </Space>
                </Card>

                <Spin spinning={sensitivityLoading}>
                  {sensitivityData ? (
                    <Row gutter={[16, 16]}>
                      <Col xs={24} lg={14}>
                        {/* 敏感性排名表 */}
                        <Card title="敏感性排名" size="small" style={{ marginBottom: 16 }}>
                          <Table
                            columns={sensitivityColumns}
                            dataSource={sensitivityData.sensitivities}
                            rowKey="parameter"
                            pagination={false}
                            size="small"
                          />
                        </Card>

                        {/* 雷达图 */}
                        {sensitivityData.sensitivities.length >= 3 && (
                          <Card title="敏感性雷达图" size="small">
                            <ReactECharts
                              option={getSensitivityRadarOption()}
                              style={{ height: 350 }}
                              notMerge
                            />
                          </Card>
                        )}
                      </Col>

                      <Col xs={24} lg={10}>
                        {/* 调参建议 */}
                        <Card
                          title={
                            <Space>
                              <BulbOutlined style={{ color: '#faad14' }} />
                              调参建议
                            </Space>
                          }
                          size="small"
                        >
                          {sensitivityData.recommendations.map((rec, i) => (
                            <Alert
                              key={i}
                              type="info"
                              showIcon
                              icon={<BulbOutlined />}
                              message={rec}
                              style={{ marginBottom: i < sensitivityData.recommendations.length - 1 ? 12 : 0 }}
                            />
                          ))}
                        </Card>

                        {/* 最优参数组合 */}
                        <Card
                          title={
                            <Space>
                              <CheckCircleOutlined style={{ color: '#52c41a' }} />
                              推荐参数值
                            </Space>
                          }
                          size="small"
                          style={{ marginTop: 16 }}
                        >
                          <Descriptions column={1} size="small">
                            {sensitivityData.sensitivities.slice(0, 5).map(s => (
                              <Descriptions.Item key={s.parameter} label={s.parameter_label}>
                                <Tag color="green">{String(s.best_value)}</Tag>
                                <Text type="secondary" style={{ marginLeft: 8 }}>
                                  ({METRIC_OPTIONS.find(m => m.value === targetMetric)?.label}: {s.best_metric.toFixed(4)})
                                </Text>
                              </Descriptions.Item>
                            ))}
                          </Descriptions>
                        </Card>
                      </Col>
                    </Row>
                  ) : (
                    <Empty description="请选择目标指标并开始分析" />
                  )}
                </Spin>
              </div>
            ),
          },
          {
            key: 'details',
            label: (
              <span>
                <InfoCircleOutlined />
                结果详情
              </span>
            ),
            children: (
              <Spin spinning={configLoading}>
                {configData?.result_details ? (
                  <Table
                    dataSource={configData.result_details}
                    rowKey="result_id"
                    pagination={{ pageSize: 10 }}
                    size="small"
                    scroll={{ x: 1200 }}
                    columns={[
                      {
                        title: '结果名称',
                        dataIndex: 'result_name',
                        key: 'result_name',
                        width: 150,
                        fixed: 'left',
                        render: (name: string) => <Text strong>{name}</Text>,
                      },
                      {
                        title: '模型',
                        dataIndex: 'model_name',
                        key: 'model_name',
                        width: 100,
                        render: (name: string) => <Tag color="blue">{name}</Tag>,
                      },
                      {
                        title: '配置',
                        dataIndex: 'config_name',
                        key: 'config_name',
                        width: 120,
                        render: (name: string | null) => name || <Text type="secondary">-</Text>,
                      },
                      {
                        title: '窗口大小',
                        key: 'window_size',
                        width: 90,
                        render: (_, r) => r.parameters?.window_size ?? '-',
                      },
                      {
                        title: '步长',
                        key: 'stride',
                        width: 70,
                        render: (_, r) => r.parameters?.stride ?? '-',
                      },
                      {
                        title: '归一化',
                        key: 'normalization',
                        width: 100,
                        render: (_, r) => r.parameters?.normalization ?? '-',
                      },
                      {
                        title: 'RMSE',
                        key: 'rmse',
                        width: 100,
                        render: (_, r) => r.metrics?.rmse?.toFixed(4) ?? '-',
                      },
                      {
                        title: 'MAE',
                        key: 'mae',
                        width: 100,
                        render: (_, r) => r.metrics?.mae?.toFixed(4) ?? '-',
                      },
                      {
                        title: 'R²',
                        key: 'r2',
                        width: 100,
                        render: (_, r) => r.metrics?.r2?.toFixed(4) ?? '-',
                      },
                    ]}
                  />
                ) : (
                  <Empty description="暂无数据" />
                )}
              </Spin>
            ),
          },
        ]}
      />
    </div>
  )
}

// 导出 Statistic 组件（内部使用）
function Statistic({ title, value, suffix, valueStyle }: {
  title: string
  value: string | number
  suffix?: string
  valueStyle?: React.CSSProperties
}) {
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12 }}>{title}</Text>
      <div style={{ fontSize: 24, fontWeight: 600, ...valueStyle }}>
        {value}{suffix && <span style={{ fontSize: 14, fontWeight: 400, marginLeft: 4 }}>{suffix}</span>}
      </div>
    </div>
  )
}

