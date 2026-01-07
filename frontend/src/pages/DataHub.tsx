/**
 * 数据中心页面
 */

import { Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

export default function DataHub() {
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={2}>📊 数据中心</Title>
        <Paragraph>
          数据集的上传、预览、下载和管理功能
        </Paragraph>
        <Paragraph type="secondary">
          开发中...
        </Paragraph>
      </Card>
    </div>
  )
}

