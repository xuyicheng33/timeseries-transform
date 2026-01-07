/**
 * 配置向导页面
 */

import { Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

export default function ConfigWizard() {
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={2}>⚙️ 配置向导</Title>
        <Paragraph>
          分步创建实验配置，生成标准文件名
        </Paragraph>
        <Paragraph type="secondary">
          开发中...
        </Paragraph>
      </Card>
    </div>
  )
}

