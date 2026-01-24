/**
 * 数据中心页面
 * 功能：数据集的上传、预览、下载、管理和数据质量检测
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Badge,
  Col,
  Card,
  Table,
  Button,
  Dropdown,
  Menu,
  Radio,
  Row,
  Select,
  Space,
  Modal,
  Form,
  Input,
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
import type { UploadFile, UploadProps } from 'antd/es/upload'
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  ExportOutlined,
  InboxOutlined,
  FileTextOutlined,
  FolderOutlined,
  HomeOutlined,
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

  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [folderForm] = Form.useForm()
  const [editingFolder, setEditingFolder] = useState<Folder | null>(null)
  const [folderSaving, setFolderSaving] = useState(false)

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
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

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

  const selectedFolderMenuKey =
    selectedFolderId === null ? 'root' : `folder-${selectedFolderId}`

  const handleFolderMenuClick = (key: string) => {
    if (key === 'create') {
      setEditingFolder(null)
      setFolderModalOpen(true)
      folderForm.resetFields()
      return
    }

    if (key === 'root') {
      setSelectedFolderId(null)
      setCurrentPage(1)
      setSelectedRowKeys([])
      return
    }

    if (key.startsWith('folder-')) {
      const id = Number(key.slice('folder-'.length))
      if (!Number.isNaN(id)) {
        setSelectedFolderId(id)
        setCurrentPage(1)
        setSelectedRowKeys([])
      }
    }
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
      setFolderSaving(true)

      if (editingFolder) {
        await updateFolderApi(editingFolder.id, {
          name: values.name,
          description: values.description || '',
        })
        message.success('重命名成功')
      } else {
        await createFolder({
          name: values.name,
          description: values.description || '',
          parent_id: null,
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
    if (folder.dataset_count === 0) {
      Modal.confirm({
        title: '删除文件夹',
        content: `确认删除文件夹「${folder.name}」吗？`,
        okText: '删除',
        cancelText: '取消',
        okButtonProps: { danger: true },
        onOk: async () => {
          await deleteFolder(folder.id, { action: 'move_to_root' })
          message.success('删除成功')
          if (selectedFolderId === folder.id) {
            setSelectedFolderId(null)
            setCurrentPage(1)
            setSelectedRowKeys([])
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
      const wasSelected = selectedFolderId === deletingFolder.id
      const params =
        deleteFolderAction === 'cascade'
          ? { action: 'cascade' as const, confirm_name: deleteFolderConfirmName }
          : { action: 'move_to_root' as const }

      await deleteFolder(deletingFolder.id, params)
      message.success('删除成功')

      handleCloseDeleteFolderModal()
      if (wasSelected) {
        setSelectedFolderId(null)
        setCurrentPage(1)
        setSelectedRowKeys([])
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
    setUploadFile(null)
    setUploadProgress(0)
    uploadForm.resetFields()
  }

  const handleUploadModalClose = () => {
    setUploadModalOpen(false)
    setUploadFile(null)
    setUploadProgress(0)
    uploadForm.resetFields()
  }

  const uploadProps: UploadProps = {
    accept: APP_CONFIG.UPLOAD.ALLOWED_TYPES.join(','),
    maxCount: 1,
    beforeUpload: (file) => {
      // 检查文件大小
      if (file.size > APP_CONFIG.UPLOAD.MAX_SIZE) {
        message.error(`文件大小不能超过 ${formatFileSize(APP_CONFIG.UPLOAD.MAX_SIZE)}`)
        return Upload.LIST_IGNORE
      }
      // 检查文件类型
      const isCSV = file.name.toLowerCase().endsWith('.csv')
      if (!isCSV) {
        message.error('只支持 CSV 文件')
        return Upload.LIST_IGNORE
      }
      // 保存原始 File 对象
      setUploadFile(file)
      // 自动填充名称（去掉扩展名）
      const nameWithoutExt = file.name.replace(/\.csv$/i, '')
      uploadForm.setFieldValue('name', nameWithoutExt)
      return false // 阻止自动上传
    },
    onRemove: () => {
      setUploadFile(null)
      uploadForm.setFieldValue('name', '')
    },
    fileList: uploadFile ? [{ uid: '-1', name: uploadFile.name, status: 'done' } as UploadFile] : [],
  }

  const handleUpload = async () => {
    try {
      const values = await uploadForm.validateFields()
      if (!uploadFile) {
        message.error('请选择文件')
        return
      }

      setUploading(true)
      setUploadProgress(0)

      await uploadDataset(
        values.name,
        values.description || '',
        uploadFile,
        values.folder_id ?? null,
        (percent) => setUploadProgress(percent)
      )

      message.success('上传成功')
      setUploading(false)
      handleUploadModalClose()
      fetchDatasets()
      fetchFolders()
    } catch {
      // Error is handled by the API layer
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
      folder_id: dataset.folder_id,
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
      const nextFolderId = (values.folder_id ?? null) as number | null
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
      title: '文件夹',
      dataIndex: 'folder_id',
      key: 'folder_id',
      width: 140,
      render: (folderId: number | null) => {
        if (folderId === null) {
          return <Text type="secondary">根目录</Text>
        }
        const folder = folders.find((item) => item.id === folderId)
        return folder ? (
          <Tag icon={<FolderOutlined />}>{folder.name}</Tag>
        ) : (
          <Text type="secondary">-</Text>
        )
      },
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
              <Menu
                mode="inline"
                selectedKeys={[selectedFolderMenuKey]}
                onClick={({ key }) => handleFolderMenuClick(String(key))}
              >
                <Menu.Item key="root" icon={<HomeOutlined />}>
                  <Space>
                    <span>根目录</span>
                    <Badge count={rootDatasetCount} size="small" />
                  </Space>
                </Menu.Item>
                <Menu.Divider />
                {folders.map((folder) => (
                  <Menu.Item key={`folder-${folder.id}`} icon={<FolderOutlined />}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <Space size={6}>
                        {folder.description ? (
                          <Tooltip title={folder.description}>
                            <span>{folder.name}</span>
                          </Tooltip>
                        ) : (
                          <span>{folder.name}</span>
                        )}
                        <Badge count={folder.dataset_count} size="small" />
                      </Space>
                      {isAdmin && (
                        <Dropdown
                          menu={{
                            items: [
                              { key: 'rename', label: '重命名' },
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
                    </div>
                  </Menu.Item>
                ))}
                {isAdmin && (
                  <>
                    <Menu.Divider />
                    <Menu.Item key="create" icon={<PlusOutlined />}>
                      新建文件夹
                    </Menu.Item>
                  </>
                )}
              </Menu>
            )}
          </Card>
        </Col>

        <Col xs={24} md={17} lg={18} xl={19}>
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
                    options={[
                      { label: '根目录', value: 'root' },
                      ...folders.map((folder) => ({ label: folder.name, value: folder.id })),
                    ]}
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
        onClose={() => setFolderSortModalOpen(false)}
        onSuccess={fetchFolders}
      />

      <Modal
        title={editingFolder ? '重命名文件夹' : '新建文件夹'}
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
              文件夹「{deletingFolder.name}」包含 {deletingFolder.dataset_count} 个数据集
            </Text>
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
        width={520}
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

          <Form.Item
            name="name"
            label="数据集名称"
            rules={[
              { required: true, message: '请输入数据集名称' },
              { max: 255, message: '名称不能超过255个字符' },
            ]}
          >
            <Input placeholder="请输入数据集名称" disabled={uploading} />
          </Form.Item>

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
              placeholder="选择文件夹（可选，默认根目录）"
              allowClear
              disabled={uploading}
              options={folders.map((folder) => ({ label: folder.name, value: folder.id }))}
            />
          </Form.Item>

          {uploading && (
            <Form.Item label="上传进度">
              <Progress percent={uploadProgress} status="active" />
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
              options={folders.map((folder) => ({ label: folder.name, value: folder.id }))}
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
