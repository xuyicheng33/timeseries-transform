/**
 * 数据中心页面
 * 功能：数据集的上传、预览、下载、管理和数据质量检测
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Badge,
  Breadcrumb,
  Col,
  Card,
  List,
  Table,
  Button,
  Dropdown,
  Radio,
  Row,
  Select,
  Space,
  Modal,
  Form,
  Input,
  Tree,
  Upload,
  Progress,
  Tag,
  Tooltip,
  Popconfirm,
  message,
  Typography,
  Descriptions,
  Empty,
  Drawer,
  Spin,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { DataNode } from 'antd/es/tree'
import type { UploadFile, UploadProps } from 'antd/es/upload'
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  ExportOutlined,
  InboxOutlined,
  InfoCircleOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  LineChartOutlined,
  ImportOutlined,
  MoreOutlined,
  PlusOutlined,
  SortAscendingOutlined,
  UploadOutlined,
} from '@ant-design/icons'

import type {
  CleaningResult,
  DataQualityReport,
  Dataset,
  DatasetPreview,
  DatasetUpdate,
  Folder,
  OutlierMethod,
} from '@/types'
import {
  batchMoveDatasets,
  getDatasets,
  uploadDataset,
  previewDataset as fetchPreviewDataset,
  updateDataset,
  deleteDataset,
  getDatasetDownloadPath,
} from '@/api/datasets'
import { createFolder, deleteFolder, getFolders, updateFolder as updateFolderApi } from '@/api/folders'
import { getQualityReport } from '@/api/quality'
import { batchDeleteDatasets, exportData, previewImport, importData } from '@/api/batch'
import { download } from '@/utils/download'
import { formatFileSize, formatDateTime } from '@/utils/format'
import { APP_CONFIG } from '@/config/app'
import DataQualityReportComponent from '@/components/DataQualityReport'
import DataCleaningModal from '@/components/DataCleaningModal'
import DataExploration from '@/components/DataExploration'
import DatasetSortModal from '@/components/DatasetSortModal'
import FolderSortModal from '@/components/FolderSortModal'
import { useAuth } from '@/contexts/AuthContext'

const { Title, Text } = Typography
const { TextArea } = Input
const { Dragger } = Upload

// 列名展示的最大数量
const MAX_VISIBLE_COLUMNS = 5

type FolderSortValue = 'manual' | 'name_asc' | 'name_desc' | 'time_desc' | 'time_asc'

function resolveFolderSort(
  value: FolderSortValue
): { sortBy: 'manual' | 'name' | 'time'; order: 'asc' | 'desc' } {
  switch (value) {
    case 'name_asc':
      return { sortBy: 'name', order: 'asc' }
    case 'name_desc':
      return { sortBy: 'name', order: 'desc' }
    case 'time_asc':
      return { sortBy: 'time', order: 'asc' }
    case 'time_desc':
      return { sortBy: 'time', order: 'desc' }
    default:
      return { sortBy: 'manual', order: 'asc' }
  }
}

export default function DataHub() {
  // ============ 认证状态 ============
  const { user } = useAuth()
  const isAdmin = user?.is_admin ?? false

  // ============ 状态定义 ============
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const [folders, setFolders] = useState<Folder[]>([])
  const [foldersLoading, setFoldersLoading] = useState(false)
  const [rootDatasetCount, setRootDatasetCount] = useState(0)
  const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null)
  const [folderSort, setFolderSort] = useState<FolderSortValue>('manual')
  const [folderSortModalOpen, setFolderSortModalOpen] = useState(false)
  const [folderTreeExpandedKeys, setFolderTreeExpandedKeys] = useState<React.Key[]>(['root'])

  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [folderForm] = Form.useForm()
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null)
  const [folderSaving, setFolderSaving] = useState(false)

  const [folderInfoModalOpen, setFolderInfoModalOpen] = useState(false)
  const [folderInfoFolder, setFolderInfoFolder] = useState<Folder | null>(null)

  const [deleteFolderModalOpen, setDeleteFolderModalOpen] = useState(false)
  const [deletingFolder, setDeletingFolder] = useState<Folder | null>(null)
  const [deleteFolderAction, setDeleteFolderAction] = useState<'move_to_root' | 'cascade'>(
    'move_to_root'
  )
  const [deleteFolderConfirmName, setDeleteFolderConfirmName] = useState('')
  const [folderDeleting, setFolderDeleting] = useState(false)

  const [batchMoving, setBatchMoving] = useState(false)

  // 上传相关
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadForm] = Form.useForm()
  const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([])
  const [uploadNameByUid, setUploadNameByUid] = useState<Record<string, string>>({})
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadingIndex, setUploadingIndex] = useState(0)
  const [uploadingTotal, setUploadingTotal] = useState(0)

  // 预览相关
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewData, setPreviewData] = useState<DatasetPreview | null>(null)
  const [previewDataset, setPreviewDatasetInfo] = useState<Dataset | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // 编辑相关
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editForm] = Form.useForm()
  const [editingDataset, setEditingDataset] = useState<Dataset | null>(null)
  const [editLoading, setEditLoading] = useState(false)

  // 数据质量相关
  const [qualityDrawerOpen, setQualityDrawerOpen] = useState(false)
  const [qualityDataset, setQualityDataset] = useState<Dataset | null>(null)
  const [qualityReport, setQualityReport] = useState<DataQualityReport | null>(null)
  const [qualityLoading, setQualityLoading] = useState(false)
  const [cleaningModalOpen, setCleaningModalOpen] = useState(false)

  // 数据探索相关
  const [explorationDrawerOpen, setExplorationDrawerOpen] = useState(false)
  const [explorationDataset, setExplorationDataset] = useState<Dataset | null>(null)

  // 批量操作相关
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [batchDeleting, setBatchDeleting] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importPreview, setImportPreview] = useState<{
    datasets_count: number
    configurations_count: number
    results_count: number
  } | null>(null)
  const [importing, setImporting] = useState(false)

  // 排序相关
  const [sortModalOpen, setSortModalOpen] = useState(false)

  // ============ 数据获取 ============
  const fetchFolders = useCallback(async () => {
    setFoldersLoading(true)
    try {
      const { sortBy, order } = resolveFolderSort(folderSort)
      const response = await getFolders(sortBy, order)
      setFolders(response.items)
      setRootDatasetCount(response.root_dataset_count)
    } catch {
      // Error is handled by the API layer
    } finally {
      setFoldersLoading(false)
    }
  }, [folderSort])

  const fetchDatasets = useCallback(async () => {
    setLoading(true)
    try {
      const options =
        selectedFolderId === null
          ? { rootOnly: true }
          : { folderId: selectedFolderId }
      const response = await getDatasets(currentPage, pageSize, options)
      setDatasets(response.items)
      setTotal(response.total)
    } catch {
      // Error is handled by the API layer
    } finally {
      setLoading(false)
    }
  }, [currentPage, pageSize, selectedFolderId])

  useEffect(() => {
    fetchFolders()
  }, [fetchFolders])

  useEffect(() => {
    fetchDatasets()
  }, [fetchDatasets])

  const foldersById = useMemo(() => new Map(folders.map((folder) => [folder.id, folder])), [folders])

  useEffect(() => {
    if (selectedFolderId !== null && !foldersById.has(selectedFolderId)) {
      setSelectedFolderId(null)
      setCurrentPage(1)
      setSelectedRowKeys([])
    }
  }, [foldersById, selectedFolderId])

  const selectedTreeKey = selectedFolderId === null ? 'root' : `folder-${selectedFolderId}`

  const handleSelectFolder = (folderId: number | null) => {
    setSelectedFolderId(folderId)
    setCurrentPage(1)
    setSelectedRowKeys([])
  }

  const handleTreeSelect = (keys: React.Key[]) => {
    const key = String(keys[0] ?? 'root')
    if (key === 'root') {
      handleSelectFolder(null)
      return
    }
    if (key.startsWith('folder-')) {
      const id = Number(key.slice('folder-'.length))
      if (!Number.isNaN(id)) {
        handleSelectFolder(id)
      }
    }
  }

  const currentFolder = selectedFolderId === null ? null : (foldersById.get(selectedFolderId) ?? null)

  const folderPath = useMemo(() => {
    if (!currentFolder) return []

    const path: Folder[] = []
    const visited = new Set<number>()
    let cursor: Folder | undefined | null = currentFolder

    while (cursor && !visited.has(cursor.id)) {
      path.unshift(cursor)
      visited.add(cursor.id)
      if (cursor.parent_id === null) break
      cursor = foldersById.get(cursor.parent_id)
    }

    return path
  }, [currentFolder, foldersById])

  const childFolders = useMemo(() => {
    const parentId = selectedFolderId === null ? null : selectedFolderId
    return folders.filter((folder) => folder.parent_id === parentId)
  }, [folders, selectedFolderId])

  const folderTreeData: DataNode[] = useMemo(() => {
    const childrenByParent = new Map<number | null, Folder[]>()
    for (const folder of folders) {
      const items = childrenByParent.get(folder.parent_id) ?? []
      items.push(folder)
      childrenByParent.set(folder.parent_id, items)
    }

    const renderFolderTitle = (folder: Folder) => (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          width: '100%',
        }}
      >
        {folder.description ? (
          <Tooltip title={folder.description}>
            <span
              style={{
                flex: 1,
                minWidth: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {folder.name}
            </span>
          </Tooltip>
        ) : (
          <span
            style={{
              flex: 1,
              minWidth: 0,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {folder.name}
          </span>
        )}
        <Badge count={folder.dataset_count} size="small" />
      </div>
    )

    const buildNodes = (parentId: number | null): DataNode[] => {
      const items = childrenByParent.get(parentId) ?? []
      return items.map((folder) => {
        const children = buildNodes(folder.id)
        return {
          key: `folder-${folder.id}`,
          title: renderFolderTitle(folder),
          children: children.length > 0 ? children : undefined,
        }
      })
    }

    return [
      {
        key: 'root',
        title: (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              width: '100%',
            }}
          >
            <span style={{ flex: 1, minWidth: 0 }}>根目录</span>
            <Badge count={rootDatasetCount} size="small" />
          </div>
        ),
        children: buildNodes(null),
      },
    ]
  }, [folders, rootDatasetCount])

  const folderSelectOptions = useMemo(
    () => {
      const buildFolderLabel = (folder: Folder): string => {
        const parts: string[] = [folder.name]
        const visited = new Set<number>([folder.id])
        let cursor: Folder | undefined | null = folder

        while (cursor && cursor.parent_id !== null) {
          const parent = foldersById.get(cursor.parent_id)
          if (!parent || visited.has(parent.id)) break
          parts.unshift(parent.name)
          visited.add(parent.id)
          cursor = parent
        }

        return parts.join(' / ')
      }

      return [
        { label: '根目录', value: 'root' as const },
        ...folders.map((folder) => ({ label: buildFolderLabel(folder), value: folder.id })),
      ]
    },
    [folders, foldersById]
  )

  useEffect(() => {
    const nextKeys = new Set<React.Key>(['root'])
    if (selectedFolderId !== null) {
      nextKeys.add(`folder-${selectedFolderId}`)
    }

    const visited = new Set<number>()
    let cursor: Folder | undefined | null = currentFolder
    while (cursor && cursor.parent_id !== null && !visited.has(cursor.id)) {
      nextKeys.add(`folder-${cursor.parent_id}`)
      visited.add(cursor.id)
      cursor = foldersById.get(cursor.parent_id)
    }

    setFolderTreeExpandedKeys((prev) => Array.from(new Set([...prev, ...Array.from(nextKeys)])))
  }, [currentFolder, foldersById, selectedFolderId])

  const handleOpenCreateFolder = () => {
    if (currentFolder && currentFolder.parent_id !== null) {
      message.error('当前版本仅支持两级文件夹')
      return
    }

    setEditingFolder(null)
    setFolderModalOpen(true)
    folderForm.resetFields()
  }

  const handleOpenFolderInfo = (folder: Folder) => {
    setFolderInfoFolder(folder)
    setFolderInfoModalOpen(true)
  }

  const handleCloseFolderInfo = () => {
    setFolderInfoModalOpen(false)
    setFolderInfoFolder(null)
  }

  const handleOpenRenameFolder = (folder: Folder) => {
    setEditingFolder(folder)
    setFolderModalOpen(true)
    folderForm.setFieldsValue({ name: folder.name, description: folder.description })
  }

  const handleCloseFolderModal = () => {
    setFolderModalOpen(false)
    setEditingFolder(null)
    folderForm.resetFields()
  }

  const handleSaveFolder = async () => {
    try {
      const values = await folderForm.validateFields()

      let parentId: number | null = null
      if (!editingFolder && selectedFolderId !== null) {
        const selected = foldersById.get(selectedFolderId)
        if (!selected || selected.parent_id !== null) {
          message.error('当前版本仅支持两级文件夹')
          return
        }
        parentId = selectedFolderId
      }

      setFolderSaving(true)

      if (editingFolder) {
        await updateFolderApi(editingFolder.id, {
          name: values.name,
          description: values.description || '',
        })
        message.success('保存成功')
      } else {
        await createFolder({
          name: values.name,
          description: values.description || '',
          parent_id: parentId,
        })
        message.success('创建成功')
      }

      handleCloseFolderModal()
      fetchFolders()
    } catch {
      // Error is handled by the API layer
    } finally {
      setFolderSaving(false)
    }
  }

  const handleOpenDeleteFolder = (folder: Folder) => {
    const children = folders.filter((item) => item.parent_id === folder.id)
    const totalDatasets =
      folder.dataset_count + children.reduce((sum, item) => sum + item.dataset_count, 0)

    if (totalDatasets === 0) {
      Modal.confirm({
        title: '删除文件夹',
        content:
          children.length > 0
            ? `确认删除文件夹「${folder.name}」吗？该文件夹包含 ${children.length} 个子文件夹，将一并删除。`
            : `确认删除文件夹「${folder.name}」吗？`,
        okText: '删除',
        cancelText: '取消',
        okButtonProps: { danger: true },
        onOk: async () => {
          await deleteFolder(folder.id, { action: 'move_to_root' })
          message.success('删除成功')
          const isInSubtree =
            selectedFolderId !== null &&
            (selectedFolderId === folder.id ||
              foldersById.get(selectedFolderId)?.parent_id === folder.id)
          if (isInSubtree) {
            handleSelectFolder(null)
          }
          fetchFolders()
          fetchDatasets()
        },
      })
      return
    }

    setDeletingFolder(folder)
    setDeleteFolderAction('move_to_root')
    setDeleteFolderConfirmName('')
    setDeleteFolderModalOpen(true)
  }

  const handleCloseDeleteFolderModal = () => {
    setDeleteFolderModalOpen(false)
    setDeletingFolder(null)
    setDeleteFolderAction('move_to_root')
    setDeleteFolderConfirmName('')
  }

  const handleConfirmDeleteFolder = async () => {
    if (!deletingFolder) return

    setFolderDeleting(true)
    try {
      const isInSubtree =
        selectedFolderId !== null &&
        (selectedFolderId === deletingFolder.id ||
          foldersById.get(selectedFolderId)?.parent_id === deletingFolder.id)
      const params =
        deleteFolderAction === 'cascade'
          ? { action: 'cascade' as const, confirm_name: deleteFolderConfirmName }
          : { action: 'move_to_root' as const }

      await deleteFolder(deletingFolder.id, params)
      message.success('删除成功')

      handleCloseDeleteFolderModal()
      if (isInSubtree) {
        handleSelectFolder(null)
      }
      fetchFolders()
      fetchDatasets()
    } catch {
      // Error is handled by the API layer
    } finally {
      setFolderDeleting(false)
    }
  }

  // ============ 上传功能 ============
  const handleUploadModalOpen = () => {
    setUploadModalOpen(true)
    setUploadFileList([])
    setUploadNameByUid({})
    setUploadProgress(0)
    setUploadingIndex(0)
    setUploadingTotal(0)
    uploadForm.resetFields()
    uploadForm.setFieldValue('folder_id', selectedFolderId === null ? 'root' : selectedFolderId)
  }

  const handleUploadModalClose = () => {
    setUploadModalOpen(false)
    setUploadFileList([])
    setUploadNameByUid({})
    setUploadProgress(0)
    setUploadingIndex(0)
    setUploadingTotal(0)
    uploadForm.resetFields()
  }

  const uploadProps: UploadProps = {
    accept: APP_CONFIG.UPLOAD.ALLOWED_TYPES.join(','),
    multiple: true,
    maxCount: 100,
    fileList: uploadFileList,
    beforeUpload: (file) => {
      if (uploadFileList.length >= 100) {
        message.error('单次最多上传 100 个文件')
        return Upload.LIST_IGNORE
      }

      if (file.size > APP_CONFIG.UPLOAD.MAX_SIZE) {
        message.error(`文件大小不能超过 ${formatFileSize(APP_CONFIG.UPLOAD.MAX_SIZE)}`)
        return Upload.LIST_IGNORE
      }

      const isCSV = file.name.toLowerCase().endsWith('.csv')
      if (!isCSV) {
        message.error('只支持 CSV 文件')
        return Upload.LIST_IGNORE
      }

      return false
    },
    onChange: (info) => {
      const nextList = info.fileList.slice(0, 100)
      if (info.fileList.length > 100) {
        message.warning('单次最多上传 100 个文件')
      }
      setUploadFileList(nextList)
      setUploadNameByUid((prev) => {
        const next: Record<string, string> = {}
        for (const item of nextList) {
          next[item.uid] = prev[item.uid] ?? item.name.replace(/\.csv$/i, '')
        }
        return next
      })
    },
    onRemove: (file) => {
      setUploadNameByUid((prev) => {
        const next = { ...prev }
        delete next[file.uid]
        return next
      })
      return true
    },
  }

  const handleUpload = async () => {
    try {
      const values = await uploadForm.validateFields()
      if (uploadFileList.length === 0) {
        message.error('请选择文件')
        return
      }

      const description = values.description || ''
      const folderValue = values.folder_id
      const folderId =
        folderValue === undefined || folderValue === null || folderValue === 'root'
          ? null
          : Number(folderValue)

      for (const item of uploadFileList) {
        const datasetName = (uploadNameByUid[item.uid] ?? item.name.replace(/\.csv$/i, '')).trim()
        if (!datasetName) {
          message.error(`数据集名称不能为空：${item.name}`)
          return
        }
        if (datasetName.length > 255) {
          message.error(`数据集名称不能超过 255 个字符：${item.name}`)
          return
        }
      }

      setUploading(true)
      setUploadProgress(0)
      setUploadingIndex(0)
      setUploadingTotal(uploadFileList.length)

      const failed: UploadFile[] = []
      const failedUids = new Set<string>()

      for (let index = 0; index < uploadFileList.length; index += 1) {
        const item = uploadFileList[index]
        const file = item.originFileObj as File | undefined
        if (!file) {
          failed.push(item)
          failedUids.add(item.uid)
          continue
        }

        const datasetName = (uploadNameByUid[item.uid] ?? item.name.replace(/\.csv$/i, '')).trim()
        setUploadingIndex(index + 1)

        try {
          await uploadDataset(datasetName, description, file, folderId, (percent) => {
            const overall = Math.round(((index + percent / 100) / uploadFileList.length) * 100)
            setUploadProgress(overall)
          })
        } catch {
          failed.push(item)
          failedUids.add(item.uid)
        }
      }

      const successCount = uploadFileList.length - failed.length
      if (successCount > 0) {
        fetchDatasets()
        fetchFolders()
      }

      if (failed.length === 0) {
        message.success('上传成功')
        handleUploadModalClose()
        return
      }

      message.warning(`上传完成：成功 ${successCount}，失败 ${failed.length}`)
      setUploadFileList(failed)
      setUploadNameByUid((prev) => {
        const next: Record<string, string> = {}
        for (const uid of failedUids) {
          if (prev[uid] !== undefined) {
            next[uid] = prev[uid]
          }
        }
        return next
      })
      setUploadProgress(0)
      setUploadingIndex(0)
      setUploadingTotal(failed.length)
    } catch {
      // Error is handled by the API layer
    } finally {
      setUploading(false)
    }
  }

  // ============ 预览功能 ============
  const handlePreview = async (dataset: Dataset) => {
    setPreviewModalOpen(true)
    setPreviewDatasetInfo(dataset)
    setPreviewLoading(true)
    setPreviewData(null)

    try {
      const data = await fetchPreviewDataset(dataset.id, APP_CONFIG.PREVIEW.DEFAULT_ROWS)
      setPreviewData(data)
    } catch {
      // Error is handled by the API layer
    } finally {
      setPreviewLoading(false)
    }
  }

  const handlePreviewModalClose = () => {
    setPreviewModalOpen(false)
    setPreviewData(null)
    setPreviewDatasetInfo(null)
  }

  // 动态生成预览表格列
  const getPreviewColumns = (): ColumnsType<Record<string, unknown>> => {
    if (!previewData?.columns) return []
    return previewData.columns.map((col) => ({
      title: col,
      dataIndex: col,
      key: col,
      width: 150,
      ellipsis: true,
      render: (value: unknown) => {
        if (value === null || value === undefined) return <Text type="secondary">-</Text>
        return String(value)
      },
    }))
  }

  // ============ 下载功能 ============
  const handleDownload = async (dataset: Dataset) => {
    try {
      const path = getDatasetDownloadPath(dataset.id)
      await download(path, dataset.filename)
    } catch {
      // 错误已在 download 函数中处理
    }
  }

  // ============ 编辑功能 ============
  const handleEditModalOpen = (dataset: Dataset) => {
    setEditingDataset(dataset)
    setEditModalOpen(true)
    editForm.setFieldsValue({
      name: dataset.name,
      description: dataset.description,
      folder_id: dataset.folder_id ?? 'root',
    })
  }

  const handleEditModalClose = () => {
    setEditModalOpen(false)
    setEditingDataset(null)
    editForm.resetFields()
  }

  const handleEdit = async () => {
    if (!editingDataset) return

    try {
      const values = await editForm.validateFields()
      setEditLoading(true)

      const updateData: DatasetUpdate = {}
      if (values.name !== editingDataset.name) {
        updateData.name = values.name
      }
      if (values.description !== editingDataset.description) {
        updateData.description = values.description
      }
      const folderValue = values.folder_id
      const nextFolderId =
        folderValue === undefined || folderValue === null || folderValue === 'root'
          ? null
          : (folderValue as number)
      const currentFolderId = (editingDataset.folder_id ?? null) as number | null
      if (nextFolderId !== currentFolderId) {
        updateData.folder_id = nextFolderId
      }

      if (Object.keys(updateData).length === 0) {
        message.info('没有修改')
        setEditLoading(false)
        handleEditModalClose()
        return
      }

      await updateDataset(editingDataset.id, updateData)
      message.success('更新成功')
      setEditLoading(false)
      handleEditModalClose()
      fetchDatasets()
      fetchFolders()
    } catch {
      // Error is handled by the API layer
      setEditLoading(false)
    }
  }

  // ============ 数据质量检测功能 ============
  const handleQualityCheck = async (dataset: Dataset, method: OutlierMethod = 'iqr') => {
    setQualityDataset(dataset)
    setQualityDrawerOpen(true)
    setQualityLoading(true)
    setQualityReport(null)

    try {
      const report = await getQualityReport(dataset.id, method)
      setQualityReport(report)
    } catch {
      message.error('获取质量报告失败')
    } finally {
      setQualityLoading(false)
    }
  }

  const handleQualityRefresh = async (method: OutlierMethod) => {
    if (!qualityDataset) return
    setQualityLoading(true)

    try {
      const report = await getQualityReport(qualityDataset.id, method)
      setQualityReport(report)
      message.success('质量报告已刷新')
    } catch {
      message.error('刷新失败')
    } finally {
      setQualityLoading(false)
    }
  }

  const handleQualityDrawerClose = () => {
    setQualityDrawerOpen(false)
    setQualityDataset(null)
    setQualityReport(null)
  }

  const handleOpenCleaning = () => {
    setCleaningModalOpen(true)
  }

  const handleCleaningSuccess = (result: CleaningResult) => {
    setCleaningModalOpen(false)
    // 刷新数据集列表
    fetchDatasets()
    fetchFolders()
    // 如果创建了新数据集，提示用户
    if (result.new_dataset_id) {
      message.success(`已创建新数据集: ${result.new_dataset_name}`)
    }
    // 刷新质量报告
    if (qualityDataset) {
      handleQualityCheck(qualityDataset)
    }
  }

  // ============ 数据探索功能 ============
  const handleExploration = (dataset: Dataset) => {
    setExplorationDataset(dataset)
    setExplorationDrawerOpen(true)
  }

  const handleExplorationDrawerClose = () => {
    setExplorationDrawerOpen(false)
    setExplorationDataset(null)
  }

  // ============ 批量操作功能 ============
  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的数据集')
      return
    }

    setBatchDeleting(true)
    try {
      const result = await batchDeleteDatasets(selectedRowKeys as number[])
      if (result.success_count > 0) {
        message.success(`成功删除 ${result.success_count} 个数据集`)
      }
      if (result.failed_count > 0) {
        message.warning(`${result.failed_count} 个数据集删除失败`)
      }
      setSelectedRowKeys([])
      fetchDatasets()
      fetchFolders()
    } catch {
      message.error('批量删除失败')
    } finally {
      setBatchDeleting(false)
    }
  }

  const handleBatchMove = async (target: 'root' | number) => {
    if (!isAdmin) return

    const datasetIds = selectedRowKeys
      .map((key) => Number(key))
      .filter((id) => !Number.isNaN(id))

    if (datasetIds.length === 0) {
      message.warning('请先选择要移动的数据集')
      return
    }

    setBatchMoving(true)
    try {
      await batchMoveDatasets(datasetIds, target === 'root' ? null : target)
      message.success('移动成功')
      setSelectedRowKeys([])
      fetchDatasets()
      fetchFolders()
    } catch {
      message.error('批量移动失败')
    } finally {
      setBatchMoving(false)
    }
  }

  const handleExport = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的数据集')
      return
    }

    setExporting(true)
    try {
      const blob = await exportData({
        dataset_ids: selectedRowKeys as number[],
        include_configs: true,
        include_results: true
      })
      
      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `timeseries_export_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      message.success('导出成功')
    } catch {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }

  const handleImportModalOpen = () => {
    setImportModalOpen(true)
    setImportFile(null)
    setImportPreview(null)
  }

  const handleImportModalClose = () => {
    setImportModalOpen(false)
    setImportFile(null)
    setImportPreview(null)
  }

  const handleImportFileChange = async (file: File) => {
    setImportFile(file)
    try {
      const preview = await previewImport(file)
      setImportPreview({
        datasets_count: preview.datasets_count,
        configurations_count: preview.configurations_count,
        results_count: preview.results_count
      })
    } catch {
      message.error('解析导入文件失败')
      setImportFile(null)
    }
  }

  const handleImport = async () => {
    if (!importFile) {
      message.warning('请先选择导入文件')
      return
    }

    setImporting(true)
    try {
      const result = await importData(importFile)
      message.success(
        `导入成功：${result.imported_datasets} 个数据集，${result.imported_configurations} 个配置，${result.imported_results} 个结果`
      )
      handleImportModalClose()
      fetchDatasets()
      fetchFolders()
    } catch {
      message.error('导入失败')
    } finally {
      setImporting(false)
    }
  }

  // ============ 删除功能 ============
  const handleDelete = async (dataset: Dataset) => {
    try {
      await deleteDataset(dataset.id)
      message.success('删除成功')
      fetchDatasets()
      fetchFolders()
    } catch {
      // Error is handled by the API layer
    }
  }

  // ============ 列名展示 ============
  const renderColumns = (columns: string[]) => {
    if (columns.length === 0) {
      return <Text type="secondary">-</Text>
    }

    const visibleColumns = columns.slice(0, MAX_VISIBLE_COLUMNS)
    const hiddenCount = columns.length - MAX_VISIBLE_COLUMNS

    return (
      <Space size={[4, 4]} wrap>
        {visibleColumns.map((col) => (
          <Tag key={col} style={{ margin: 0 }}>
            {col}
          </Tag>
        ))}
        {hiddenCount > 0 && (
          <Tooltip title={columns.slice(MAX_VISIBLE_COLUMNS).join(', ')}>
            <Tag color="blue" style={{ margin: 0, cursor: 'pointer' }}>
              +{hiddenCount}
            </Tag>
          </Tooltip>
        )}
      </Space>
    )
  }

  // ============ 表格列定义 ============
  const columns: ColumnsType<Dataset> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (name: string) => (
        <Space>
          <FileTextOutlined style={{ color: '#1890ff' }} />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: 180,
      ellipsis: true,
      render: (filename: string) => (
        <Tooltip title={filename}>
          <Text type="secondary">{filename}</Text>
        </Tooltip>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 220,
      ellipsis: true,
      render: (description: string) =>
        description ? (
          <Tooltip title={description}>
            <Text type="secondary">{description}</Text>
          </Tooltip>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '行数',
      dataIndex: 'row_count',
      key: 'row_count',
      width: 100,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '列数',
      dataIndex: 'column_count',
      key: 'column_count',
      width: 80,
    },
    {
      title: '列名',
      dataIndex: 'columns',
      key: 'columns',
      width: 280,
      render: (cols: string[]) => renderColumns(cols),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => formatDateTime(date),
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="预览">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handlePreview(record)}
            />
          </Tooltip>
          <Tooltip title="数据探索">
            <Button
              type="text"
              size="small"
              icon={<LineChartOutlined />}
              onClick={() => handleExploration(record)}
            />
          </Tooltip>
          <Tooltip title="质量检测">
            <Button
              type="text"
              size="small"
              icon={<SafetyCertificateOutlined />}
              onClick={() => handleQualityCheck(record)}
            />
          </Tooltip>
          <Tooltip title="下载">
            <Button
              type="text"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record)}
            />
          </Tooltip>
          {/* 仅管理员可编辑 */}
          {isAdmin && (
            <Tooltip title="编辑">
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEditModalOpen(record)}
              />
            </Tooltip>
          )}
          {/* 仅管理员可删除 */}
          {isAdmin && (
            <Popconfirm
              title="确认删除"
              description={`确定要删除数据集「${record.name}」吗？相关的配置和结果也会被删除。`}
              onConfirm={() => handleDelete(record)}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Tooltip title="删除">
                <Button type="text" size="small" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const deletingFolderChildren = deletingFolder
    ? folders.filter((folder) => folder.parent_id === deletingFolder.id)
    : []
  const deletingFolderTotalDatasets = deletingFolder
    ? deletingFolder.dataset_count +
      deletingFolderChildren.reduce((sum, folder) => sum + folder.dataset_count, 0)
    : 0

  // ============ 渲染 ============
  return (
    <div style={{ padding: 24 }}>
      {/* 页面头部 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              数据中心
            </Title>
            <Text type="secondary">管理时间序列数据集，支持上传、预览、下载</Text>
          </div>
          <Space>
            {/* 仅管理员可排序 */}
            {isAdmin && (
              <Button icon={<SortAscendingOutlined />} onClick={() => setSortModalOpen(true)}>
                排序
              </Button>
            )}
            {/* 仅管理员可导入 */}
            {isAdmin && (
              <Button icon={<ImportOutlined />} onClick={handleImportModalOpen}>
                导入
              </Button>
            )}
            {/* 仅管理员可上传 */}
            {isAdmin && (
              <Button type="primary" icon={<UploadOutlined />} onClick={handleUploadModalOpen}>
                上传数据集
              </Button>
            )}
          </Space>
        </div>
      </Card>

      <Row gutter={16}>
        <Col xs={24} md={7} lg={6} xl={5}>
          <Card
            size="small"
            title="文件夹"
            extra={
              <Space size="small">
                <Select<FolderSortValue>
                  size="small"
                  style={{ width: 140 }}
                  value={folderSort}
                  onChange={(value) => setFolderSort(value)}
                  options={[
                    { label: '手动排序', value: 'manual' },
                    { label: '名称 A-Z', value: 'name_asc' },
                    { label: '名称 Z-A', value: 'name_desc' },
                    { label: '创建时间（最新）', value: 'time_desc' },
                    { label: '创建时间（最旧）', value: 'time_asc' },
                  ]}
                />
                {isAdmin && folderSort === 'manual' && (
                  <Button size="small" onClick={() => setFolderSortModalOpen(true)}>
                    文件夹排序
                  </Button>
                )}
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            {foldersLoading ? (
              <div style={{ textAlign: 'center', padding: 24 }}>
                <Spin />
              </div>
            ) : (
              <Tree.DirectoryTree
                multiple={false}
                blockNode
                showIcon={false}
                expandedKeys={folderTreeExpandedKeys}
                onExpand={(keys) => setFolderTreeExpandedKeys(keys)}
                treeData={folderTreeData}
                selectedKeys={[selectedTreeKey]}
                onSelect={(keys) => handleTreeSelect(keys)}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} md={17} lg={18} xl={19}>
          <Card style={{ marginBottom: 16 }} size="small">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <Breadcrumb>
                <Breadcrumb.Item>
                  <a onClick={() => handleSelectFolder(null)}>根目录</a>
                </Breadcrumb.Item>
                {folderPath.map((folder) => (
                  <Breadcrumb.Item key={folder.id}>
                    <a onClick={() => handleSelectFolder(folder.id)}>{folder.name}</a>
                  </Breadcrumb.Item>
                ))}
              </Breadcrumb>
              <Space size="small">
                {currentFolder && (
                  <Tooltip title="查看描述">
                    <Button
                      size="small"
                      icon={<InfoCircleOutlined />}
                      onClick={() => handleOpenFolderInfo(currentFolder)}
                    />
                  </Tooltip>
                )}
                {isAdmin && (
                  <Button
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={handleOpenCreateFolder}
                    disabled={Boolean(currentFolder && currentFolder.parent_id !== null)}
                  >
                    新建文件夹
                  </Button>
                )}
              </Space>
            </div>
          </Card>

          <Card
            style={{ marginBottom: 16 }}
            size="small"
            title={selectedFolderId === null ? '文件夹' : '子文件夹'}
          >
            {childFolders.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文件夹" />
            ) : (
              <List
                grid={{ gutter: 12, xs: 1, sm: 2, md: 2, lg: 3, xl: 4, xxl: 4 }}
                dataSource={childFolders}
                renderItem={(folder) => (
                  <List.Item key={folder.id}>
                    <Card size="small" hoverable onClick={() => handleSelectFolder(folder.id)}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: 8,
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            flex: 1,
                            minWidth: 0,
                          }}
                        >
                          <Text strong ellipsis style={{ flex: 1, minWidth: 0 }}>
                            {folder.name}
                          </Text>
                          <Badge count={folder.dataset_count} size="small" />
                        </div>
                        <Space size={0}>
                          <Tooltip title="描述">
                            <Button
                              type="text"
                              size="small"
                              icon={<InfoCircleOutlined />}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleOpenFolderInfo(folder)
                              }}
                            />
                          </Tooltip>
                          {isAdmin && (
                            <Dropdown
                              menu={{
                                items: [
                                  { key: 'rename', label: '编辑' },
                                  { key: 'delete', label: '删除', danger: true },
                                ],
                                onClick: ({ key }) => {
                                  if (key === 'rename') {
                                    handleOpenRenameFolder(folder)
                                  } else if (key === 'delete') {
                                    handleOpenDeleteFolder(folder)
                                  }
                                },
                              }}
                              trigger={['click']}
                            >
                              <Button
                                type="text"
                                size="small"
                                icon={<MoreOutlined />}
                                onClick={(e) => e.stopPropagation()}
                              />
                            </Dropdown>
                          )}
                        </Space>
                      </div>
                      {folder.description ? (
                        <Text type="secondary" ellipsis={{ tooltip: folder.description }}>
                          {folder.description}
                        </Text>
                      ) : (
                        <Text type="secondary">-</Text>
                      )}
                    </Card>
                  </List.Item>
                )}
              />
            )}
          </Card>

          {selectedRowKeys.length > 0 && (
            <Card style={{ marginBottom: 16 }} size="small">
              <Space wrap>
                <Text>已选择 {selectedRowKeys.length} 项</Text>
                <Button icon={<ExportOutlined />} onClick={handleExport} loading={exporting}>
                  导出选中
                </Button>
                {isAdmin && (
                  <Select
                    style={{ width: 220 }}
                    placeholder="移动到..."
                    disabled={batchMoving}
                    onSelect={(value) => handleBatchMove(value as 'root' | number)}
                    options={folderSelectOptions}
                  />
                )}
                {isAdmin && (
                  <Popconfirm
                    title="批量删除"
                    description={`确定要删除选中的 ${selectedRowKeys.length} 个数据集吗？相关的配置和结果也会被删除。`}
                    onConfirm={handleBatchDelete}
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                  >
                    <Button danger icon={<DeleteOutlined />} loading={batchDeleting}>
                      批量删除
                    </Button>
                  </Popconfirm>
                )}
                <Button type="link" onClick={() => setSelectedRowKeys([])}>
                  取消选择
                </Button>
              </Space>
            </Card>
          )}

          <Card>
            <Table
              columns={columns}
              dataSource={datasets}
              rowKey="id"
              loading={loading}
              scroll={{ x: 1500 }}
              rowSelection={{
                selectedRowKeys,
                onChange: (keys) => setSelectedRowKeys(keys),
              }}
              pagination={{
                current: currentPage,
                pageSize: pageSize,
                total: total,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (t) => `共 ${t} 个数据集`,
                pageSizeOptions: ['10', '20', '50'],
                onChange: (page, size) => {
                  setCurrentPage(page)
                  setPageSize(size)
                },
              }}
              locale={{
                emptyText: (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据集">
                    {isAdmin && (
                      <Button type="primary" onClick={handleUploadModalOpen}>
                        上传第一个数据集
                      </Button>
                    )}
                  </Empty>
                ),
              }}
            />
          </Card>
        </Col>
      </Row>

      <FolderSortModal
        open={folderSortModalOpen}
        parentId={selectedFolderId}
        onClose={() => setFolderSortModalOpen(false)}
        onSuccess={fetchFolders}
      />

      <Modal
        title={folderInfoFolder ? `文件夹：${folderInfoFolder.name}` : '文件夹'}
        open={folderInfoModalOpen}
        onCancel={handleCloseFolderInfo}
        footer={[
          <Button key="close" onClick={handleCloseFolderInfo}>
            关闭
          </Button>,
        ]}
      >
        {folderInfoFolder ? (
          <Descriptions column={1} size="small">
            <Descriptions.Item label="名称">{folderInfoFolder.name}</Descriptions.Item>
            <Descriptions.Item label="描述">
              {folderInfoFolder.description ? (
                <Text>{folderInfoFolder.description}</Text>
              ) : (
                <Text type="secondary">-</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {formatDateTime(folderInfoFolder.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {formatDateTime(folderInfoFolder.updated_at)}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无信息" />
        )}
      </Modal>

      <Modal
        title={editingFolder ? '编辑文件夹' : '新建文件夹'}
        open={folderModalOpen}
        onCancel={handleCloseFolderModal}
        onOk={handleSaveFolder}
        okText={editingFolder ? '保存' : '创建'}
        cancelText="取消"
        confirmLoading={folderSaving}
        maskClosable={!folderSaving}
        closable={!folderSaving}
      >
        <Form form={folderForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="文件夹名称"
            rules={[
              { required: true, message: '请输入文件夹名称' },
              { max: 255, message: '名称不能超过255个字符' },
            ]}
          >
            <Input placeholder="请输入文件夹名称" disabled={folderSaving} />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
            rules={[{ max: 1000, message: '描述不能超过1000个字符' }]}
          >
            <Input.TextArea
              placeholder="可选"
              disabled={folderSaving}
              autoSize={{ minRows: 3, maxRows: 6 }}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="删除文件夹"
        open={deleteFolderModalOpen}
        onCancel={handleCloseDeleteFolderModal}
        onOk={handleConfirmDeleteFolder}
        okText="删除"
        cancelText="取消"
        confirmLoading={folderDeleting}
        okButtonProps={{
          danger: true,
          disabled:
            deleteFolderAction === 'cascade' &&
            deleteFolderConfirmName !== deletingFolder?.name,
        }}
        maskClosable={!folderDeleting}
        closable={!folderDeleting}
      >
        {deletingFolder && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text>
              文件夹「{deletingFolder.name}」包含 {deletingFolderTotalDatasets} 个数据集
            </Text>
            {deletingFolderChildren.length > 0 && (
              <Text type="secondary">包含 {deletingFolderChildren.length} 个子文件夹</Text>
            )}
            <Radio.Group
              value={deleteFolderAction}
              onChange={(e) => setDeleteFolderAction(e.target.value)}
            >
              <Space direction="vertical">
                <Radio value="move_to_root">将数据集移到根目录（推荐）</Radio>
                <Radio value="cascade">
                  <Text type="danger">同时删除所有数据集（不可恢复）</Text>
                </Radio>
              </Space>
            </Radio.Group>
            {deleteFolderAction === 'cascade' && (
              <div>
                <Text type="danger">请输入文件夹名称确认：</Text>
                <Input
                  placeholder={deletingFolder.name}
                  value={deleteFolderConfirmName}
                  onChange={(e) => setDeleteFolderConfirmName(e.target.value)}
                />
              </div>
            )}
          </Space>
        )}
      </Modal>

      {/* 上传 Modal */}
      <Modal
        title="上传数据集"
        open={uploadModalOpen}
        onCancel={handleUploadModalClose}
        onOk={handleUpload}
        okText="上传"
        cancelText="取消"
        confirmLoading={uploading}
        maskClosable={!uploading}
        closable={!uploading}
        width={760}
      >
        <Form form={uploadForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="选择文件" required>
            <Dragger {...uploadProps} disabled={uploading}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                仅支持 CSV 文件，最大 {formatFileSize(APP_CONFIG.UPLOAD.MAX_SIZE)}
              </p>
            </Dragger>
          </Form.Item>

          {uploadFileList.length > 0 && (
            <Form.Item label="文件列表">
              <Table
                size="small"
                rowKey="uid"
                pagination={false}
                dataSource={uploadFileList}
                scroll={{ y: 240 }}
                columns={[
                  {
                    title: '文件',
                    dataIndex: 'name',
                    key: 'name',
                    ellipsis: true,
                  },
                  {
                    title: '数据集名称',
                    key: 'dataset_name',
                    width: 300,
                    render: (_, record: UploadFile) => (
                      <Input
                        value={
                          uploadNameByUid[record.uid] ?? record.name.replace(/\.csv$/i, '')
                        }
                        onChange={(e) =>
                          setUploadNameByUid((prev) => ({
                            ...prev,
                            [record.uid]: e.target.value,
                          }))
                        }
                        disabled={uploading}
                      />
                    ),
                  },
                  {
                    title: '大小',
                    key: 'size',
                    width: 110,
                    render: (_, record: UploadFile) => formatFileSize(record.size ?? 0),
                  },
                ]}
              />
            </Form.Item>
          )}

          <Form.Item
            name="description"
            label="描述"
            rules={[{ max: 1000, message: '描述不能超过1000个字符' }]}
          >
            <TextArea
              placeholder="请输入数据集描述（可选）"
              rows={3}
              disabled={uploading}
            />
          </Form.Item>

          <Form.Item name="folder_id" label="文件夹">
            <Select
              placeholder="选择文件夹"
              allowClear
              disabled={uploading}
              options={folderSelectOptions}
            />
          </Form.Item>

          {uploading && (
            <Form.Item label="上传进度">
              <Space direction="vertical" style={{ width: '100%' }} size={4}>
                <Progress percent={uploadProgress} status="active" />
                <Text type="secondary">
                  {uploadingIndex}/{uploadingTotal}
                </Text>
              </Space>
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 预览 Modal */}
      <Modal
        title={`预览数据集：${previewDataset?.name || ''}`}
        open={previewModalOpen}
        onCancel={handlePreviewModalClose}
        footer={[
          <Button key="close" onClick={handlePreviewModalClose}>
            关闭
          </Button>,
          <Button
            key="download"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => previewDataset && handleDownload(previewDataset)}
          >
            下载
          </Button>,
        ]}
        width={1000}
      >
        {previewDataset && (
          <Descriptions
            bordered
            size="small"
            column={4}
            style={{ marginBottom: 16 }}
          >
            <Descriptions.Item label="文件名">{previewDataset.filename}</Descriptions.Item>
            <Descriptions.Item label="大小">
              {formatFileSize(previewDataset.file_size)}
            </Descriptions.Item>
            <Descriptions.Item label="总行数">
              {previewDataset.row_count.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="列数">{previewDataset.column_count}</Descriptions.Item>
            <Descriptions.Item label="列名" span={4}>
              {renderColumns(previewDataset.columns)}
            </Descriptions.Item>
            {previewDataset.description && (
              <Descriptions.Item label="描述" span={4}>
                {previewDataset.description}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}

        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          预览前 {APP_CONFIG.PREVIEW.DEFAULT_ROWS} 行数据
          {previewData && previewData.total_rows > APP_CONFIG.PREVIEW.DEFAULT_ROWS && (
            <span>（共 {previewData.total_rows.toLocaleString()} 行）</span>
          )}
        </Text>

        <Table
          columns={getPreviewColumns()}
          dataSource={previewData?.data || []}
          rowKey={(_, index) => String(index)}
          loading={previewLoading}
          scroll={{ x: 'max-content', y: 400 }}
          pagination={false}
          size="small"
          bordered
        />
      </Modal>

      {/* 编辑 Modal */}
      <Modal
        title="编辑数据集"
        open={editModalOpen}
        onCancel={handleEditModalClose}
        onOk={handleEdit}
        okText="保存"
        cancelText="取消"
        confirmLoading={editLoading}
        maskClosable={!editLoading}
        closable={!editLoading}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="数据集名称"
            rules={[
              { required: true, message: '请输入数据集名称' },
              { max: 255, message: '名称不能超过255个字符' },
            ]}
          >
            <Input placeholder="请输入数据集名称" disabled={editLoading} />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
            rules={[{ max: 1000, message: '描述不能超过1000个字符' }]}
          >
            <TextArea
              placeholder="请输入数据集描述（可选）"
              rows={3}
              disabled={editLoading}
            />
          </Form.Item>

          <Form.Item name="folder_id" label="文件夹">
            <Select
              placeholder="选择文件夹（可选，默认根目录）"
              allowClear
              disabled={editLoading}
              options={folderSelectOptions}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 数据质量检测抽屉 */}
      <Drawer
        title={
          <Space>
            <SafetyCertificateOutlined />
            数据质量检测 - {qualityDataset?.name}
          </Space>
        }
        placement="right"
        width={900}
        open={qualityDrawerOpen}
        onClose={handleQualityDrawerClose}
        destroyOnClose
      >
        {qualityLoading && !qualityReport ? (
          <div style={{ textAlign: 'center', padding: 100 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">正在分析数据质量...</Text>
            </div>
          </div>
        ) : (
          <DataQualityReportComponent
            report={qualityReport}
            loading={qualityLoading}
            onRefresh={handleQualityRefresh}
            onOpenCleaning={handleOpenCleaning}
            isAdmin={isAdmin}
          />
        )}
      </Drawer>

      {/* 数据清洗弹窗 */}
      {qualityDataset && (
        <DataCleaningModal
          visible={cleaningModalOpen}
          datasetId={qualityDataset.id}
          datasetName={qualityDataset.name}
          qualityReport={qualityReport}
          onClose={() => setCleaningModalOpen(false)}
          onSuccess={handleCleaningSuccess}
        />
      )}

      {/* 数据探索抽屉 */}
      <Drawer
        title={
          <Space>
            <LineChartOutlined />
            数据探索 - {explorationDataset?.name}
          </Space>
        }
        placement="right"
        width={1100}
        open={explorationDrawerOpen}
        onClose={handleExplorationDrawerClose}
        destroyOnClose
      >
        {explorationDataset && (
          <DataExploration
            datasetId={explorationDataset.id}
            datasetName={explorationDataset.name}
            columns={explorationDataset.columns}
          />
        )}
      </Drawer>

      {/* 导入 Modal */}
      <Modal
        title="导入数据"
        open={importModalOpen}
        onCancel={handleImportModalClose}
        onOk={handleImport}
        okText="导入"
        cancelText="取消"
        confirmLoading={importing}
        okButtonProps={{ disabled: !importFile }}
      >
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="选择导入文件" required>
            <Dragger
              accept=".zip"
              maxCount={1}
              beforeUpload={(file) => {
                handleImportFileChange(file)
                return false
              }}
              onRemove={() => {
                setImportFile(null)
                setImportPreview(null)
              }}
              fileList={importFile ? [{ uid: '-1', name: importFile.name, status: 'done' }] : []}
              disabled={importing}
            >
              <p className="ant-upload-drag-icon">
                <ImportOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽 ZIP 文件到此区域</p>
              <p className="ant-upload-hint">
                支持导入之前导出的数据包
              </p>
            </Dragger>
          </Form.Item>

          {importPreview && (
            <Card size="small" title="导入预览">
              <Space direction="vertical">
                <Text>数据集: {importPreview.datasets_count} 个</Text>
                <Text>配置: {importPreview.configurations_count} 个</Text>
                <Text>结果: {importPreview.results_count} 个</Text>
              </Space>
            </Card>
          )}
        </Form>
      </Modal>

      {/* 排序弹窗 */}
      <DatasetSortModal
        open={sortModalOpen}
        onClose={() => setSortModalOpen(false)}
        onSuccess={fetchDatasets}
      />
    </div>
  )
}
