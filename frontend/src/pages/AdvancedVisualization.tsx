/**
 * 高级可视化面板
 * 整合特征重要性、置信区间、预测分解等高级分析功能
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Space,
  Tabs,
  Empty,
  message,
  Row,
  Col,
  Typography,
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  DotChartOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { getResults } from '@/api/results';
import type { Result } from '@/types';
import ConfidenceIntervalChart from '@/components/ConfidenceIntervalChart';
import FeatureImportanceChart from '@/components/FeatureImportanceChart';
import PredictionDecompositionChart from '@/components/PredictionDecompositionChart';

const { Title, Text } = Typography;
const { Option } = Select;

const AdvancedVisualization: React.FC = () => {
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedResultId, setSelectedResultId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState('confidence');

  // 加载结果列表
  useEffect(() => {
    const loadResults = async () => {
      setLoading(true);
      try {
        const response = await getResults(undefined, undefined, 1, 100);
        setResults(response.items);
        // 默认选择第一个结果
        if (response.items.length > 0 && !selectedResultId) {
          setSelectedResultId(response.items[0].id);
        }
      } catch (error) {
        message.error('加载结果列表失败');
      } finally {
        setLoading(false);
      }
    };
    loadResults();
  }, []);

  const selectedResult = results.find(r => r.id === selectedResultId);

  const tabItems = [
    {
      key: 'confidence',
      label: (
        <span>
          <LineChartOutlined />
          置信区间
        </span>
      ),
      children: selectedResultId ? (
        <ConfidenceIntervalChart
          resultId={selectedResultId}
          resultName={selectedResult?.name}
        />
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
      children: selectedResultId ? (
        <FeatureImportanceChart
          resultId={selectedResultId}
          resultName={selectedResult?.name}
        />
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
      children: selectedResultId ? (
        <PredictionDecompositionChart
          resultId={selectedResultId}
          resultName={selectedResult?.name}
        />
      ) : (
        <Empty description="请选择一个预测结果" />
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Row align="middle" justify="space-between" style={{ marginBottom: 24 }}>
          <Col>
            <Space>
              <ExperimentOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <div>
                <Title level={4} style={{ margin: 0 }}>高级可视化分析</Title>
                <Text type="secondary">深入分析预测结果的置信度、特征影响和时序分解</Text>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <span>选择预测结果:</span>
              <Select
                value={selectedResultId}
                onChange={setSelectedResultId}
                style={{ width: 300 }}
                placeholder="选择一个预测结果"
                loading={loading}
                showSearch
                optionFilterProp="children"
              >
                {results.map(r => (
                  <Option key={r.id} value={r.id}>
                    {r.name} ({r.model_name})
                  </Option>
                ))}
              </Select>
            </Space>
          </Col>
        </Row>

        {selectedResult && (
          <div style={{ marginBottom: 16, padding: '12px 16px', background: '#f5f5f5', borderRadius: 4 }}>
            <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
              <span><strong>模型:</strong> {selectedResult.model_name}</span>
              {selectedResult.model_version && (
                <span><strong>版本:</strong> {selectedResult.model_version}</span>
              )}
              <span><strong>数据行数:</strong> {selectedResult.row_count?.toLocaleString()}</span>
              {selectedResult.metrics?.r2 !== undefined && (
                <span><strong>R²:</strong> {selectedResult.metrics.r2.toFixed(4)}</span>
              )}
              {selectedResult.metrics?.rmse !== undefined && (
                <span><strong>RMSE:</strong> {selectedResult.metrics.rmse.toFixed(6)}</span>
              )}
            </Space>
          </div>
        )}

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
        />
      </Card>
    </div>
  );
};

export default AdvancedVisualization;

