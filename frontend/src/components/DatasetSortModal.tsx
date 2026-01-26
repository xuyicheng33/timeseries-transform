/**
 * 数据集排序弹窗组件
 * 支持拖拽排序数据集顺序
 */

import React, { useState, useEffect } from 'react'
import { Modal, List, message, Typography, Space, Tag, Empty, Spin } from 'antd'
import { HolderOutlined, FileTextOutlined } from '@ant-design/icons'
import type { Dataset } from '@/types'
import { getAllDatasets, updateDatasetSortOrder } from '@/api/datasets'

const { Text } = Typography

interface DatasetSortModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function DatasetSortModal({ open, onClose, onSuccess }: DatasetSortModalProps) {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  // 加载数据集列表
  useEffect(() => {
    if (open) {
      loadDatasets()
    }
  }, [open])

  const loadDatasets = async () => {
    setLoading(true)
    try {
      const data = await getAllDatasets()
      setDatasets(data)
      setHasChanges(false)
    } catch {
      message.error('加载数据集列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 拖拽开始
  const handleDragStart = (index: number) => {
    setDraggedIndex(index)
  }

  // 拖拽结束
  const handleDragEnd = () => {
    setDraggedIndex(null)
  }

  // 拖拽经过
  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (draggedIndex === null || draggedIndex === index) return

    const newDatasets = [...datasets]
    const draggedItem = newDatasets[draggedIndex]
    newDatasets.splice(draggedIndex, 1)
    newDatasets.splice(index, 0, draggedItem)

    setDatasets(newDatasets)
    setDraggedIndex(index)
    setHasChanges(true)
  }

  // 保存排序
  const handleSave = async () => {
    if (!hasChanges) {
      onClose()
      return
    }

    setSaving(true)
    try {
      const orders = datasets.map((dataset, index) => ({
        id: dataset.id,
        sort_order: index,
      }))

      await updateDatasetSortOrder({ orders })
      message.success('排序保存成功')
      onSuccess()
      onClose()
    } catch {
      message.error('保存排序失败')
    } finally {
      setSaving(false)
    }
  }

  // 关闭弹窗
  const handleClose = () => {
    if (saving) return
    if (hasChanges) {
      Modal.confirm({
        title: '确认关闭',
        content: '您有未保存的排序更改，确定要关闭吗？',
        okText: '确定',
        cancelText: '取消',
        onOk: onClose,
      })
    } else {
      onClose()
    }
  }

  return (
    <Modal
      title="数据集排序"
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
        <Text type="secondary">拖拽数据集调整显示顺序，排在前面的数据集将优先显示。</Text>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : datasets.length === 0 ? (
        <Empty description="暂无数据集" />
      ) : (
        <List
          dataSource={datasets}
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
                <FileTextOutlined style={{ color: '#1890ff' }} />
                <Text strong style={{ flex: 1 }}>
                  {item.name}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {item.row_count.toLocaleString()} 行 · {item.column_count} 列
                </Text>
              </Space>
            </List.Item>
          )}
          style={{
            maxHeight: 400,
            overflow: 'auto',
          }}
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
