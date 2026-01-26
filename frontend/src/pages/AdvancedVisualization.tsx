/**
 * 高级可视化面板
 * 整合特征重要性、置信区间、预测分解等高级分析功能
 * 支持多选结果进行对比分析
 */
import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, Select, Space, Tabs, Empty, message, Row, Col, Typography, Tag, Button } from 'antd'
import {
  LineChartOutlined,
  BarChartOutlined,
  DotChartOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import { getResults } from '@/api/results'
import type { Result } from '@/types'
import ConfidenceIntervalChart from '@/components/ConfidenceIntervalChart'
import FeatureImportanceChart from '@/components/FeatureImportanceChart'
import PredictionDecompositionChart from '@/components/PredictionDecompositionChart'

const { Title, Text } = Typography
const { Option } = Select

const AdvancedVisualization: React.FC = () => {
  const [searchParams] = useSearchParams()
  const [results, setResults] = useState<Result[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedResultIds, setSelectedResultIds] = useState<number[]>([])
  const [activeTab, setActiveTab] = useState('confidence')

  // 加载结果列表
  useEffect(() => {
    const loadResults = async () => {
      setLoading(true)
      try {
        const response = await getResults(undefined, undefined, 1, 100)
        setResults(response.items)

        // 处理 URL 参数 ?ids=1,2,3
        const idsParam = searchParams.get('ids')
        if (idsParam) {
          const ids = idsParam
            .split(',')
            .map((id) => parseInt(id.trim(), 10))
            .filter((id) => !isNaN(id) && id > 0)

          // 验证 ids 是否存在
          const validIds = ids.filter((id) => response.items.some((r) => r.id === id))
          if (validIds.length > 0) {
            setSelectedResultIds(validIds)
          } else if (response.items.length > 0) {
            // URL 参数无效，默认选择第一个
            setSelectedResultIds([response.items[0].id])
          }
        } else if (response.items.length > 0) {
          // 没有 URL 参数，默认选择第一个结果
          setSelectedResultIds([response.items[0].id])
        }
      } catch (error) {
        message.error('加载结果列表失败')
      } finally {
        setLoading(false)
      }
    }
    loadResults()
  }, [searchParams])

  // 获取选中的结果对象列表
  const selectedResults = results.filter((r) => selectedResultIds.includes(r.id))

  // 当前主要选中的结果（用于单结果分析组件）
  const primaryResult = selectedResults[0]

  // 跳转到可视化对比页面
  const handleGoToComparison = () => {
    if (selectedResultIds.length > 0) {
      window.open(`/visualization?ids=${selectedResultIds.join(',')}`, '_blank')
    }
  }

  const tabItems = [
    {
      key: 'confidence',
      label: (
        <span>
          <LineChartOutlined />
          置信区间
        </span>
      ),
      children: primaryResult ? (
        <ConfidenceIntervalChart resultId={primaryResult.id} resultName={primaryResult.name} />
      ) : (
        <Empty description="请选择一个预测结果" />
      ),
    },
    {
      key: 'feature',
      label: (
        <span>
          <BarChartOutlined />
          特征重要性
        </span>
      ),
      children: primaryResult ? (
        <FeatureImportanceChart resultId={primaryResult.id} resultName={primaryResult.name} />
      ) : (
        <Empty description="请选择一个预测结果" />
      ),
    },
    {
      key: 'decomposition',
      label: (
        <span>
          <DotChartOutlined />
          预测分解
        </span>
      ),
      children: primaryResult ? (
        <PredictionDecompositionChart resultId={primaryResult.id} resultName={primaryResult.name} />
      ) : (
        <Empty description="请选择一个预测结果" />
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Row align="middle" justify="space-between" style={{ marginBottom: 24 }}>
          <Col>
            <Space>
              <ExperimentOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <div>
                <Title level={4} style={{ margin: 0 }}>
                  高级可视化分析
                </Title>
                <Text type="secondary">深入分析预测结果的置信度、特征影响和时序分解</Text>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <span>选择预测结果:</span>
              <Select
                mode="multiple"
                value={selectedResultIds}
                onChange={(values) => {
                  if (values.length === 0) {
                    message.warning('请至少选择一个结果')
                    return
                  }
                  setSelectedResultIds(values)
                }}
                style={{ minWidth: 300, maxWidth: 500 }}
                placeholder="选择预测结果（支持多选）"
                loading={loading}
                showSearch
                optionFilterProp="children"
                maxTagCount={3}
              >
                {results.map((r) => (
                  <Option key={r.id} value={r.id}>
                    {r.name} ({r.model_name})
                  </Option>
                ))}
              </Select>
              {selectedResultIds.length > 1 && (
                <Button type="primary" onClick={handleGoToComparison}>
                  对比分析
                </Button>
              )}
            </Space>
          </Col>
        </Row>

        {/* 显示选中的结果信息 */}
        {selectedResults.length > 0 && (
          <div
            style={{
              marginBottom: 16,
              padding: '12px 16px',
              background: '#f5f5f5',
              borderRadius: 4,
            }}
          >
            <Space wrap>
              <Text strong>已选择 {selectedResults.length} 个结果：</Text>
              {selectedResults.map((result) => (
                <Tag
                  key={result.id}
                  color="blue"
                  closable
                  onClose={() => {
                    if (selectedResultIds.length > 1) {
                      setSelectedResultIds(selectedResultIds.filter((id) => id !== result.id))
                    } else {
                      message.warning('请至少保留一个结果')
                    }
                  }}
                >
                  {result.name} ({result.model_name})
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {/* 主要结果详情 */}
        {primaryResult && (
          <div
            style={{
              marginBottom: 16,
              padding: '12px 16px',
              background: '#e6f7ff',
              borderRadius: 4,
            }}
          >
            <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
              <span>
                <strong>当前分析:</strong> {primaryResult.name}
              </span>
              <span>
                <strong>模型:</strong> {primaryResult.model_name}
              </span>
              {primaryResult.model_version && (
                <span>
                  <strong>版本:</strong> {primaryResult.model_version}
                </span>
              )}
              <span>
                <strong>数据行数:</strong> {primaryResult.row_count?.toLocaleString()}
              </span>
              {primaryResult.metrics?.r2 !== undefined && (
                <span>
                  <strong>R²:</strong> {primaryResult.metrics.r2.toFixed(4)}
                </span>
              )}
              {primaryResult.metrics?.rmse !== undefined && (
                <span>
                  <strong>RMSE:</strong> {primaryResult.metrics.rmse.toFixed(6)}
                </span>
              )}
            </Space>
            {selectedResults.length > 1 && (
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">
                  提示：高级分析当前显示第一个选中结果的详情。如需对比多个结果，请点击"对比分析"按钮。
                </Text>
              </div>
            )}
          </div>
        )}

        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} size="large" />
      </Card>
    </div>
  )
}

export default AdvancedVisualization
