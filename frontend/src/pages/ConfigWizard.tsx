/**
 * 配置向导页面
 * 功能：分步创建实验配置，生成标准文件名
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Steps,
  Button,
  Form,
  Select,
  Transfer,
  Radio,
  Switch,
  InputNumber,
  Space,
  Table,
  Modal,
  Input,
  Popconfirm,
  Typography,
  Divider,
  Alert,
  Tag,
  Tooltip,
  Empty,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { TransferProps } from 'antd/es/transfer'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'

import type { Dataset, Configuration, ConfigurationCreate, ConfigurationUpdate } from '@/types'
import { getDatasets } from '@/api/datasets'
import {
  getConfigurations,
  createConfiguration,
  updateConfiguration,
  deleteConfiguration,
  generateFilename,
} from '@/api/configurations'
import { formatDateTime } from '@/utils/format'
import {
  NORMALIZATION_OPTIONS,
  TARGET_TYPE_OPTIONS,
  ANOMALY_TYPE_OPTIONS,
  INJECTION_ALGORITHM_OPTIONS,
  SEQUENCE_LOGIC_OPTIONS,
} from '@/constants'

const { Title, Text, Paragraph } = Typography

// 步骤定义
const STEPS = [
  { title: '选择数据集', description: '选择要配置的数据集' },
  { title: '选择通道', description: '选择要使用的数据列' },
  { title: '归一化', description: '配置数据归一化方式' },
  { title: '异常注入', description: '配置异常注入（可选）' },
  { title: '窗口参数', description: '设置滑动窗口参数' },
  { title: '预览确认', description: '预览配置并生成文件名' },
]

// Transfer 数据项类型
interface TransferItem {
  key: string
  title: string
}

export default function ConfigWizard() {
  // ============ 状态定义 ============
  // 配置列表
  const [configurations, setConfigurations] = useState<Configuration[]>([])
  const [configLoading, setConfigLoading] = useState(false)

  // 数据集列表
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [datasetsLoading, setDatasetsLoading] = useState(false)

  // 向导状态
  const [wizardOpen, setWizardOpen] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm()

  // 选中的数据集
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null)

  // Transfer 状态
  const [targetKeys, setTargetKeys] = useState<string[]>([])

  // 生成的文件名
  const [generatedFilename, setGeneratedFilename] = useState('')
  const [filenameLoading, setFilenameLoading] = useState(false)

  // 提交状态
  const [submitting, setSubmitting] = useState(false)

  // 编辑状态
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<Configuration | null>(null)
  const [editForm] = Form.useForm()
  const [editLoading, setEditLoading] = useState(false)

  // ============ 数据获取 ============
  const fetchConfigurations = useCallback(async () => {
    setConfigLoading(true)
    try {
      const data = await getConfigurations()
      setConfigurations(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setConfigLoading(false)
    }
  }, [])

  const fetchDatasets = useCallback(async () => {
    setDatasetsLoading(true)
    try {
      const data = await getDatasets()
      setDatasets(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setDatasetsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfigurations()
    fetchDatasets()
  }, [fetchConfigurations, fetchDatasets])

  // ============ 向导控制 ============
  const handleWizardOpen = () => {
    setWizardOpen(true)
    setCurrentStep(0)
    setSelectedDataset(null)
    setTargetKeys([])
    setGeneratedFilename('')
    form.resetFields()
    form.setFieldsValue({
      normalization: 'none',
      anomaly_enabled: false,
      window_size: 100,
      stride: 1,
      target_type: 'next',
      target_k: 1,
    })
  }

  const handleWizardClose = () => {
    if (submitting) return
    setWizardOpen(false)
    setCurrentStep(0)
    setSelectedDataset(null)
    setTargetKeys([])
    setGeneratedFilename('')
    form.resetFields()
  }

  // ============ 步骤导航 ============
  const validateCurrentStep = async (): Promise<boolean> => {
    try {
      switch (currentStep) {
        case 0: // 选择数据集
          await form.validateFields(['dataset_id'])
          return true
        case 1: // 选择通道
          if (targetKeys.length === 0) {
            message.error('请至少选择一个通道')
            return false
          }
          return true
        case 2: // 归一化
          await form.validateFields(['normalization'])
          return true
        case 3: // 异常注入
          const anomalyEnabled = form.getFieldValue('anomaly_enabled')
          if (anomalyEnabled) {
            await form.validateFields(['anomaly_type', 'injection_algorithm', 'sequence_logic'])
          }
          return true
        case 4: // 窗口参数
          const targetType = form.getFieldValue('target_type')
          const fieldsToValidate = ['window_size', 'stride', 'target_type']
          if (targetType === 'kstep') {
            fieldsToValidate.push('target_k')
          }
          await form.validateFields(fieldsToValidate)
          return true
        default:
          return true
      }
    } catch {
      return false
    }
  }

  const handleNext = async () => {
    const valid = await validateCurrentStep()
    if (!valid) return

    if (currentStep === 4) {
      // 进入预览步骤，生成文件名
      await handleGenerateFilename()
    }

    setCurrentStep((s) => s + 1)
  }

  const handlePrev = () => {
    setCurrentStep((s) => s - 1)
  }

  // ============ 数据集选择 ============
  const handleDatasetChange = (datasetId: number) => {
    const dataset = datasets.find((d) => d.id === datasetId)
    setSelectedDataset(dataset || null)
    setTargetKeys([]) // 重置通道选择
  }

  // ============ Transfer 配置 ============
  const transferDataSource: TransferItem[] = selectedDataset
    ? selectedDataset.columns.map((col) => ({ key: col, title: col }))
    : []

  const handleTransferChange: TransferProps['onChange'] = (newTargetKeys) => {
    setTargetKeys(newTargetKeys as string[])
  }

  // ============ 生成文件名 ============
  const handleGenerateFilename = async () => {
    if (!selectedDataset) return

    setFilenameLoading(true)
    try {
      const values = form.getFieldsValue()
      const response = await generateFilename({
        dataset_name: selectedDataset.name,
        channels: targetKeys,
        normalization: values.normalization,
        anomaly_enabled: values.anomaly_enabled,
        anomaly_type: values.anomaly_enabled ? values.anomaly_type : '',
        injection_algorithm: values.anomaly_enabled ? values.injection_algorithm : '',
        sequence_logic: values.anomaly_enabled ? values.sequence_logic : '',
        window_size: values.window_size,
        stride: values.stride,
        target_type: values.target_type,
        target_k: values.target_k,
      })
      setGeneratedFilename(response.filename)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setFilenameLoading(false)
    }
  }

  // ============ 提交配置 ============
  const handleSubmit = async () => {
    if (!selectedDataset) return

    try {
      await form.validateFields(['name'])
      const values = form.getFieldsValue()

      setSubmitting(true)

      const configData: ConfigurationCreate = {
        name: values.name,
        dataset_id: selectedDataset.id,
        channels: targetKeys,
        normalization: values.normalization,
        anomaly_enabled: values.anomaly_enabled,
        anomaly_type: values.anomaly_enabled ? values.anomaly_type : undefined,
        injection_algorithm: values.anomaly_enabled ? values.injection_algorithm : undefined,
        sequence_logic: values.anomaly_enabled ? values.sequence_logic : undefined,
        window_size: values.window_size,
        stride: values.stride,
        target_type: values.target_type,
        target_k: values.target_type === 'kstep' ? values.target_k : undefined,
      }

      await createConfiguration(configData)
      message.success('配置创建成功')
      setSubmitting(false)
      handleWizardClose()
      fetchConfigurations()
    } catch {
      // 错误已在 API 层处理
      setSubmitting(false)
    }
  }

  // ============ 复制文件名 ============
  const handleCopyFilename = async () => {
    try {
      await navigator.clipboard.writeText(generatedFilename)
      message.success('文件名已复制到剪贴板')
    } catch {
      message.error('复制失败，请手动复制')
    }
  }

  // ============ 编辑配置 ============
  const handleEditOpen = (config: Configuration) => {
    setEditingConfig(config)
    setEditModalOpen(true)
    editForm.setFieldsValue({
      name: config.name,
    })
  }

  const handleEditClose = () => {
    setEditModalOpen(false)
    setEditingConfig(null)
    editForm.resetFields()
  }

  const handleEditSubmit = async () => {
    if (!editingConfig) return

    try {
      const values = await editForm.validateFields()
      setEditLoading(true)

      const updateData: ConfigurationUpdate = {}
      if (values.name !== editingConfig.name) {
        updateData.name = values.name
      }

      if (Object.keys(updateData).length === 0) {
        message.info('没有修改')
        setEditLoading(false)
        handleEditClose()
        return
      }

      await updateConfiguration(editingConfig.id, updateData)
      message.success('更新成功')
      setEditLoading(false)
      handleEditClose()
      fetchConfigurations()
    } catch {
      // 错误已在 API 层处理
      setEditLoading(false)
    }
  }

  // ============ 删除配置 ============
  const handleDelete = async (config: Configuration) => {
    try {
      await deleteConfiguration(config.id)
      message.success('删除成功')
      fetchConfigurations()
    } catch {
      // 错误已在 API 层处理
    }
  }

  // ============ 渲染步骤内容 ============
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <Form.Item
            name="dataset_id"
            label="选择数据集"
            rules={[{ required: true, message: '请选择数据集' }]}
          >
            <Select
              placeholder="请选择数据集"
              loading={datasetsLoading}
              onChange={handleDatasetChange}
              showSearch
              optionFilterProp="children"
              style={{ width: '100%' }}
            >
              {datasets.map((dataset) => (
                <Select.Option key={dataset.id} value={dataset.id}>
                  {dataset.name} ({dataset.column_count} 列, {dataset.row_count.toLocaleString()} 行)
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        )

      case 1:
        return (
          <div>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              从左侧选择要使用的数据列，移动到右侧
            </Text>
            <Transfer
              dataSource={transferDataSource}
              titles={['可用列', '已选列']}
              targetKeys={targetKeys}
              onChange={handleTransferChange}
              render={(item) => item.title}
              listStyle={{ width: 280, height: 350 }}
              showSearch
              filterOption={(inputValue, item) =>
                item.title.toLowerCase().includes(inputValue.toLowerCase())
              }
            />
          </div>
        )

      case 2:
        return (
          <Form.Item
            name="normalization"
            label="归一化方式"
            rules={[{ required: true, message: '请选择归一化方式' }]}
          >
            <Radio.Group>
              {NORMALIZATION_OPTIONS.map((opt) => (
                <Radio key={opt.value} value={opt.value} style={{ display: 'block', marginBottom: 8 }}>
                  {opt.label}
                </Radio>
              ))}
            </Radio.Group>
          </Form.Item>
        )

      case 3:
        return (
          <div>
            <Form.Item name="anomaly_enabled" label="启用异常注入" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item noStyle shouldUpdate={(prev, curr) => prev.anomaly_enabled !== curr.anomaly_enabled}>
              {({ getFieldValue }) =>
                getFieldValue('anomaly_enabled') && (
                  <>
                    <Form.Item
                      name="anomaly_type"
                      label="异常类型"
                      rules={[{ required: true, message: '请选择异常类型' }]}
                    >
                      <Select placeholder="请选择异常类型">
                        {ANOMALY_TYPE_OPTIONS.map((opt) => (
                          <Select.Option key={opt.value} value={opt.value}>
                            {opt.label}
                          </Select.Option>
                        ))}
                      </Select>
                    </Form.Item>

                    <Form.Item
                      name="injection_algorithm"
                      label="注入算法"
                      rules={[{ required: true, message: '请选择注入算法' }]}
                    >
                      <Select placeholder="请选择注入算法">
                        {INJECTION_ALGORITHM_OPTIONS.map((opt) => (
                          <Select.Option key={opt.value} value={opt.value}>
                            {opt.label}
                          </Select.Option>
                        ))}
                      </Select>
                    </Form.Item>

                    <Form.Item
                      name="sequence_logic"
                      label="序列逻辑"
                      rules={[{ required: true, message: '请选择序列逻辑' }]}
                    >
                      <Select placeholder="请选择序列逻辑">
                        {SEQUENCE_LOGIC_OPTIONS.map((opt) => (
                          <Select.Option key={opt.value} value={opt.value}>
                            {opt.label}
                          </Select.Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </>
                )
              }
            </Form.Item>
          </div>
        )

      case 4:
        return (
          <div>
            <Form.Item
              name="window_size"
              label="窗口大小"
              rules={[{ required: true, message: '请输入窗口大小' }]}
            >
              <InputNumber min={1} max={10000} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item
              name="stride"
              label="步长"
              rules={[{ required: true, message: '请输入步长' }]}
            >
              <InputNumber min={1} max={1000} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item
              name="target_type"
              label="目标类型"
              rules={[{ required: true, message: '请选择目标类型' }]}
            >
              <Radio.Group>
                {TARGET_TYPE_OPTIONS.map((opt) => (
                  <Radio key={opt.value} value={opt.value}>
                    {opt.label}
                  </Radio>
                ))}
              </Radio.Group>
            </Form.Item>

            <Form.Item noStyle shouldUpdate={(prev, curr) => prev.target_type !== curr.target_type}>
              {({ getFieldValue }) =>
                getFieldValue('target_type') === 'kstep' && (
                  <Form.Item
                    name="target_k"
                    label="K 值"
                    rules={[{ required: true, message: '请输入 K 值' }]}
                  >
                    <InputNumber min={1} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                )
              }
            </Form.Item>
          </div>
        )

      case 5:
        const formValues = form.getFieldsValue()
        return (
          <div>
            <Alert
              message="配置预览"
              description="请确认以下配置信息，然后输入配置名称并提交"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Card size="small" style={{ marginBottom: 16 }}>
              <Paragraph>
                <Text strong>数据集：</Text> {selectedDataset?.name}
              </Paragraph>
              <Paragraph>
                <Text strong>选中通道：</Text>{' '}
                {targetKeys.map((key) => (
                  <Tag key={key}>{key}</Tag>
                ))}
              </Paragraph>
              <Paragraph>
                <Text strong>归一化：</Text>{' '}
                {NORMALIZATION_OPTIONS.find((o) => o.value === formValues.normalization)?.label}
              </Paragraph>
              <Paragraph>
                <Text strong>异常注入：</Text>{' '}
                {formValues.anomaly_enabled ? (
                  <>
                    {ANOMALY_TYPE_OPTIONS.find((o) => o.value === formValues.anomaly_type)?.label} /{' '}
                    {INJECTION_ALGORITHM_OPTIONS.find((o) => o.value === formValues.injection_algorithm)?.label} /{' '}
                    {SEQUENCE_LOGIC_OPTIONS.find((o) => o.value === formValues.sequence_logic)?.label}
                  </>
                ) : (
                  '未启用'
                )}
              </Paragraph>
              <Paragraph>
                <Text strong>窗口参数：</Text> 窗口大小 {formValues.window_size}，步长 {formValues.stride}
              </Paragraph>
              <Paragraph>
                <Text strong>目标类型：</Text>{' '}
                {TARGET_TYPE_OPTIONS.find((o) => o.value === formValues.target_type)?.label}
                {formValues.target_type === 'kstep' && ` (K=${formValues.target_k})`}
              </Paragraph>
            </Card>

            <Divider />

            <Form.Item label="生成的标准文件名">
              <Space.Compact style={{ width: '100%' }}>
                <Input
                  value={generatedFilename}
                  readOnly
                  style={{ fontFamily: 'monospace' }}
                  placeholder={filenameLoading ? '生成中...' : ''}
                />
                <Tooltip title="复制文件名">
                  <Button icon={<CopyOutlined />} onClick={handleCopyFilename} disabled={!generatedFilename} />
                </Tooltip>
              </Space.Compact>
            </Form.Item>

            <Form.Item
              name="name"
              label="配置名称"
              rules={[
                { required: true, message: '请输入配置名称' },
                { max: 255, message: '名称不能超过255个字符' },
              ]}
            >
              <Input placeholder="请输入配置名称，用于标识此配置" />
            </Form.Item>
          </div>
        )

      default:
        return null
    }
  }

  // ============ 表格列定义 ============
  const columns: ColumnsType<Configuration> = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '数据集',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      width: 150,
      render: (datasetId: number) => {
        const dataset = datasets.find((d) => d.id === datasetId)
        return dataset?.name || `ID: ${datasetId}`
      },
    },
    {
      title: '通道数',
      dataIndex: 'channels',
      key: 'channels',
      width: 80,
      render: (channels: string[]) => channels.length,
    },
    {
      title: '归一化',
      dataIndex: 'normalization',
      key: 'normalization',
      width: 100,
      render: (norm: string) => NORMALIZATION_OPTIONS.find((o) => o.value === norm)?.label || norm,
    },
    {
      title: '窗口/步长',
      key: 'window',
      width: 100,
      render: (_, record) => `${record.window_size}/${record.stride}`,
    },
    {
      title: '生成文件名',
      dataIndex: 'generated_filename',
      key: 'generated_filename',
      width: 300,
      ellipsis: true,
      render: (filename: string) => (
        <Tooltip title={filename}>
          <Text code style={{ fontSize: 12 }}>
            {filename}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => formatDateTime(date),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditOpen(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description={`确定要删除配置「${record.name}」吗？`}
            onConfirm={() => handleDelete(record)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除">
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // ============ 渲染 ============
  return (
    <div style={{ padding: 24 }}>
      {/* 页面头部 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              ⚙️ 配置向导
            </Title>
            <Text type="secondary">创建和管理实验配置，生成标准文件名</Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleWizardOpen}>
            新建配置
          </Button>
        </div>
      </Card>

      {/* 配置列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={configurations}
          rowKey="id"
          loading={configLoading}
          scroll={{ x: 1300 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个配置`,
            defaultPageSize: 10,
            pageSizeOptions: ['10', '20', '50'],
          }}
          locale={{
            emptyText: (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无配置">
                <Button type="primary" onClick={handleWizardOpen}>
                  创建第一个配置
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      {/* 配置向导 Modal */}
      <Modal
        title="新建配置"
        open={wizardOpen}
        onCancel={handleWizardClose}
        width={700}
        footer={null}
        maskClosable={!submitting}
        closable={!submitting}
      >
        <Steps current={currentStep} items={STEPS} size="small" style={{ marginBottom: 24 }} />

        <Form form={form} layout="vertical" style={{ minHeight: 300 }}>
          {renderStepContent()}
        </Form>

        <Divider />

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button onClick={handleWizardClose} disabled={submitting}>
            取消
          </Button>
          <Space>
            {currentStep > 0 && (
              <Button onClick={handlePrev} disabled={submitting}>
                上一步
              </Button>
            )}
            {currentStep < STEPS.length - 1 && (
              <Button type="primary" onClick={handleNext}>
                下一步
              </Button>
            )}
            {currentStep === STEPS.length - 1 && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={handleSubmit}
                loading={submitting}
              >
                创建配置
              </Button>
            )}
          </Space>
        </div>
      </Modal>

      {/* 编辑 Modal */}
      <Modal
        title="编辑配置"
        open={editModalOpen}
        onCancel={handleEditClose}
        onOk={handleEditSubmit}
        okText="保存"
        cancelText="取消"
        confirmLoading={editLoading}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="配置名称"
            rules={[
              { required: true, message: '请输入配置名称' },
              { max: 255, message: '名称不能超过255个字符' },
            ]}
          >
            <Input placeholder="请输入配置名称" disabled={editLoading} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

