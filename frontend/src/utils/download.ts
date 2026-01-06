/**
 * 文件下载工具
 */

import { message } from 'antd'
import rawRequest from '@/api/request'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const API_PREFIX = (import.meta.env.VITE_API_PREFIX || '/api').replace(/\/$/, '')

/**
 * 获取完整 URL
 */
function getFullUrl(path: string): string {
  return `${BASE_URL}${API_PREFIX}${path}`
}

/**
 * 从 Content-Disposition 头解析文件名
 */
function parseFilename(disposition: string | undefined): string | null {
  if (!disposition) return null

  const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition)
  if (matches && matches[1]) {
    let filename = matches[1].replace(/['"]/g, '')
    // 解码 URL 编码的文件名
    try {
      filename = decodeURIComponent(filename)
    } catch {
      // 如果解码失败，使用原始文件名
    }
    return filename
  }

  return null
}

/**
 * 使用 Blob 方式下载文件
 * @param path 不带 /api 前缀的路径，如 '/datasets/1/download'
 * @param fallbackFilename 备用文件名
 */
export async function downloadByBlob(
  path: string,
  fallbackFilename: string
): Promise<void> {
  try {
    const response = await rawRequest.get(path, {
      responseType: 'blob',
    })

    // 解析文件名
    const disposition = response.headers['content-disposition']
    const filename = parseFilename(disposition) || fallbackFilename

    // 创建 Blob URL 并触发下载
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    message.success('下载成功')
  } catch (error) {
    message.error('下载失败')
    throw error
  }
}

/**
 * 使用直链方式下载文件（简单场景）
 * @param path 不带 /api 前缀的路径，如 '/datasets/1/download'
 */
export function downloadByLink(path: string): void {
  const url = getFullUrl(path)
  const a = document.createElement('a')
  a.href = url
  a.download = ''
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

/**
 * 统一下载入口（推荐使用 Blob 方式）
 * @param path 不带 /api 前缀的路径
 * @param fallbackFilename 备用文件名
 */
export async function download(
  path: string,
  fallbackFilename: string
): Promise<void> {
  return downloadByBlob(path, fallbackFilename)
}

