/**
 * 数据清洗配置弹窗组件
 */
import { useState, useEffect } from 'react'
import {
  Modal,
  Form,
  Select,
  InputNumber,
  Switch,
  Input,
  Tabs,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Alert,
  Button,
  Space,
  Typography,
  Divider,
  Tooltip,
  Progress,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ArrowRightOutlined,
  DeleteOutlined,
} from '@ant-design/icons'

import type {
  CleaningConfig,
  CleaningPreviewResponse,
  CleaningPreviewRow,
  CleaningPreviewStats,
  CleaningResult,
  DataQualityReport,
  OutlierMethod,
} from '@/types'
import {
  DEFAULT_CLEANING_CONFIG,
  OUTLIER_METHOD_OPTIONS,
  OUTLIER_ACTION_OPTIONS,
  MISSING_STRATEGY_OPTIONS,
} from '@/types'
import { previewCleaning, applyCleaning } from '@/api/quality'

const { Text } = Typography

interface DataCleaningModalProps {
  visible: boolean
  datasetId: number
  datasetName: string
  qualityReport?: DataQualityReport | null
  onClose: () => void
  onSuccess?: (result: CleaningResult) => void
}

export default function DataCleaningModal({
  visible,
  datasetId,
  datasetName,
  qualityReport: _qualityReport,
  onClose,
  onSuccess,
}: DataCleaningModalProps) {
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('config')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [applyLoading, setApplyLoading] = useState(false)
  const [previewResult, setPreviewResult] = useState<CleaningPreviewResponse | null>(null)

  // 重置状态
  useEffect(() => {
    if (visible) {
      form.setFieldsValue(DEFAULT_CLEANING_CONFIG)
      setPreviewResult(null)
      setActiveTab('config')
    }
  }, [visible, form])

  // 获取当前配置
  const getConfig = (): CleaningConfig => {
    const values = form.getFieldsValue()
    return {
      ...DEFAULT_CLEANING_CONFIG,
      ...values,
      outlier_params: getOutlierParams(values.outlier_method, values),
    }
  }

  // 根据方法获取异常值参数
  const getOutlierParams = (method: OutlierMethod, values: any): Record<string, number> => {
    switch (method) {
      case 'iqr':
        return { multiplier: values.iqr_multiplier || 1.5 }
      case 'zscore':
      case 'mad':
        return { threshold: values.zscore_threshold || 3.0 }
      case 'percentile':
        return {
          lower: values.percentile_lower || 1,
          upper: values.percentile_upper || 99,
        }
      case 'threshold':
        return {
          lower: values.threshold_lower ?? -Infinity,
          upper: values.threshold_upper ?? Infinity,
        }
      default:
        return { multiplier: 1.5 }
    }
  }

  // 预览清洗效果
  const handlePreview = async () => {
    setPreviewLoading(true)
    try {
      const config = getConfig()
      const result = await previewCleaning(datasetId, config)
      setPreviewResult(result)
      setActiveTab('preview')
      message.success('预览生成成功')
    } catch (error) {
      message.error('预览失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  // 执行清洗
  const handleApply = async () => {
    setApplyLoading(true)
    try {
      const config = getConfig()
      const result = await applyCleaning(datasetId, config)
      message.success(result.message)
      onSuccess?.(result)
      onClose()
    } catch (error) {
      message.error('清洗执行失败')
    } finally {
      setApplyLoading(false)
    }
  }

  // 预览变更表格列
  const changeColumns: ColumnsType<CleaningPreviewRow> = [
    {
      title: '行号',
      dataIndex: 'index',
      key: 'index',
      width: 80,
    },
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
      width: 150,
      ellipsis: true,
    },
    {
      title: '原始值',
      dataIndex: 'original_value',
      key: 'original_value',
      width: 120,
      render: (val) => (
        <Text type="secondary" delete={val === null}>
          {val === null ? 'NULL' : String(val)}
        </Text>
      ),
    },
    {
      title: '',
      key: 'arrow',
      width: 50,
      render: () => <ArrowRightOutlined style={{ color: '#1890ff' }} />,
    },
    {
      title: '新值',
      dataIndex: 'new_value',
      key: 'new_value',
      width: 120,
      render: (val) => (
        <Text strong style={{ color: '#52c41a' }}>
          {val === null ? 'NULL' : String(val)}
        </Text>
      ),
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action: string) => {
        const actionMap: Record<string, { color: string; text: string }> = {
          removed: { color: 'error', text: '删除' },
          filled: { color: 'processing', text: '填充' },
          clipped: { color: 'warning', text: '裁剪' },
          replaced: { color: 'success', text: '替换' },
        }
        const config = actionMap[action] || { color: 'default', text: action }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
  ]

  // 统计表格列
  const statsColumns: ColumnsType<CleaningPreviewStats> = [
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
      width: 150,
    },
    {
      title: '原缺失',
      dataIndex: 'original_missing',
      key: 'original_missing',
      width: 100,
    },
    {
      title: '清洗后缺失',
      dataIndex: 'after_missing',
      key: 'after_missing',
      width: 100,
      render: (val, record) => (
        <Text type={val < record.original_missing ? 'success' : undefined}>
          {val}
        </Text>
      ),
    },
    {
      title: '原异常',
      dataIndex: 'original_outliers',
      key: 'original_outliers',
      width: 100,
    },
    {
      title: '清洗后异常',
      dataIndex: 'after_outliers',
      key: 'after_outliers',
      width: 100,
      render: (val, record) => (
        <Text type={val < record.original_outliers ? 'success' : undefined}>
          {val}
        </Text>
      ),
    },
    {
      title: '影响行数',
      dataIndex: 'rows_affected',
      key: 'rows_affected',
      width: 100,
    },
  ]

  // 监听异常值方法变化
  const outlierMethod = Form.useWatch('outlier_method', form)

  return (
    <Modal
      title={`数据清洗 - ${datasetName}`}
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button
          key="preview"
          onClick={handlePreview}
          loading={previewLoading}
        >
          预览效果
        </Button>,
        <Button
          key="apply"
          type="primary"
          onClick={handleApply}
          loading={applyLoading}
          disabled={!previewResult}
        >
          执行清洗
        </Button>,
      ]}
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'config',
            label: '清洗配置',
            children: (
              <Form
                form={form}
                layout="vertical"
                initialValues={DEFAULT_CLEANING_CONFIG}
              >
                {/* 缺失值处理 */}
                <Card title="缺失值处理" size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="missing_strategy"
                        label="处理策略"
                      >
                        <Select options={MISSING_STRATEGY_OPTIONS} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="missing_drop_threshold"
                        label="列删除阈值"
                        tooltip="缺失率超过此值的列将被删除"
                      >
                        <InputNumber
                          min={0}
                          max={1}
                          step={0.1}
                          style={{ width: '100%' }}
                          formatter={(val) => `${(val || 0) * 100}%`}
                          parser={(val) => (parseFloat(val?.replace('%', '') || '0') / 100) as any}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item
                    noStyle
                    shouldUpdate={(prev, curr) => prev.missing_strategy !== curr.missing_strategy}
                  >
                    {({ getFieldValue }) =>
                      getFieldValue('missing_strategy') === 'fill_value' && (
                        <Form.Item
                          name="missing_fill_value"
                          label="填充值"
                        >
                          <InputNumber style={{ width: '100%' }} placeholder="输入填充值" />
                        </Form.Item>
                      )
                    }
                  </Form.Item>
                </Card>

                {/* 异常值处理 */}
                <Card title="异常值处理" size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="outlier_method"
                        label="检测方法"
                      >
                        <Select
                          options={OUTLIER_METHOD_OPTIONS.map(opt => ({
                            value: opt.value,
                            label: (
                              <Tooltip title={opt.description}>
                                {opt.label}
                              </Tooltip>
                            ),
                          }))}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="outlier_action"
                        label="处理方式"
                      >
                        <Select options={OUTLIER_ACTION_OPTIONS} />
                      </Form.Item>
                    </Col>
                  </Row>

                  {/* 方法特定参数 */}
                  {outlierMethod === 'iqr' && (
                    <Form.Item
                      name="iqr_multiplier"
                      label="IQR 倍数"
                      tooltip="默认 1.5，越大越宽松"
                      initialValue={1.5}
                    >
                      <InputNumber min={0.5} max={5} step={0.5} style={{ width: '100%' }} />
                    </Form.Item>
                  )}

                  {(outlierMethod === 'zscore' || outlierMethod === 'mad') && (
                    <Form.Item
                      name="zscore_threshold"
                      label="阈值"
                      tooltip="默认 3.0，越大越宽松"
                      initialValue={3.0}
                    >
                      <InputNumber min={1} max={10} step={0.5} style={{ width: '100%' }} />
                    </Form.Item>
                  )}

                  {outlierMethod === 'percentile' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="percentile_lower"
                          label="下百分位"
                          initialValue={1}
                        >
                          <InputNumber min={0} max={50} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="percentile_upper"
                          label="上百分位"
                          initialValue={99}
                        >
                          <InputNumber min={50} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}

                  {outlierMethod === 'threshold' && (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="threshold_lower"
                          label="下界"
                        >
                          <InputNumber style={{ width: '100%' }} placeholder="不限" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="threshold_upper"
                          label="上界"
                        >
                          <InputNumber style={{ width: '100%' }} placeholder="不限" />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}
                </Card>

                {/* 重复值处理 */}
                <Card title="重复值处理" size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="drop_duplicates"
                        label="删除重复行"
                        valuePropName="checked"
                      >
                        <Switch />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        noStyle
                        shouldUpdate={(prev, curr) => prev.drop_duplicates !== curr.drop_duplicates}
                      >
                        {({ getFieldValue }) =>
                          getFieldValue('drop_duplicates') && (
                            <Form.Item
                              name="duplicate_keep"
                              label="保留策略"
                            >
                              <Select
                                options={[
                                  { value: 'first', label: '保留第一条' },
                                  { value: 'last', label: '保留最后一条' },
                                  { value: 'none', label: '全部删除' },
                                ]}
                              />
                            </Form.Item>
                          )
                        }
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>

                {/* 输出选项 */}
                <Card title="输出选项" size="small">
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="create_new_dataset"
                        label="创建新数据集"
                        valuePropName="checked"
                        tooltip="关闭则覆盖原数据集"
                      >
                        <Switch defaultChecked />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        noStyle
                        shouldUpdate={(prev, curr) => prev.create_new_dataset !== curr.create_new_dataset}
                      >
                        {({ getFieldValue }) =>
                          getFieldValue('create_new_dataset') && (
                            <Form.Item
                              name="new_dataset_suffix"
                              label="新数据集后缀"
                            >
                              <Input placeholder="_cleaned" />
                            </Form.Item>
                          )
                        }
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>
              </Form>
            ),
          },
          {
            key: 'preview',
            label: '预览结果',
            disabled: !previewResult,
            children: previewResult && (
              <div>
                {/* 汇总统计 */}
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={[16, 16]}>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="原始行数"
                        value={previewResult.total_rows_before}
                      />
                    </Col>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="清洗后行数"
                        value={previewResult.total_rows_after}
                        valueStyle={{
                          color: previewResult.rows_removed > 0 ? '#faad14' : '#52c41a',
                        }}
                      />
                    </Col>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="删除行数"
                        value={previewResult.rows_removed}
                        valueStyle={{ color: previewResult.rows_removed > 0 ? '#ff4d4f' : undefined }}
                      />
                    </Col>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="修改单元格"
                        value={previewResult.cells_modified}
                      />
                    </Col>
                  </Row>

                  <Divider style={{ margin: '16px 0' }} />

                  {/* 质量评分对比 */}
                  <Row align="middle" justify="center" gutter={24}>
                    <Col>
                      <div style={{ textAlign: 'center' }}>
                        <Text type="secondary">清洗前</Text>
                        <Progress
                          type="circle"
                          percent={previewResult.quality_score_before}
                          size={80}
                          strokeColor={previewResult.quality_score_before >= 70 ? '#52c41a' : '#faad14'}
                        />
                      </div>
                    </Col>
                    <Col>
                      <ArrowRightOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                    </Col>
                    <Col>
                      <div style={{ textAlign: 'center' }}>
                        <Text type="secondary">清洗后</Text>
                        <Progress
                          type="circle"
                          percent={previewResult.quality_score_after}
                          size={80}
                          strokeColor={previewResult.quality_score_after >= 70 ? '#52c41a' : '#faad14'}
                        />
                      </div>
                    </Col>
                    <Col>
                      <Statistic
                        title="质量提升"
                        value={previewResult.quality_score_after - previewResult.quality_score_before}
                        prefix={previewResult.quality_score_after > previewResult.quality_score_before ? '+' : ''}
                        suffix="分"
                        valueStyle={{
                          color: previewResult.quality_score_after > previewResult.quality_score_before
                            ? '#52c41a'
                            : previewResult.quality_score_after < previewResult.quality_score_before
                            ? '#ff4d4f'
                            : undefined,
                        }}
                      />
                    </Col>
                  </Row>
                </Card>

                {/* 删除的列 */}
                {previewResult.columns_removed.length > 0 && (
                  <Alert
                    type="warning"
                    icon={<DeleteOutlined />}
                    message={`将删除 ${previewResult.columns_removed.length} 列`}
                    description={
                      <Space wrap>
                        {previewResult.columns_removed.map((col) => (
                          <Tag key={col} color="error">{col}</Tag>
                        ))}
                      </Space>
                    }
                    style={{ marginBottom: 16 }}
                    showIcon
                  />
                )}

                {/* 变更详情 */}
                <Card title="变更详情（前100条）" size="small" style={{ marginBottom: 16 }}>
                  <Table
                    columns={changeColumns}
                    dataSource={previewResult.preview_changes.map((c, i) => ({ ...c, key: i }))}
                    size="small"
                    pagination={{ pageSize: 10 }}
                    scroll={{ x: 600 }}
                  />
                </Card>

                {/* 列统计 */}
                {previewResult.stats.length > 0 && (
                  <Card title="列统计变化" size="small">
                    <Table
                      columns={statsColumns}
                      dataSource={previewResult.stats.map((s, i) => ({ ...s, key: i }))}
                      size="small"
                      pagination={{ pageSize: 10 }}
                    />
                  </Card>
                )}
              </div>
            ),
          },
        ]}
      />
    </Modal>
  )
}

