/**
 * 预测分解图表组件
 */
import React, { useEffect, useRef, useState } from 'react';
import { Card, Spin, Alert, Tag, Space, InputNumber } from 'antd';
import * as echarts from 'echarts';
import { decomposePrediction } from '@/api/advancedViz';
import type { PredictionDecompositionResponse } from '@/types/advancedViz';
import { DECOMPOSITION_COLORS } from '@/types/advancedViz';

interface PredictionDecompositionChartProps {
  resultId: number;
  resultName?: string;
}

const COMPONENT_LABELS: Record<string, string> = {
  trend: '趋势',
  seasonal: '季节性',
  residual: '残差',
  predicted: '预测值',
  true: '真实值',
};

const PredictionDecompositionChart: React.FC<PredictionDecompositionChartProps> = ({
  resultId,
  resultName,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<PredictionDecompositionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [customPeriod, setCustomPeriod] = useState<number | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await decomposePrediction({
        result_id: resultId,
        period: customPeriod || undefined,
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
  }, [resultId, customPeriod]);

  useEffect(() => {
    if (!chartRef.current || !data || data.components.length === 0) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // 构建图例和系列
    const legendData: string[] = [];
    const series: echarts.SeriesOption[] = [];
    
    // 获取索引（使用第一个组件的索引）
    const indices = data.components[0]?.indices || [];

    // 按顺序添加组件
    const componentOrder = ['predicted', 'true', 'trend', 'seasonal', 'residual'];
    
    for (const name of componentOrder) {
      const component = data.components.find(c => c.name === name);
      if (!component) continue;

      const label = COMPONENT_LABELS[name] || name;
      const color = DECOMPOSITION_COLORS[name as keyof typeof DECOMPOSITION_COLORS] || '#999';
      
      legendData.push(label);
      
      series.push({
        name: label,
        type: 'line',
        data: component.values,
        smooth: name !== 'residual',
        lineStyle: {
          color,
          width: name === 'predicted' || name === 'true' ? 2 : 1.5,
          type: name === 'residual' ? 'dashed' : 'solid',
        },
        itemStyle: { color },
        symbol: 'none',
        // 默认隐藏残差
        emphasis: { focus: 'series' },
      });
    }

    const option: echarts.EChartsOption = {
      title: {
        text: '预测分解分析',
        subtext: data.detected_period 
          ? `检测到周期: ${data.detected_period}` 
          : '未检测到明显周期',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: {
        data: legendData,
        top: 50,
        selected: {
          '残差': false, // 默认隐藏残差
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: 100,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: indices,
        name: '索引',
        axisLabel: {
          formatter: (value: string) => {
            const num = parseInt(value);
            return num >= 1000 ? `${(num / 1000).toFixed(1)}k` : value;
          },
        },
      },
      yAxis: {
        type: 'value',
        name: '值',
        scale: true,
      },
      dataZoom: [
        {
          type: 'slider',
          show: true,
          xAxisIndex: 0,
          start: 0,
          end: 100,
        },
        {
          type: 'inside',
          xAxisIndex: 0,
        },
      ],
      series,
    };

    chartInstance.current.setOption(option, true);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data]);

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
    };
  }, []);

  return (
    <Card
      title={resultName ? `${resultName} - 预测分解` : '预测分解分析'}
      extra={
        <Space>
          <span>自定义周期:</span>
          <InputNumber
            value={customPeriod}
            onChange={(v) => setCustomPeriod(v)}
            min={2}
            max={1000}
            placeholder="自动检测"
            style={{ width: 120 }}
          />
        </Space>
      }
    >
      {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
      
      <Spin spinning={loading}>
        {data && (
          <>
            <Space style={{ marginBottom: 16 }}>
              {data.detected_period && (
                <Tag color="blue">检测周期: {data.detected_period}</Tag>
              )}
              <Tag color="purple">趋势</Tag>
              <Tag color="green">季节性</Tag>
              <Tag color="orange">残差</Tag>
            </Space>
            
            <div style={{ marginBottom: 8, color: '#888' }}>
              分解公式: 预测值 = 趋势 + 季节性 + 残差
            </div>
            
            <div ref={chartRef} style={{ width: '100%', height: 450 }} />
          </>
        )}
      </Spin>
    </Card>
  );
};

export default PredictionDecompositionChart;

