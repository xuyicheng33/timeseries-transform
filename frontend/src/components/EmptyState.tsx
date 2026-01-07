/**
 * 空状态组件
 * 统一的空数据展示组件，支持自定义图标、描述和操作按钮
 */

import { Empty, Button } from 'antd'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  image?: ReactNode
  description?: string
  actionText?: string
  onAction?: () => void
  children?: ReactNode
}

export default function EmptyState({
  image = Empty.PRESENTED_IMAGE_SIMPLE,
  description = '暂无数据',
  actionText,
  onAction,
  children,
}: EmptyStateProps) {
  return (
    <Empty image={image} description={description}>
      {actionText && onAction && (
        <Button type="primary" onClick={onAction}>
          {actionText}
        </Button>
      )}
      {children}
    </Empty>
  )
}

