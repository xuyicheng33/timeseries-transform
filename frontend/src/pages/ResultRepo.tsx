/**
 * 结果仓库页面
 * 功能：预测结果的上传、查看和管理
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Upload,
  Progress,
  Statistic,
  Row,
  Col,
  Tooltip,
  Popconfirm,
  Typography,
  Tag,
  Empty,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile, UploadProps } from 'antd/es/upload'
import {
  UploadOutlined,
  DownloadOutlined,
  EditOutlined,
  DeleteOutlined,
  InboxOutlined,
  ExperimentOutlined,
  EyeOutlined,
  QuestionCircleOutlined,
  BarChartOutlined,
} from '@ant-design/icons'

import type { Dataset, Configuration, Result, ResultUpdate, Metrics } from '@/types'
import {
  getResults,
  getModelNames,
  uploadResult,
  updateResult,
  deleteResult,
  getResultDownloadPath,
  previewResult,
} from '@/api/results'
import { download } from '@/utils/download'
import { formatFileSize, formatDateTime, formatMetric, hasMetrics } from '@/utils/format'
import { APP_CONFIG } from '@/config/app'
import { METRIC_NAMES, METRIC_DESCRIPTIONS } from '@/constants'

const { Title, Text } = Typography
const { TextArea } = Input
const { Dragger } = Upload

export default function ResultRepo() {
  // ============ 状态定义 ============
  const [results, setResults] = useState<Result[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  // 数据集和配置列表（用于筛选和关联）
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [configurations, setConfigurations] = useState<Configuration[]>([])
  const [modelNames, setModelNames] = useState<string[]>([])

  // 筛选条件
  const [filterDatasetId, setFilterDatasetId] = useState<number | undefined>()
  const [filterModelName, setFilterModelName] = useState<string | undefined>()

  // 上传相关
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadForm] = Form.useForm()
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  // 编辑相关
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editForm] = Form.useForm()
  const [editingResult, setEditingResult] = useState<Result | null>(null)
  const [editLoading, setEditLoading] = useState(false)

  // 指标详情
  const [metricsModalOpen, setMetricsModalOpen] = useState(false)
  const [selectedResult, setSelectedResult] = useState<Result | null>(null)

  // 预览相关
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewData, setPreviewData] = useState<{ columns: string[]; data: Record<string, unknown>[]; total_rows: number } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewResult, setPreviewResult] = useState<Result | null>(null)

  // ============ 数据获取 ============
  const fetchResults = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getResults(filterDatasetId, filterModelName, currentPage, pageSize)
      setResults(response.items)
      setTotal(response.total)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setLoading(false)
    }
  }, [filterDatasetId, filterModelName, currentPage, pageSize])

  const fetchDatasets = useCallback(async () => {
    try {
      const { getAllDatasets } = await import('@/api/datasets')
      const data = await getAllDatasets()
      setDatasets(data)
    } catch {
      // 错误已在 API 层处理
    }
  }, [])

  const fetchConfigurations = useCallback(async () => {
    try {
      const { getAllConfigurations } = await import('@/api/configurations')
      const data = await getAllConfigurations()
      setConfigurations(data)
    } catch {
      // 错误已在 API 层处理
    }
  }, [])

  const fetchModelNames = useCallback(async () => {
    try {
      const names = await getModelNames(filterDatasetId)
      setModelNames(names)
    } catch {
      // 错误已在 API 层处理
    }
  }, [filterDatasetId])

  useEffect(() => {
    fetchResults()
  }, [fetchResults])

  useEffect(() => {
    fetchDatasets()
    fetchConfigurations()
  }, [fetchDatasets, fetchConfigurations])

  useEffect(() => {
    fetchModelNames()
  }, [fetchModelNames])

  // ============ 上传功能 ============
  const handleUploadModalOpen = () => {
    setUploadModalOpen(true)
    setUploadFile(null)
    setUploadProgress(0)
    uploadForm.resetFields()
  }

  const handleUploadModalClose = () => {
    setUploadModalOpen(false)
    setUploadFile(null)
    setUploadProgress(0)
    uploadForm.resetFields()
  }

  const uploadProps: UploadProps = {
    accept: APP_CONFIG.UPLOAD.ALLOWED_TYPES.join(','),
    maxCount: 1,
    beforeUpload: (file) => {
      if (file.size > APP_CONFIG.UPLOAD.MAX_SIZE) {
        message.error(`文件大小不能超过 ${formatFileSize(APP_CONFIG.UPLOAD.MAX_SIZE)}`)
        return Upload.LIST_IGNORE
      }
      const isCSV = file.name.toLowerCase().endsWith('.csv')
      if (!isCSV) {
        message.error('只支持 CSV 文件')
        return Upload.LIST_IGNORE
      }
      // 保存原始 File 对象
      setUploadFile(file)
      // 自动填充名称
      const nameWithoutExt = file.name.replace(/\.csv$/i, '')
      uploadForm.setFieldValue('name', nameWithoutExt)
      return false
    },
    onRemove: () => {
      setUploadFile(null)
      uploadForm.setFieldValue('name', '')
    },
    fileList: uploadFile ? [{ uid: '-1', name: uploadFile.name, status: 'done' } as UploadFile] : [],
  }

  const handleUpload = async () => {
    try {
      const values = await uploadForm.validateFields()
      if (!uploadFile) {
        message.error('请选择文件')
        return
      }

      setUploading(true)
      setUploadProgress(0)

      await uploadResult(
        values.name,
        values.dataset_id,
        values.model_name,
        uploadFile,
        values.configuration_id,
        values.model_version,
        values.description,
        (percent) => setUploadProgress(percent),
        values.target_column  // 新增：目标列参数
      )

      message.success('上传成功')
      setUploading(false)
      handleUploadModalClose()
      fetchResults()
    } catch {
      // 错误已在 API 层处理
      setUploading(false)
    }
  }

  // ============ 下载功能 ============
  const handleDownload = async (result: Result) => {
    try {
      const path = getResultDownloadPath(result.id)
      await download(path, result.filename)
    } catch {
      // 错误已在 download 函数中处理
    }
  }

  // ============ 编辑功能 ============
  const handleEditModalOpen = (result: Result) => {
    setEditingResult(result)
    setEditModalOpen(true)
    editForm.setFieldsValue({
      name: result.name,
      model_name: result.model_name,
      model_version: result.model_version,
      description: result.description,
    })
  }

  const handleEditModalClose = () => {
    setEditModalOpen(false)
    setEditingResult(null)
    editForm.resetFields()
  }

  const handleEdit = async () => {
    if (!editingResult) return

    try {
      const values = await editForm.validateFields()
      setEditLoading(true)

      const updateData: ResultUpdate = {}
      if (values.name !== editingResult.name) updateData.name = values.name
      if (values.model_name !== editingResult.model_name) updateData.model_name = values.model_name
      if (values.model_version !== editingResult.model_version) updateData.model_version = values.model_version
      if (values.description !== editingResult.description) updateData.description = values.description

      if (Object.keys(updateData).length === 0) {
        message.info('没有修改')
        setEditLoading(false)
        handleEditModalClose()
        return
      }

      await updateResult(editingResult.id, updateData)
      message.success('更新成功')
      setEditLoading(false)
      handleEditModalClose()
      fetchResults()
    } catch {
      // 错误已在 API 层处理
      setEditLoading(false)
    }
  }

  // ============ 删除功能 ============
  const handleDelete = async (result: Result) => {
    try {
      await deleteResult(result.id)
      message.success('删除成功')
      fetchResults()
    } catch {
      // 错误已在 API 层处理
    }
  }

  // ============ 指标详情 ============
  const handleShowMetrics = (result: Result) => {
    setSelectedResult(result)
    setMetricsModalOpen(true)
  }

  const handleMetricsModalClose = () => {
    setMetricsModalOpen(false)
    setSelectedResult(null)
  }

  // ============ 预览功能 ============
  const handlePreview = async (result: Result) => {
    setPreviewResult(result)
    setPreviewModalOpen(true)
    setPreviewLoading(true)
    setPreviewData(null)

    try {
      const data = await previewResult(result.id, 100)
      setPreviewData(data)
    } catch {
      // 错误已在 API 层处理
    } finally {
      setPreviewLoading(false)
    }
  }

  const handlePreviewModalClose = () => {
    setPreviewModalOpen(false)
    setPreviewData(null)
    setPreviewResult(null)
  }

  // 动态生成预览表格列
  const getPreviewColumns = () => {
    if (!previewData?.columns) return []
    return previewData.columns.map((col) => ({
      title: col,
      dataIndex: col,
      key: col,
      width: 150,
      ellipsis: true,
      render: (value: unknown) => {
        if (value === null || value === undefined) return <Text type="secondary">-</Text>
        if (typeof value === 'number') return value.toFixed(6)
        return String(value)
      },
    }))
  }

  // 渲染指标卡片
  const renderMetricsCards = (metrics: Metrics) => {
    const metricKeys: (keyof Metrics)[] = ['mse', 'rmse', 'mae', 'r2', 'mape']
    return (
      <Row gutter={[16, 16]}>
        {metricKeys.map((key) => (
          <Col span={8} key={key}>
            <Card size="small">
              <Statistic
                title={
                  <Tooltip title={METRIC_DESCRIPTIONS[key]}>
                    <span style={{ cursor: 'help' }}>{METRIC_NAMES[key]}</span>
                  </Tooltip>
                }
                value={formatMetric(metrics[key], key)}
                valueStyle={{
                  color: key === 'r2' && metrics[key] > 0.9 ? '#3f8600' : undefined,
                  fontSize: 20,
                }}
              />
            </Card>
          </Col>
        ))}
      </Row>
    )
  }

  // ============ 表格列定义 ============
  const columns: ColumnsType<Result> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      ellipsis: true,
      render: (name: string, record: Result) => (
        <Space>
          <ExperimentOutlined style={{ color: '#722ed1' }} />
          <a onClick={() => handleShowMetrics(record)} style={{ fontWeight: 500 }}>{name}</a>
        </Space>
      ),
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
      title: '模型',
      key: 'model',
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color="blue">{record.model_name}</Tag>
          {record.model_version && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              v{record.model_version}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '行数',
      dataIndex: 'row_count',
      key: 'row_count',
      width: 100,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '指标',
      key: 'metrics',
      width: 200,
      render: (_, record) => {
        if (!hasMetrics(record.metrics)) {
          return <Text type="secondary">-</Text>
        }
        const metrics = record.metrics as Metrics
        return (
          <Space size={4} wrap>
            <Tooltip title={`MSE: ${formatMetric(metrics.mse, 'mse')}`}>
              <Tag>MSE: {formatMetric(metrics.mse, 'mse')}</Tag>
            </Tooltip>
            <Tooltip title={`R²: ${formatMetric(metrics.r2, 'r2')}`}>
              <Tag color={metrics.r2 > 0.9 ? 'green' : metrics.r2 > 0.7 ? 'blue' : 'default'}>
                R²: {formatMetric(metrics.r2, 'r2')}
              </Tag>
            </Tooltip>
            <Button type="link" size="small" onClick={() => handleShowMetrics(record)}>
              详情
            </Button>
          </Space>
        )
      },
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
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="指标详情">
            <Button
              type="text"
              size="small"
              icon={<BarChartOutlined />}
              onClick={() => handleShowMetrics(record)}
            />
          </Tooltip>
          <Tooltip title="预览数据">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handlePreview(record)}
            />
          </Tooltip>
          <Tooltip title="下载">
            <Button
              type="text"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditModalOpen(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description={`确定要删除结果「${record.name}」吗？`}
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
              结果仓库
            </Title>
            <Text type="secondary">管理预测结果，查看评估指标</Text>
          </div>
          <Button type="primary" icon={<UploadOutlined />} onClick={handleUploadModalOpen}>
            上传结果
          </Button>
        </div>
      </Card>

      {/* 筛选条件 */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Text>筛选：</Text>
          <Select
            placeholder="选择数据集"
            allowClear
            style={{ width: 200 }}
            value={filterDatasetId}
            onChange={(value) => {
              setFilterDatasetId(value)
              setCurrentPage(1)  // 重置页码
            }}
          >
            {datasets.map((dataset) => (
              <Select.Option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </Select.Option>
            ))}
          </Select>
          <Select
            placeholder="选择模型"
            allowClear
            style={{ width: 150 }}
            value={filterModelName}
            onChange={(value) => {
              setFilterModelName(value)
              setCurrentPage(1)  // 重置页码
            }}
          >
            {modelNames.map((name) => (
              <Select.Option key={name} value={name}>
                {name}
              </Select.Option>
            ))}
          </Select>
        </Space>
      </Card>

      {/* 结果列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={results}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 个结果`,
            pageSizeOptions: ['10', '20', '50'],
            onChange: (page, size) => {
              setCurrentPage(page)
              setPageSize(size)
            },
          }}
          locale={{
            emptyText: (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无结果">
                <Button type="primary" onClick={handleUploadModalOpen}>
                  上传第一个结果
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      {/* 上传 Modal */}
      <Modal
        title="上传预测结果"
        open={uploadModalOpen}
        onCancel={handleUploadModalClose}
        onOk={handleUpload}
        okText="上传"
        cancelText="取消"
        confirmLoading={uploading}
        maskClosable={!uploading}
        closable={!uploading}
        width={650}
      >
        <Form form={uploadForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="选择文件" required>
            <Dragger {...uploadProps} disabled={uploading}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持 CSV 格式，文件需包含以下列之一：
              </p>
              <p className="ant-upload-hint" style={{ fontSize: 12, color: '#666' }}>
                格式1: true_value + predicted_value 列（完整格式，可直接计算指标）
              </p>
              <p className="ant-upload-hint" style={{ fontSize: 12, color: '#666' }}>
                格式2: 仅 predicted_value 列（需选择目标列，系统自动从数据集获取真实值）
              </p>
            </Dragger>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="结果名称"
                rules={[
                  { required: true, message: '请输入结果名称' },
                  { max: 255, message: '名称不能超过255个字符' },
                ]}
              >
                <Input placeholder="请输入结果名称" disabled={uploading} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dataset_id"
                label="关联数据集"
                rules={[{ required: true, message: '请选择数据集' }]}
              >
                <Select
                  placeholder="请选择数据集"
                  disabled={uploading}
                  onChange={() => {
                    // 数据集变化时清空已选配置和目标列
                    uploadForm.setFieldValue('configuration_id', undefined)
                    uploadForm.setFieldValue('target_column', undefined)
                  }}
                >
                  {datasets.map((dataset) => (
                    <Select.Option key={dataset.id} value={dataset.id}>
                      {dataset.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="model_name"
                label="模型名称"
                rules={[
                  { required: true, message: '请输入模型名称' },
                  { max: 100, message: '模型名称不能超过100个字符' },
                ]}
              >
                <Input placeholder="如：Transformer, LSTM, TCN" disabled={uploading} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="model_version" label="模型版本">
                <Input placeholder="如：1.0.0（可选）" disabled={uploading} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.dataset_id !== curr.dataset_id}
          >
            {({ getFieldValue }) => {
              const selectedDatasetId = getFieldValue('dataset_id')
              const filteredConfigs = selectedDatasetId
                ? configurations.filter((c) => c.dataset_id === selectedDatasetId)
                : []
              return (
                <Form.Item name="configuration_id" label="关联配置">
                  <Select
                    placeholder={selectedDatasetId ? '请选择配置（可选）' : '请先选择数据集'}
                    allowClear
                    disabled={uploading || !selectedDatasetId}
                  >
                    {filteredConfigs.map((config) => (
                      <Select.Option key={config.id} value={config.id}>
                        {config.name}
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              )
            }}
          </Form.Item>

          {/* 目标列选择（用于只上传预测值的情况） */}
          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.dataset_id !== curr.dataset_id}
          >
            {({ getFieldValue }) => {
              const selectedDatasetId = getFieldValue('dataset_id')
              const selectedDataset = datasets.find((d) => d.id === selectedDatasetId)
              const columns = selectedDataset?.columns || []
              
              return (
                <Form.Item
                  name="target_column"
                  label={
                    <Space>
                      <span>目标列</span>
                      <Tooltip title="如果上传的文件只包含 predicted_value 列（没有 true_value），请选择数据集中对应的真实值列，系统会自动进行匹配比较">
                        <QuestionCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    </Space>
                  }
                >
                  <Select
                    placeholder={selectedDatasetId ? '仅预测值文件需要选择（可选）' : '请先选择数据集'}
                    allowClear
                    disabled={uploading || !selectedDatasetId}
                    showSearch
                    optionFilterProp="children"
                  >
                    {columns.map((col: string) => (
                      <Select.Option key={col} value={col}>
                        {col}
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              )
            }}
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
            rules={[{ max: 1000, message: '描述不能超过1000个字符' }]}
          >
            <TextArea placeholder="请输入描述（可选）" rows={2} disabled={uploading} />
          </Form.Item>

          {uploading && (
            <Form.Item label="上传进度">
              <Progress percent={uploadProgress} status="active" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 编辑 Modal */}
      <Modal
        title="编辑结果"
        open={editModalOpen}
        onCancel={handleEditModalClose}
        onOk={handleEdit}
        okText="保存"
        cancelText="取消"
        confirmLoading={editLoading}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="结果名称"
            rules={[
              { required: true, message: '请输入结果名称' },
              { max: 255, message: '名称不能超过255个字符' },
            ]}
          >
            <Input placeholder="请输入结果名称" disabled={editLoading} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="model_name"
                label="模型名称"
                rules={[
                  { required: true, message: '请输入模型名称' },
                  { max: 100, message: '模型名称不能超过100个字符' },
                ]}
              >
                <Input placeholder="模型名称" disabled={editLoading} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="model_version" label="模型版本">
                <Input placeholder="模型版本（可选）" disabled={editLoading} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
            rules={[{ max: 1000, message: '描述不能超过1000个字符' }]}
          >
            <TextArea placeholder="请输入描述（可选）" rows={2} disabled={editLoading} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 指标详情 Modal */}
      <Modal
        title={`指标详情：${selectedResult?.name || ''}`}
        open={metricsModalOpen}
        onCancel={handleMetricsModalClose}
        footer={[
          <Button key="close" onClick={handleMetricsModalClose}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedResult && hasMetrics(selectedResult.metrics) && (
          renderMetricsCards(selectedResult.metrics as Metrics)
        )}
      </Modal>

      {/* 预览 Modal */}
      <Modal
        title={`预览数据：${previewResult?.name || ''}`}
        open={previewModalOpen}
        onCancel={handlePreviewModalClose}
        footer={[
          <Button key="close" onClick={handlePreviewModalClose}>
            关闭
          </Button>,
          <Button
            key="download"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => previewResult && handleDownload(previewResult)}
          >
            下载
          </Button>,
        ]}
        width={800}
      >
        {previewResult && (
          <div style={{ marginBottom: 16 }}>
            <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
              <span><Text strong>模型：</Text>{previewResult.model_name}</span>
              {previewResult.model_version && (
                <span><Text strong>版本：</Text>{previewResult.model_version}</span>
              )}
              <span><Text strong>总行数：</Text>{previewResult.row_count?.toLocaleString()}</span>
            </Space>
          </div>
        )}

        {previewLoading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Text type="secondary">加载中...</Text>
          </div>
        ) : previewData ? (
          <>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              预览前 100 行数据（共 {previewData.total_rows.toLocaleString()} 行）
            </Text>
            <Table
              columns={getPreviewColumns()}
              dataSource={previewData.data}
              rowKey={(_, index) => String(index)}
              scroll={{ x: 'max-content', y: 400 }}
              pagination={false}
              size="small"
              bordered
            />
          </>
        ) : (
          <Empty description="暂无数据" />
        )}
      </Modal>
    </div>
  )
}

