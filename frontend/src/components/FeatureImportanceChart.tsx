/**
 * 特征重要性图表组件
 */
import React, { useEffect, useRef, useState } from 'react';
import { Card, Select, Spin, Alert, Space, Tag, Empty } from 'antd';
import * as echarts from 'echarts';
import { analyzeFeatureImportance } from '@/api/advancedViz';
import type { FeatureImportanceResponse, FeatureImportanceMethod } from '@/types/advancedViz';
import { FEATURE_IMPORTANCE_METHODS } from '@/types/advancedViz';

interface FeatureImportanceChartProps {
  resultId: number;
  resultName?: string;
}

const FeatureImportanceChart: React.FC<FeatureImportanceChartProps> = ({
  resultId,
  resultName,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<FeatureImportanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [method, setMethod] = useState<FeatureImportanceMethod>('correlation');
  const [topK, setTopK] = useState(10);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await analyzeFeatureImportance({
        result_id: resultId,
        method,
        top_k: topK,
      });
      setData(response);
    } catch (err: any) {
      setError(err?.message || '加载失败');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [resultId, method, topK]);

  useEffect(() => {
    if (!chartRef.current || !data || data.features.length === 0) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const features = data.features.slice().reverse(); // 反转以便最重要的在上面
    const names = features.map(f => f.feature_name);
    const values = features.map(f => f.importance);

    // 生成渐变色
    const maxValue = Math.max(...values);
    const colors = values.map(v => {
      const ratio = v / maxValue;
      const r = Math.round(24 + (255 - 24) * (1 - ratio));
      const g = Math.round(144 + (100 - 144) * (1 - ratio));
      const b = Math.round(255 + (100 - 255) * (1 - ratio));
      return `rgb(${r}, ${g}, ${b})`;
    });

    const option: echarts.EChartsOption = {
      title: {
        text: '特征重要性分析',
        subtext: `方法: ${FEATURE_IMPORTANCE_METHODS.find(m => m.value === method)?.label || method}`,
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const p = params[0];
          const feature = features[p.dataIndex];
          return `
            <div style="padding: 8px;">
              <div><strong>${feature.feature_name}</strong></div>
              <div>重要性: ${feature.importance.toFixed(6)}</div>
              <div>排名: #${feature.rank}</div>
            </div>
          `;
        },
      },
      grid: {
        left: '3%',
        right: '10%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: '重要性',
        max: 1,
        axisLabel: {
          formatter: (value: number) => value.toFixed(2),
        },
      },
      yAxis: {
        type: 'category',
        data: names,
        axisLabel: {
          width: 120,
          overflow: 'truncate',
          ellipsis: '...',
        },
      },
      series: [
        {
          name: '重要性',
          type: 'bar',
          data: values.map((v, i) => ({
            value: v,
            itemStyle: { color: colors[i] },
          })),
          label: {
            show: true,
            position: 'right',
            formatter: (params: any) => params.value.toFixed(4),
          },
          barMaxWidth: 30,
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data, method]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
    };
  }, []);

  const methodInfo = FEATURE_IMPORTANCE_METHODS.find(m => m.value === method);

  return (
    <Card
      title={resultName ? `${resultName} - 特征重要性` : '特征重要性分析'}
      extra={
        <Space>
          <span>分析方法:</span>
          <Select
            value={method}
            onChange={setMethod}
            style={{ width: 140 }}
            options={FEATURE_IMPORTANCE_METHODS.map(m => ({
              value: m.value,
              label: m.label,
            }))}
          />
          <span>显示数量:</span>
          <Select
            value={topK}
            onChange={setTopK}
            style={{ width: 80 }}
            options={[
              { value: 5, label: '5' },
              { value: 10, label: '10' },
              { value: 15, label: '15' },
              { value: 20, label: '20' },
            ]}
          />
        </Space>
      }
    >
      {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
      
      {methodInfo && (
        <div style={{ marginBottom: 16 }}>
          <Tag color="blue">{methodInfo.label}</Tag>
          <span style={{ color: '#888', marginLeft: 8 }}>{methodInfo.description}</span>
        </div>
      )}
      
      <Spin spinning={loading}>
        {data && data.features.length > 0 ? (
          <>
            <div style={{ marginBottom: 8, color: '#888' }}>
              共 {data.total_features} 个特征，显示前 {data.features.length} 个
            </div>
            <div ref={chartRef} style={{ width: '100%', height: Math.max(300, topK * 35) }} />
          </>
        ) : !loading && !error ? (
          <Empty description="无特征数据，请确保结果文件包含特征列" />
        ) : null}
      </Spin>
    </Card>
  );
};

export default FeatureImportanceChart;

