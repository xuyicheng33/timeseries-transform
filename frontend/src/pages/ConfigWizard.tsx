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
  Collapse,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { TransferProps } from 'antd/es/transfer'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  RocketOutlined,
  SettingOutlined,
} from '@ant-design/icons'

import type { Dataset, Configuration, ConfigurationCreate, ConfigurationUpdate, ModelTemplateBrief } from '@/types'
import { MODEL_CATEGORY_CONFIG, TASK_TYPE_CONFIG } from '@/types/modelTemplate'
import type { TaskType } from '@/types/modelTemplate'
import {
  getConfigurations,
  createConfiguration,
  updateConfiguration,
  deleteConfiguration,
  generateFilename,
} from '@/api/configurations'
import { getAllModelTemplates, getModelTemplate } from '@/api/modelTemplates'
import { formatDateTime } from '@/utils/format'
import {
  NORMALIZATION_OPTIONS,
  NORMALIZATION_GROUPS,
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
  { title: '模型模板', description: '选择模型模板（可选）' },
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
  const [configTotal, setConfigTotal] = useState(0)
  const [configPage, setConfigPage] = useState(1)
  const [configPageSize, setConfigPageSize] = useState(10)

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

  // 步骤切换状态（防止连点跳步）
  const [stepLoading, setStepLoading] = useState(false)

  // 编辑状态
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<Configuration | null>(null)
  const [editForm] = Form.useForm()
  const [editLoading, setEditLoading] = useState(false)

  // 模型模板状态
  const [modelTemplates, setModelTemplates] = useState<ModelTemplateBrief[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [selectedTemplateDetail, setSelectedTemplateDetail] = useState<any>(null)
  const [templatesLoading, setTemplatesLoading] = useState(false)

  // ============ 数据获取 ============
  const fetchConfigurations = useCallback(async () => {
    setConfigLoading(true)
    try {
      const response = await getConfigurations(undefined, configPage, configPageSize)
      setConfigurations(response.items)
      setConfigTotal(response.total)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setConfigLoading(false)
    }
  }, [configPage, configPageSize])

  const fetchDatasets = useCallback(async () => {
    setDatasetsLoading(true)
    try {
      const { getAllDatasets } = await import('@/api/datasets')
      const data = await getAllDatasets()
      setDatasets(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setDatasetsLoading(false)
    }
  }, [])

  const fetchModelTemplates = useCallback(async () => {
    setTemplatesLoading(true)
    try {
      const data = await getAllModelTemplates()
      setModelTemplates(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setTemplatesLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfigurations()
    fetchDatasets()
    fetchModelTemplates()
  }, [fetchConfigurations, fetchDatasets, fetchModelTemplates])

  // ============ 向导控制 ============
  const handleWizardOpen = () => {
    setWizardOpen(true)
    setCurrentStep(0)
    setSelectedDataset(null)
    setTargetKeys([])
    setGeneratedFilename('')
    setSelectedTemplateId(null)
    setSelectedTemplateDetail(null)
    form.resetFields()
    form.setFieldsValue({
      normalization: 'none',
      anomaly_enabled: false,
      window_size: 100,
      stride: 1,
      target_type: 'next',
      target_k: 1,
      model_template_id: null,
    })
  }

  const handleWizardClose = () => {
    if (submitting) return
    setWizardOpen(false)
    setCurrentStep(0)
    setSelectedDataset(null)
    setTargetKeys([])
    setGeneratedFilename('')
    setSelectedTemplateId(null)
    setSelectedTemplateDetail(null)
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
        case 5: // 模型模板（可选，无需验证）
          return true
        default:
          return true
      }
    } catch {
      return false
    }
  }

  const handleNext = async () => {
    if (stepLoading) return
    setStepLoading(true)

    try {
      const valid = await validateCurrentStep()
      if (!valid) return

      if (currentStep === 5) {
        // 进入预览步骤，生成文件名
        await handleGenerateFilename()
      }

      setCurrentStep((s) => s + 1)
    } finally {
      setStepLoading(false)
    }
  }

  const handlePrev = () => {
    if (stepLoading) return
    setCurrentStep((s) => s - 1)
  }

  // ============ 数据集选择 ============
  const handleDatasetChange = (datasetId: number) => {
    const dataset = datasets.find((d) => d.id === datasetId)
    setSelectedDataset(dataset || null)
    setTargetKeys([]) // 重置通道选择
  }

  // ============ 模型模板选择 ============
  const handleTemplateChange = async (templateId: number | null) => {
    setSelectedTemplateId(templateId)
    if (templateId) {
      try {
        const detail = await getModelTemplate(templateId)
        setSelectedTemplateDetail(detail)
      } catch {
        setSelectedTemplateDetail(null)
      }
    } else {
      setSelectedTemplateDetail(null)
    }
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
      // 使用 getFieldsValue(true) 获取所有字段值，包括未渲染的
      const values = form.getFieldsValue(true)
      const targetType = values.target_type || 'next'
      // 当 target_type 是 kstep 时，使用用户输入的 target_k，否则默认为 1
      const targetK = targetType === 'kstep' ? (values.target_k || 1) : 1
      
      const response = await generateFilename({
        dataset_name: selectedDataset.name,
        channels: targetKeys,
        // 确保必填字段有默认值，避免 undefined 被 axios 丢弃
        normalization: values.normalization || 'none',
        anomaly_enabled: values.anomaly_enabled ?? false,
        anomaly_type: values.anomaly_enabled ? (values.anomaly_type || '') : '',
        injection_algorithm: values.anomaly_enabled ? (values.injection_algorithm || '') : '',
        sequence_logic: values.anomaly_enabled ? (values.sequence_logic || '') : '',
        window_size: values.window_size || 100,
        stride: values.stride || 1,
        target_type: targetType,
        target_k: targetK,
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
        // 确保必填字段有默认值
        normalization: values.normalization || 'none',
        anomaly_enabled: values.anomaly_enabled ?? false,
        anomaly_type: values.anomaly_enabled ? (values.anomaly_type || '') : '',
        injection_algorithm: values.anomaly_enabled ? (values.injection_algorithm || '') : '',
        sequence_logic: values.anomaly_enabled ? (values.sequence_logic || '') : '',
        window_size: values.window_size || 100,
        stride: values.stride || 1,
        target_type: values.target_type || 'next',
        target_k: values.target_type === 'kstep' ? (values.target_k || 1) : 1,
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
          <div>
            <Form.Item
              name="normalization"
              label="归一化方式"
              rules={[{ required: true, message: '请选择归一化方式' }]}
              initialValue="none"
              tooltip="选择适合您数据特征的归一化方法"
            >
              <Select
                placeholder="请选择归一化方式"
                style={{ width: '100%' }}
                optionLabelProp="label"
              >
                {NORMALIZATION_GROUPS.map((group) => (
                  <Select.OptGroup key={group.label} label={group.label}>
                    {group.options.map((opt) => {
                      const fullOpt = NORMALIZATION_OPTIONS.find(o => o.value === opt.value)
                      return (
                        <Select.Option key={opt.value} value={opt.value} label={opt.label}>
                          <div>
                            <Text strong>{opt.label}</Text>
                            {fullOpt?.description && (
                              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                                - {fullOpt.description}
                              </Text>
                            )}
                          </div>
                        </Select.Option>
                      )
                    })}
                  </Select.OptGroup>
                ))}
              </Select>
            </Form.Item>
            
            <Alert
              message="归一化方法说明"
              description={
                <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                  <li><Text strong>基础方法：</Text>MinMax、Z-Score 适用于大多数场景</li>
                  <li><Text strong>鲁棒方法：</Text>Robust、MaxAbs 对异常值不敏感</li>
                  <li><Text strong>变换方法：</Text>Log、Box-Cox 适合长尾分布或偏态数据</li>
                  <li><Text strong>分布变换：</Text>Quantile、Rank 将数据映射到特定分布</li>
                </ul>
              }
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </div>
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
        // 模型模板选择（可选）
        return (
          <div>
            <Alert
              message="模型模板（可选）"
              description="选择一个预定义的模型模板，可以帮助您快速配置训练参数。此步骤为可选，您也可以跳过。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item
              name="model_template_id"
              label={
                <Space>
                  <RocketOutlined />
                  选择模型模板
                </Space>
              }
            >
              <Select
                placeholder="选择模型模板（可选）"
                loading={templatesLoading}
                onChange={handleTemplateChange}
                allowClear
                showSearch
                optionFilterProp="children"
                style={{ width: '100%' }}
              >
                {modelTemplates.map((template) => {
                  const categoryConfig = MODEL_CATEGORY_CONFIG[template.category as keyof typeof MODEL_CATEGORY_CONFIG] || MODEL_CATEGORY_CONFIG.other
                  return (
                    <Select.Option key={template.id} value={template.id}>
                      <Space>
                        <span>{categoryConfig.icon}</span>
                        <span>{template.name}</span>
                        <Tag>{`v${template.version}`}</Tag>
                        {template.is_system && <Tag color="gold">系统</Tag>}
                      </Space>
                    </Select.Option>
                  )
                })}
              </Select>
            </Form.Item>

            {selectedTemplateDetail && (
              <Card 
                size="small" 
                title={
                  <Space>
                    <SettingOutlined />
                    模板详情: {selectedTemplateDetail.name}
                  </Space>
                }
                style={{ marginTop: 16 }}
              >
                <Paragraph>
                  <Text type="secondary">{selectedTemplateDetail.description || '暂无描述'}</Text>
                </Paragraph>
                
                {selectedTemplateDetail.task_types?.length > 0 && (
                  <Paragraph>
                    <Text strong>适用任务：</Text>
                    <Space size={[0, 4]} wrap style={{ marginLeft: 8 }}>
                      {selectedTemplateDetail.task_types.map((type: TaskType) => {
                        const config = TASK_TYPE_CONFIG[type]
                        return config ? (
                          <Tag key={type} color={config.color}>{config.label}</Tag>
                        ) : null
                      })}
                    </Space>
                  </Paragraph>
                )}

                {selectedTemplateDetail.recommended_features && (
                  <Paragraph>
                    <Text strong>推荐场景：</Text>
                    <Text type="secondary" style={{ marginLeft: 8 }}>
                      {selectedTemplateDetail.recommended_features}
                    </Text>
                  </Paragraph>
                )}

                <Collapse
                  size="small"
                  items={[
                    {
                      key: 'hyperparameters',
                      label: '超参数配置',
                      children: (
                        <pre style={{ 
                          background: '#f5f5f5', 
                          padding: 8, 
                          borderRadius: 4, 
                          fontSize: 12,
                          maxHeight: 150,
                          overflow: 'auto',
                          margin: 0
                        }}>
                          {JSON.stringify(selectedTemplateDetail.hyperparameters, null, 2)}
                        </pre>
                      ),
                    },
                    {
                      key: 'training_config',
                      label: '训练配置',
                      children: (
                        <pre style={{ 
                          background: '#f5f5f5', 
                          padding: 8, 
                          borderRadius: 4, 
                          fontSize: 12,
                          maxHeight: 150,
                          overflow: 'auto',
                          margin: 0
                        }}>
                          {JSON.stringify(selectedTemplateDetail.training_config, null, 2)}
                        </pre>
                      ),
                    },
                  ]}
                />
              </Card>
            )}
          </div>
        )

      case 6:
        // 使用 getFieldsValue(true) 获取所有字段值，包括未渲染的
        const formValues = form.getFieldsValue(true)
        const normalizationValue = formValues.normalization
        const normalizationLabel = NORMALIZATION_OPTIONS.find((o) => o.value === normalizationValue)?.label || normalizationValue || '未设置'
        const targetTypeLabel = TARGET_TYPE_OPTIONS.find((o) => o.value === formValues.target_type)?.label || formValues.target_type || '未设置'
        const selectedTemplateName = selectedTemplateId 
          ? modelTemplates.find(t => t.id === selectedTemplateId)?.name 
          : null
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
                <Text strong>归一化：</Text> {normalizationLabel}
              </Paragraph>
              <Paragraph>
                <Text strong>异常注入：</Text>{' '}
                {formValues.anomaly_enabled ? (
                  <>
                    {ANOMALY_TYPE_OPTIONS.find((o) => o.value === formValues.anomaly_type)?.label || formValues.anomaly_type} /{' '}
                    {INJECTION_ALGORITHM_OPTIONS.find((o) => o.value === formValues.injection_algorithm)?.label || formValues.injection_algorithm} /{' '}
                    {SEQUENCE_LOGIC_OPTIONS.find((o) => o.value === formValues.sequence_logic)?.label || formValues.sequence_logic}
                  </>
                ) : (
                  '未启用'
                )}
              </Paragraph>
              <Paragraph>
                <Text strong>窗口参数：</Text> 窗口大小 {formValues.window_size || 100}，步长 {formValues.stride || 1}
              </Paragraph>
              <Paragraph>
                <Text strong>目标类型：</Text> {targetTypeLabel}
                {formValues.target_type === 'kstep' && ` (K=${formValues.target_k || 1})`}
              </Paragraph>
              <Paragraph>
                <Text strong>模型模板：</Text>{' '}
                {selectedTemplateName ? (
                  <Tag color="blue" icon={<RocketOutlined />}>{selectedTemplateName}</Tag>
                ) : (
                  <Text type="secondary">未选择</Text>
                )}
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
              配置向导
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
            current: configPage,
            pageSize: configPageSize,
            total: configTotal,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 个配置`,
            pageSizeOptions: ['10', '20', '50'],
            onChange: (page, size) => {
              setConfigPage(page)
              setConfigPageSize(size)
            },
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

        <Form form={form} layout="vertical" style={{ minHeight: 300 }} preserve={true}>
          {renderStepContent()}
        </Form>

        <Divider />

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button onClick={handleWizardClose} disabled={submitting}>
            取消
          </Button>
          <Space>
            {currentStep > 0 && (
              <Button onClick={handlePrev} disabled={submitting || stepLoading}>
                上一步
              </Button>
            )}
            {currentStep < STEPS.length - 1 && (
              <Button type="primary" onClick={handleNext} loading={stepLoading} disabled={stepLoading}>
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

