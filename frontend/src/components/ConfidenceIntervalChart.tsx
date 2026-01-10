/**
 * 置信区间图表组件
 */
import React, { useEffect, useRef, useState } from 'react';
import { Card, Select, Spin, Statistic, Row, Col, Alert, Space } from 'antd';
import * as echarts from 'echarts';
import { calculateConfidenceInterval } from '@/api/advancedViz';
import type { ConfidenceIntervalResponse } from '@/types/advancedViz';
import { CONFIDENCE_LEVELS } from '@/types/advancedViz';

interface ConfidenceIntervalChartProps {
  resultId: number;
  resultName?: string;
}

const ConfidenceIntervalChart: React.FC<ConfidenceIntervalChartProps> = ({
  resultId,
  resultName,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ConfidenceIntervalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confidenceLevel, setConfidenceLevel] = useState(0.95);
  const [windowSize, setWindowSize] = useState(50);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await calculateConfidenceInterval({
        result_id: resultId,
        confidence_level: confidenceLevel,
        window_size: windowSize,
        max_points: 2000,
      });
      setData(response);
    } catch (err: any) {
      setError(err?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [resultId, confidenceLevel, windowSize]);

  useEffect(() => {
    if (!chartRef.current || !data) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const indices = data.data.map(d => d.index);
    const predicted = data.data.map(d => d.predicted);
    const trueValues = data.data.map(d => d.true_value);
    const lowerBounds = data.data.map(d => d.lower_bound);
    const upperBounds = data.data.map(d => d.upper_bound);

    // 置信区间带数据
    const bandData = data.data.map(d => [d.lower_bound, d.upper_bound]);

    const option: echarts.EChartsOption = {
      title: {
        text: `预测置信区间 (${(data.confidence_level * 100).toFixed(0)}%)`,
        subtext: data.downsampled ? `已降采样至 ${data.data.length} 点` : undefined,
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          const idx = params[0]?.dataIndex;
          if (idx === undefined) return '';
          const d = data.data[idx];
          return `
            <div style="padding: 8px;">
              <div><strong>索引: ${d.index}</strong></div>
              <div>预测值: ${d.predicted.toFixed(4)}</div>
              <div>真实值: ${d.true_value?.toFixed(4) || '-'}</div>
              <div>置信区间: [${d.lower_bound.toFixed(4)}, ${d.upper_bound.toFixed(4)}]</div>
              <div>区间宽度: ${(d.upper_bound - d.lower_bound).toFixed(4)}</div>
            </div>
          `;
        },
      },
      legend: {
        data: ['预测值', '真实值', '置信区间'],
        top: 30,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
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
      series: [
        // 置信区间带（使用堆叠面积图）
        {
          name: '下界',
          type: 'line',
          data: lowerBounds,
          lineStyle: { opacity: 0 },
          areaStyle: { opacity: 0 },
          stack: 'confidence',
          symbol: 'none',
        },
        {
          name: '置信区间',
          type: 'line',
          data: bandData.map(d => d[1] - d[0]),
          lineStyle: { opacity: 0 },
          areaStyle: {
            color: 'rgba(24, 144, 255, 0.2)',
          },
          stack: 'confidence',
          symbol: 'none',
        },
        // 预测值
        {
          name: '预测值',
          type: 'line',
          data: predicted,
          smooth: true,
          lineStyle: { color: '#722ed1', width: 2 },
          itemStyle: { color: '#722ed1' },
          symbol: 'none',
        },
        // 真实值
        {
          name: '真实值',
          type: 'line',
          data: trueValues,
          smooth: true,
          lineStyle: { color: '#52c41a', width: 1.5 },
          itemStyle: { color: '#52c41a' },
          symbol: 'none',
        },
      ],
    };

    chartInstance.current.setOption(option);

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
      title={resultName ? `${resultName} - 置信区间分析` : '置信区间分析'}
      extra={
        <Space>
          <span>置信水平:</span>
          <Select
            value={confidenceLevel}
            onChange={setConfidenceLevel}
            style={{ width: 100 }}
            options={CONFIDENCE_LEVELS.map(l => ({ value: l.value, label: l.label }))}
          />
          <span>窗口大小:</span>
          <Select
            value={windowSize}
            onChange={setWindowSize}
            style={{ width: 100 }}
            options={[
              { value: 20, label: '20' },
              { value: 50, label: '50' },
              { value: 100, label: '100' },
              { value: 200, label: '200' },
            ]}
          />
        </Space>
      }
    >
      {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
      
      <Spin spinning={loading}>
        {data && (
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Statistic
                title="覆盖率"
                value={data.coverage_rate * 100}
                precision={2}
                suffix="%"
                valueStyle={{
                  color: data.coverage_rate >= confidenceLevel * 0.9 ? '#52c41a' : '#faad14',
                }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="平均区间宽度"
                value={data.avg_interval_width}
                precision={4}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="数据点数"
                value={data.total_points}
                suffix={data.downsampled ? ' (已降采样)' : ''}
              />
            </Col>
          </Row>
        )}
        <div ref={chartRef} style={{ width: '100%', height: 400 }} />
      </Spin>
    </Card>
  );
};

export default ConfidenceIntervalChart;

