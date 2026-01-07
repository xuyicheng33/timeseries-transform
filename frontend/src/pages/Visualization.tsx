/**
 * 可视化对比页面
 */

import { Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

export default function Visualization() {
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={2}>📈 可视化对比</Title>
        <Paragraph>
          多模型曲线对比和评估指标展示
        </Paragraph>
        <Paragraph type="secondary">
          开发中...
        </Paragraph>
      </Card>
    </div>
  )
}

