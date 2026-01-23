import api from './index'
import type {
  Folder,
  FolderCreate,
  FolderListResponse,
  FolderSortOrderUpdate,
  FolderUpdate,
} from '@/types'

export async function getFolders(
  sortBy: 'manual' | 'name' | 'time' = 'manual',
  order: 'asc' | 'desc' = 'asc'
): Promise<FolderListResponse> {
  return api.get('/folders', { params: { sort_by: sortBy, order } })
}

export async function createFolder(data: FolderCreate): Promise<Folder> {
  return api.post('/folders', data)
}

export async function updateFolder(id: number, data: FolderUpdate): Promise<Folder> {
  return api.put(`/folders/${id}`, data)
}

export async function deleteFolder(
  id: number,
  params: { action: 'move_to_root' | 'cascade'; confirm_name?: string }
): Promise<unknown> {
  return api.delete(`/folders/${id}`, { params })
}

export async function reorderFolders(
  data: FolderSortOrderUpdate
): Promise<{ message: string }> {
  return api.put('/folders/reorder', data)
}

