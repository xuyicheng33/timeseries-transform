import React, { useEffect, useState } from 'react'
import { Modal, List, message, Typography, Space, Tag, Empty, Spin } from 'antd'
import { HolderOutlined, FolderOutlined } from '@ant-design/icons'
import type { Folder } from '@/types'
import { getFolders, reorderFolders } from '@/api/folders'

const { Text } = Typography

interface FolderSortModalProps {
  open: boolean
  parentId: number | null
  onClose: () => void
  onSuccess: () => void
}

export default function FolderSortModal({
  open,
  parentId,
  onClose,
  onSuccess,
}: FolderSortModalProps) {
  const [folders, setFolders] = useState<Folder[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    if (open) {
      loadFolders()
    }
  }, [open, parentId])

  const loadFolders = async () => {
    setLoading(true)
    try {
      const data = await getFolders('manual', 'asc')
      setFolders(data.items.filter((folder) => folder.parent_id === parentId))
      setHasChanges(false)
    } catch {
      message.error('加载文件夹列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDragStart = (index: number) => {
    setDraggedIndex(index)
  }

  const handleDragEnd = () => {
    setDraggedIndex(null)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (draggedIndex === null || draggedIndex === index) return

    const next = [...folders]
    const draggedItem = next[draggedIndex]
    next.splice(draggedIndex, 1)
    next.splice(index, 0, draggedItem)

    setFolders(next)
    setDraggedIndex(index)
    setHasChanges(true)
  }

  const handleSave = async () => {
    if (!hasChanges) {
      onClose()
      return
    }

    setSaving(true)
    try {
      const orders = folders.map((folder, index) => ({ id: folder.id, sort_order: index }))
      await reorderFolders({ orders })
      message.success('排序保存成功')
      onSuccess()
      onClose()
    } catch {
      message.error('保存排序失败')
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    if (saving) return
    if (hasChanges) {
      Modal.confirm({
        title: '确认关闭',
        content: '您有未保存的排序更改，确认关闭吗？',
        okText: '确认',
        cancelText: '取消',
        onOk: onClose,
      })
    } else {
      onClose()
    }
  }

  return (
    <Modal
      title="文件夹排序"
      open={open}
      onCancel={handleClose}
      onOk={handleSave}
      okText="保存排序"
      cancelText="取消"
      confirmLoading={saving}
      width={600}
      maskClosable={!saving && !hasChanges}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">拖拽文件夹调整显示顺序，排序仅在“手动排序”模式下生效。</Text>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : folders.length === 0 ? (
        <Empty description="暂无文件夹" />
      ) : (
        <List
          dataSource={folders}
          renderItem={(item, index) => (
            <List.Item
              key={item.id}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragEnd={handleDragEnd}
              onDragOver={(e) => handleDragOver(e, index)}
              style={{
                cursor: 'grab',
                background: draggedIndex === index ? '#e6f7ff' : '#fff',
                borderRadius: 4,
                marginBottom: 4,
                padding: '8px 12px',
                border: '1px solid #f0f0f0',
                transition: 'background 0.2s',
              }}
            >
              <Space style={{ width: '100%' }}>
                <HolderOutlined style={{ color: '#999', cursor: 'grab' }} />
                <Tag color="blue">{index + 1}</Tag>
                <FolderOutlined style={{ color: '#1890ff' }} />
                <Text strong style={{ flex: 1 }}>
                  {item.name}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {item.dataset_count.toLocaleString()} 个数据集
                </Text>
              </Space>
            </List.Item>
          )}
          style={{ maxHeight: 400, overflow: 'auto' }}
        />
      )}

      {hasChanges && (
        <div style={{ marginTop: 12 }}>
          <Tag color="orange">有未保存的更改</Tag>
        </div>
      )}
    </Modal>
  )
}

