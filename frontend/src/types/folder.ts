export interface Folder {
  id: number
  name: string
  description: string
  parent_id: number | null
  sort_order: number
  dataset_count: number
  created_at: string
  updated_at: string
}

export interface FolderListResponse {
  items: Folder[]
  total: number
  root_dataset_count: number
}

export interface FolderCreate {
  name: string
  description?: string
  parent_id?: number | null
}

export interface FolderUpdate {
  name?: string
  description?: string
}

export interface FolderSortOrderItem {
  id: number
  sort_order: number
}

export interface FolderSortOrderUpdate {
  orders: FolderSortOrderItem[]
}
