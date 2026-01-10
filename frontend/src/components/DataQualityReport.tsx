/**
 * 数据质量报告组件
 * 展示数据集的质量分析结果
 */
import { useState, useMemo } from 'react'
import {
  Card,
  Row,
  Col,
  Progress,
  Statistic,
  Table,
  Tag,
  Tabs,
  Alert,
  Typography,
  Tooltip,
  Space,
  Select,
  Button,
  Descriptions,
  Empty,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'

import type {
  DataQualityReport as QualityReportType,
  ColumnMissingStats,
  ColumnOutlierStats,
  ColumnBasicStats,
  QualitySuggestion,
  OutlierMethod,
} from '@/types'
import { QUALITY_LEVEL_CONFIG, OUTLIER_METHOD_OPTIONS } from '@/types'

const { Text, Title } = Typography

interface DataQualityReportProps {
  report: QualityReportType | null
  loading?: boolean
  onRefresh?: (method: OutlierMethod) => void
  onOpenCleaning?: () => void
}

export default function DataQualityReport({
  report,
  loading = false,
  onRefresh,
  onOpenCleaning,
}: DataQualityReportProps) {
  const [outlierMethod, setOutlierMethod] = useState<OutlierMethod>('iqr')

  // 质量等级配置
  const qualityConfig = useMemo(() => {
    if (!report) return QUALITY_LEVEL_CONFIG.fair
    return QUALITY_LEVEL_CONFIG[report.quality_level] || QUALITY_LEVEL_CONFIG.fair
  }, [report])

  // 质量评分进度条颜色
  const getScoreColor = (score: number) => {
    if (score >= 90) return '#52c41a'
    if (score >= 70) return '#1890ff'
    if (score >= 50) return '#faad14'
    return '#ff4d4f'
  }

  // 缺失值表格列
  const missingColumns: ColumnsType<ColumnMissingStats> = [
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
      width: 200,
      ellipsis: true,
    },
    {
      title: '缺失数量',
      dataIndex: 'missing_count',
      key: 'missing_count',
      width: 120,
      sorter: (a, b) => a.missing_count - b.missing_count,
    },
    {
      title: '缺失率',
      dataIndex: 'missing_ratio',
      key: 'missing_ratio',
      width: 150,
      sorter: (a, b) => a.missing_ratio - b.missing_ratio,
      render: (ratio: number) => (
        <Space>
          <Progress
            percent={Math.round(ratio * 100)}
            size="small"
            style={{ width: 80 }}
            strokeColor={ratio > 0.1 ? '#ff4d4f' : ratio > 0.01 ? '#faad14' : '#52c41a'}
          />
          <Text>{(ratio * 100).toFixed(2)}%</Text>
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_, record) => {
        if (record.missing_ratio === 0) {
          return <Tag color="success">完整</Tag>
        } else if (record.missing_ratio > 0.5) {
          return <Tag color="error">严重缺失</Tag>
        } else if (record.missing_ratio > 0.1) {
          return <Tag color="warning">较多缺失</Tag>
        } else {
          return <Tag color="processing">少量缺失</Tag>
        }
      },
    },
  ]

  // 异常值表格列
  const outlierColumns: ColumnsType<ColumnOutlierStats> = [
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
      width: 150,
      ellipsis: true,
    },
    {
      title: '异常数量',
      dataIndex: 'outlier_count',
      key: 'outlier_count',
      width: 100,
      sorter: (a, b) => a.outlier_count - b.outlier_count,
    },
    {
      title: '异常率',
      dataIndex: 'outlier_ratio',
      key: 'outlier_ratio',
      width: 120,
      sorter: (a, b) => a.outlier_ratio - b.outlier_ratio,
      render: (ratio: number) => (
        <Text type={ratio > 0.05 ? 'danger' : ratio > 0.01 ? 'warning' : undefined}>
          {(ratio * 100).toFixed(2)}%
        </Text>
      ),
    },
    {
      title: '下界',
      dataIndex: 'lower_bound',
      key: 'lower_bound',
      width: 120,
      render: (val: number | null) => val !== null ? val.toFixed(4) : '-',
    },
    {
      title: '上界',
      dataIndex: 'upper_bound',
      key: 'upper_bound',
      width: 120,
      render: (val: number | null) => val !== null ? val.toFixed(4) : '-',
    },
    {
      title: '范围',
      key: 'range',
      width: 180,
      render: (_, record) => (
        <Text type="secondary">
          [{record.min_value.toFixed(2)}, {record.max_value.toFixed(2)}]
        </Text>
      ),
    },
  ]

  // 列统计表格列
  const statsColumns: ColumnsType<ColumnBasicStats> = [
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
      width: 150,
      fixed: 'left',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'dtype',
      key: 'dtype',
      width: 100,
    },
    {
      title: '均值',
      dataIndex: 'mean',
      key: 'mean',
      width: 120,
      render: (val?: number) => val !== undefined ? val.toFixed(4) : '-',
    },
    {
      title: '标准差',
      dataIndex: 'std',
      key: 'std',
      width: 120,
      render: (val?: number) => val !== undefined ? val.toFixed(4) : '-',
    },
    {
      title: '最小值',
      dataIndex: 'min',
      key: 'min',
      width: 120,
      render: (val?: number) => val !== undefined ? val.toFixed(4) : '-',
    },
    {
      title: '中位数',
      dataIndex: 'median',
      key: 'median',
      width: 120,
      render: (val?: number) => val !== undefined ? val.toFixed(4) : '-',
    },
    {
      title: '最大值',
      dataIndex: 'max',
      key: 'max',
      width: 120,
      render: (val?: number) => val !== undefined ? val.toFixed(4) : '-',
    },
  ]

  // 建议图标
  const getSuggestionIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />
      default:
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />
    }
  }

  // 缺失值分布图表
  const getMissingChartOption = () => {
    if (!report?.missing_stats) return {}

    const data = report.missing_stats
      .filter(s => s.missing_count > 0)
      .sort((a, b) => b.missing_ratio - a.missing_ratio)
      .slice(0, 10)

    return {
      title: { text: '缺失值分布 (Top 10)', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const item = params[0]
          return `${item.name}<br/>缺失率: ${(item.value * 100).toFixed(2)}%`
        },
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: data.map(d => d.column),
        axisLabel: { rotate: 45, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: (val: number) => `${(val * 100).toFixed(0)}%` },
      },
      series: [{
        type: 'bar',
        data: data.map(d => d.missing_ratio),
        itemStyle: {
          color: (params: any) => {
            const ratio = params.value
            if (ratio > 0.5) return '#ff4d4f'
            if (ratio > 0.1) return '#faad14'
            return '#1890ff'
          },
        },
      }],
    }
  }

  // 异常值分布图表
  const getOutlierChartOption = () => {
    if (!report?.outlier_stats) return {}

    const data = report.outlier_stats
      .filter(s => s.outlier_count > 0)
      .sort((a, b) => b.outlier_ratio - a.outlier_ratio)
      .slice(0, 10)

    return {
      title: { text: '异常值分布 (Top 10)', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const item = params[0]
          return `${item.name}<br/>异常率: ${(item.value * 100).toFixed(2)}%`
        },
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: data.map(d => d.column),
        axisLabel: { rotate: 45, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: (val: number) => `${(val * 100).toFixed(0)}%` },
      },
      series: [{
        type: 'bar',
        data: data.map(d => d.outlier_ratio),
        itemStyle: {
          color: (params: any) => {
            const ratio = params.value
            if (ratio > 0.1) return '#ff4d4f'
            if (ratio > 0.05) return '#faad14'
            return '#52c41a'
          },
        },
      }],
    }
  }

  if (!report) {
    return (
      <Card loading={loading}>
        <Empty description="暂无质量报告" />
      </Card>
    )
  }

  return (
    <div>
      {/* 概览卡片 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} sm={12} md={6}>
            <div style={{ textAlign: 'center' }}>
              <Progress
                type="dashboard"
                percent={report.quality_score}
                strokeColor={getScoreColor(report.quality_score)}
                format={(percent) => (
                  <div>
                    <div style={{ fontSize: 24, fontWeight: 'bold' }}>{percent}</div>
                    <div style={{ fontSize: 12, color: qualityConfig.color }}>
                      {qualityConfig.label}
                    </div>
                  </div>
                )}
              />
            </div>
          </Col>
          <Col xs={24} sm={12} md={18}>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Statistic title="总行数" value={report.total_rows} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="总列数" value={report.total_columns} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="缺失率"
                  value={report.total_missing_ratio * 100}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: report.total_missing_ratio > 0.1 ? '#ff4d4f' : undefined }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="异常率"
                  value={report.total_outlier_ratio * 100}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: report.total_outlier_ratio > 0.05 ? '#ff4d4f' : undefined }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="重复行"
                  value={report.duplicate_rows}
                  valueStyle={{ color: report.duplicate_rows > 0 ? '#faad14' : undefined }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="数值列" value={report.numeric_columns.length} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="分类列" value={report.categorical_columns.length} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="时间列" value={report.datetime_columns.length} />
              </Col>
            </Row>
          </Col>
        </Row>

        {/* 操作按钮 */}
        <Row justify="end" style={{ marginTop: 16 }}>
          <Space>
            <Select
              value={outlierMethod}
              onChange={(val) => setOutlierMethod(val)}
              style={{ width: 180 }}
              options={OUTLIER_METHOD_OPTIONS.map(opt => ({
                value: opt.value,
                label: opt.label,
              }))}
            />
            <Tooltip title="重新检测">
              <Button
                icon={<ReloadOutlined />}
                onClick={() => onRefresh?.(outlierMethod)}
                loading={loading}
              >
                刷新
              </Button>
            </Tooltip>
            <Button
              type="primary"
              icon={<ToolOutlined />}
              onClick={onOpenCleaning}
            >
              数据清洗
            </Button>
          </Space>
        </Row>
      </Card>

      {/* 建议提示 */}
      {report.suggestions.length > 0 && (
        <Card title="改进建议" style={{ marginBottom: 16 }} size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            {report.suggestions.slice(0, 5).map((suggestion, index) => (
              <Alert
                key={index}
                type={suggestion.level === 'error' ? 'error' : suggestion.level === 'warning' ? 'warning' : 'info'}
                icon={getSuggestionIcon(suggestion.level)}
                message={
                  <Space>
                    {suggestion.column && <Tag>{suggestion.column}</Tag>}
                    <Text>{suggestion.issue}</Text>
                  </Space>
                }
                description={suggestion.suggestion}
                showIcon
              />
            ))}
            {report.suggestions.length > 5 && (
              <Text type="secondary">还有 {report.suggestions.length - 5} 条建议...</Text>
            )}
          </Space>
        </Card>
      )}

      {/* 详细信息 Tabs */}
      <Card>
        <Tabs
          items={[
            {
              key: 'missing',
              label: (
                <span>
                  <WarningOutlined />
                  缺失值分析
                  {report.total_missing_cells > 0 && (
                    <Tag color="warning" style={{ marginLeft: 8 }}>
                      {report.total_missing_cells}
                    </Tag>
                  )}
                </span>
              ),
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Table
                      columns={missingColumns}
                      dataSource={report.missing_stats.map((s, i) => ({ ...s, key: i }))}
                      size="small"
                      pagination={{ pageSize: 10 }}
                      scroll={{ x: 500 }}
                    />
                  </Col>
                  <Col xs={24} lg={12}>
                    {report.missing_stats.some(s => s.missing_count > 0) ? (
                      <ReactECharts option={getMissingChartOption()} style={{ height: 300 }} />
                    ) : (
                      <div style={{ textAlign: 'center', padding: 50 }}>
                        <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
                        <Title level={5} style={{ marginTop: 16 }}>数据完整，无缺失值</Title>
                      </div>
                    )}
                  </Col>
                </Row>
              ),
            },
            {
              key: 'outliers',
              label: (
                <span>
                  <CloseCircleOutlined />
                  异常值检测
                  {report.total_outlier_cells > 0 && (
                    <Tag color="error" style={{ marginLeft: 8 }}>
                      {report.total_outlier_cells}
                    </Tag>
                  )}
                </span>
              ),
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={14}>
                    <Table
                      columns={outlierColumns}
                      dataSource={report.outlier_stats.map((s, i) => ({ ...s, key: i }))}
                      size="small"
                      pagination={{ pageSize: 10 }}
                      scroll={{ x: 700 }}
                    />
                  </Col>
                  <Col xs={24} lg={10}>
                    {report.outlier_stats.some(s => s.outlier_count > 0) ? (
                      <ReactECharts option={getOutlierChartOption()} style={{ height: 300 }} />
                    ) : (
                      <div style={{ textAlign: 'center', padding: 50 }}>
                        <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
                        <Title level={5} style={{ marginTop: 16 }}>未检测到异常值</Title>
                      </div>
                    )}
                  </Col>
                </Row>
              ),
            },
            {
              key: 'stats',
              label: (
                <span>
                  <InfoCircleOutlined />
                  列统计信息
                </span>
              ),
              children: (
                <Table
                  columns={statsColumns}
                  dataSource={report.column_stats
                    .filter(s => report.numeric_columns.includes(s.column))
                    .map((s, i) => ({ ...s, key: i }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 900 }}
                />
              ),
            },
            {
              key: 'time',
              label: (
                <span>
                  <InfoCircleOutlined />
                  时序分析
                </span>
              ),
              children: report.time_analysis ? (
                <Descriptions bordered column={{ xs: 1, sm: 2, md: 3 }}>
                  <Descriptions.Item label="时间列">
                    {report.time_analysis.time_column || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="开始时间">
                    {report.time_analysis.start_time || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="结束时间">
                    {report.time_analysis.end_time || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="推断频率">
                    {report.time_analysis.frequency || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="总时长">
                    {report.time_analysis.total_duration || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="是否规则">
                    {report.time_analysis.is_regular ? (
                      <Tag color="success">规则</Tag>
                    ) : (
                      <Tag color="warning">不规则</Tag>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="间隔异常数">
                    {report.time_analysis.gaps_count}
                  </Descriptions.Item>
                </Descriptions>
              ) : (
                <Empty description="未检测到时间列" />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

