/**
 * 结果仓库页面
 */

import { Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

export default function ResultRepo() {
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={2}>📁 结果仓库</Title>
        <Paragraph>
          预测结果的上传、查看和管理功能
        </Paragraph>
        <Paragraph type="secondary">
          开发中...
        </Paragraph>
      </Card>
    </div>
  )
}

