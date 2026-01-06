/**
 * 业务 Axios 实例
 * 自动解包 response.data，添加错误处理
 */

import axios from 'axios'
import { message } from 'antd'
import { getErrorMessage } from '@/utils/error'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const API_PREFIX = (import.meta.env.VITE_API_PREFIX || '/api').replace(/\/$/, '')

const api = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`,
  timeout: 30000,
})

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // 自动解包 data
    return response.data
  },
  (error) => {
    // 错误处理
    const errorMessage = getErrorMessage(error)
    message.error(errorMessage)
    return Promise.reject(error)
  }
)

export default api

