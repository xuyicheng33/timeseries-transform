/**
 * 报告生成组件
 * 用于生成实验报告（Markdown/HTML/LaTeX）
 */
import React, { useState } from 'react'
import {
  Modal,
  Form,
  Select,
  Switch,
  Input,
  Button,
  Space,
  message,
  Divider,
  Typography,
  Tooltip,
} from 'antd'
import {
  FileTextOutlined,
  DownloadOutlined,
  CopyOutlined,
  FileMarkdownOutlined,
  Html5Outlined,
  CodeOutlined,
} from '@ant-design/icons'
import {
  generateExperimentReport,
  generateResultsReport,
  getLatexTable,
  downloadReport,
  getReportExtension,
} from '@/api/reports'
import type {
  ReportConfig,
  ReportFormat,
  ExperimentReportRequest,
  MultiResultReportRequest,
} from '@/types/report'
import { DEFAULT_REPORT_CONFIG, REPORT_FORMAT_OPTIONS } from '@/types/report'

const { Text } = Typography
const { Option } = Select

interface ReportGeneratorProps {
  visible: boolean
  onClose: () => void
  // 二选一：实验组 ID 或 结果 ID 列表
  experimentId?: number
  experimentName?: string
  resultIds?: number[]
  defaultTitle?: string
}

const ReportGenerator: React.FC<ReportGeneratorProps> = ({
  visible,
  onClose,
  experimentId,
  experimentName,
  resultIds,
  defaultTitle,
}) => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [latexCode, setLatexCode] = useState<string | null>(null)
  const [latexLoading, setLatexLoading] = useState(false)

  const isExperimentMode = !!experimentId

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      const config: ReportConfig = {
        include_summary: values.include_summary,
        include_metrics_table: values.include_metrics_table,
        include_best_model: values.include_best_model,
        include_dataset_info: values.include_dataset_info,
        include_conclusion: values.include_conclusion,
        custom_title: values.custom_title || undefined,
        custom_author: values.custom_author || undefined,
      }

      const format: ReportFormat = values.format
      let blob: Blob
      let filename: string

      if (isExperimentMode && experimentId) {
        const request: ExperimentReportRequest = {
          experiment_id: experimentId,
          config,
          format,
        }
        blob = await generateExperimentReport(request)
        filename = `report_${experimentName || experimentId}.${getReportExtension(format)}`
      } else if (resultIds && resultIds.length > 0) {
        const request: MultiResultReportRequest = {
          result_ids: resultIds,
          title: values.custom_title || defaultTitle || '时序预测实验报告',
          config,
          format,
        }
        blob = await generateResultsReport(request)
        filename = `comparison_report.${getReportExtension(format)}`
      } else {
        message.error('请提供实验组或结果列表')
        return
      }

      downloadReport(blob, filename)
      message.success('报告生成成功')
      onClose()
    } catch (error: any) {
      message.error(error?.message || '报告生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGetLatex = async () => {
    if (!experimentId) return

    setLatexLoading(true)
    try {
      const result = await getLatexTable(experimentId)
      setLatexCode(result.latex)
    } catch (error) {
      message.error('获取 LaTeX 代码失败')
    } finally {
      setLatexLoading(false)
    }
  }

  const handleCopyLatex = async () => {
    if (!latexCode) return
    try {
      await navigator.clipboard.writeText(latexCode)
      message.success('LaTeX 代码已复制到剪贴板')
    } catch {
      message.error('复制失败')
    }
  }

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'markdown':
        return <FileMarkdownOutlined />
      case 'html':
        return <Html5Outlined />
      case 'latex':
        return <CodeOutlined />
      default:
        return <FileTextOutlined />
    }
  }

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined />
          生成实验报告
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={600}
      footer={null}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          format: 'markdown',
          ...DEFAULT_REPORT_CONFIG,
          custom_title: isExperimentMode ? `实验报告: ${experimentName}` : defaultTitle,
        }}
      >
        {/* 报告格式 */}
        <Form.Item name="format" label="报告格式" rules={[{ required: true }]}>
          <Select>
            {REPORT_FORMAT_OPTIONS.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                <Space>
                  {getFormatIcon(opt.value)}
                  {opt.label}
                </Space>
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Divider style={{ textAlign: 'left' }} plain>
          报告内容
        </Divider>

        {/* 内容选项 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <Form.Item name="include_summary" valuePropName="checked" style={{ marginBottom: 8 }}>
            <Switch checkedChildren="汇总统计" unCheckedChildren="汇总统计" defaultChecked />
          </Form.Item>

          <Form.Item
            name="include_metrics_table"
            valuePropName="checked"
            style={{ marginBottom: 8 }}
          >
            <Switch checkedChildren="指标对比表" unCheckedChildren="指标对比表" defaultChecked />
          </Form.Item>

          <Form.Item name="include_best_model" valuePropName="checked" style={{ marginBottom: 8 }}>
            <Switch
              checkedChildren="最佳模型分析"
              unCheckedChildren="最佳模型分析"
              defaultChecked
            />
          </Form.Item>

          <Form.Item
            name="include_dataset_info"
            valuePropName="checked"
            style={{ marginBottom: 8 }}
          >
            <Switch checkedChildren="数据集信息" unCheckedChildren="数据集信息" defaultChecked />
          </Form.Item>

          {isExperimentMode && (
            <Form.Item
              name="include_conclusion"
              valuePropName="checked"
              style={{ marginBottom: 8 }}
            >
              <Switch checkedChildren="实验结论" unCheckedChildren="实验结论" defaultChecked />
            </Form.Item>
          )}
        </div>

        <Divider style={{ textAlign: 'left' }} plain>
          自定义信息
        </Divider>

        <Form.Item name="custom_title" label="报告标题">
          <Input placeholder="自定义报告标题（可选）" />
        </Form.Item>

        <Form.Item name="custom_author" label="作者">
          <Input placeholder="自定义作者名称（可选）" />
        </Form.Item>

        {/* LaTeX 快捷功能 */}
        {isExperimentMode && (
          <>
            <Divider style={{ textAlign: 'left' }} plain>
              LaTeX 快捷工具
            </Divider>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">快速获取可直接复制到论文的 LaTeX 表格代码</Text>
              <Space>
                <Button icon={<CodeOutlined />} onClick={handleGetLatex} loading={latexLoading}>
                  获取 LaTeX 表格
                </Button>
                {latexCode && (
                  <Tooltip title="复制到剪贴板">
                    <Button icon={<CopyOutlined />} onClick={handleCopyLatex}>
                      复制代码
                    </Button>
                  </Tooltip>
                )}
              </Space>
              {latexCode && (
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 12,
                    maxHeight: 200,
                    overflow: 'auto',
                    marginTop: 8,
                  }}
                >
                  {latexCode}
                </pre>
              )}
            </Space>
          </>
        )}

        <Divider />

        {/* 操作按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={onClose}>取消</Button>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleGenerate}
            loading={loading}
          >
            生成并下载
          </Button>
        </div>
      </Form>
    </Modal>
  )
}

export default ReportGenerator
