/**
 * 原始 Axios 实例
 * 用于 Blob 下载，保留完整的 response（包含 headers）
 */

import axios from 'axios'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const API_PREFIX = (import.meta.env.VITE_API_PREFIX || '/api').replace(/\/$/, '')

const rawRequest = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`,
  timeout: 30000,
})

export default rawRequest

