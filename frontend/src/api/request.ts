/**
 * Axios 请求实例
 * 包含 Token 自动附加和刷新逻辑
 */

import axios from 'axios'
import type { AxiosError, AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { message } from 'antd'
import { TOKEN_KEY, REFRESH_TOKEN_KEY, tokenManager } from './token'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const API_PREFIX = (import.meta.env.VITE_API_PREFIX || '/api').replace(/\/$/, '')

// 创建 axios 实例
const request = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`,
  timeout: 30000,
})

// 是否正在刷新 Token
let isRefreshing = false
// 等待刷新的请求队列
let refreshSubscribers: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []
// 刷新失败的冷却时间
let lastRefreshFailTime = 0
const REFRESH_COOLDOWN = 5000 // 5秒冷却

// 添加请求到等待队列
function subscribeTokenRefresh(
  resolve: (token: string) => void,
  reject: (error: unknown) => void
) {
  refreshSubscribers.push({ resolve, reject })
}

// 通知所有等待的请求（成功）
function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach(({ resolve }) => resolve(token))
  refreshSubscribers = []
}

// 通知所有等待的请求（失败）
function onTokenRefreshFailed(error: unknown) {
  refreshSubscribers.forEach(({ reject }) => reject(error))
  refreshSubscribers = []
}

// 执行 Token 刷新
async function doRefreshToken(): Promise<string> {
  const refreshToken = tokenManager.getRefreshToken()
  if (!refreshToken) {
    throw new Error('No refresh token')
  }

  const response = await axios.post(`${BASE_URL}${API_PREFIX}/auth/refresh`, {
    refresh_token: refreshToken,
  })

  const { access_token, refresh_token: newRefreshToken } = response.data
  tokenManager.setTokens(access_token, newRefreshToken)
  return access_token
}

// 处理 401 错误的统一逻辑
// retryInstance: 用于重试的 axios 实例，默认为 request
// returnFullResponse: 是否返回完整响应（用于 rawRequest）
async function handle401Error<T = unknown>(
  originalRequest: InternalAxiosRequestConfig & { _retry?: boolean },
  retryInstance: AxiosInstance = request,
  returnFullResponse: boolean = false
): Promise<T> {
  const refreshToken = tokenManager.getRefreshToken()

  // 如果没有 refresh token，直接清除登录状态
  if (!refreshToken) {
    tokenManager.clearTokens()
    return Promise.reject(new Error('No refresh token'))
  }

  // 检查是否在冷却期内
  if (Date.now() - lastRefreshFailTime < REFRESH_COOLDOWN) {
    tokenManager.clearTokens()
    if (window.location.pathname !== '/login') {
      message.error('登录已过期，请重新登录')
      window.location.href = '/login'
    }
    return Promise.reject(new Error('Refresh token failed recently'))
  }

  // 如果正在刷新，将请求加入队列
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      subscribeTokenRefresh(
        (token: string) => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`
          }
          const retryPromise = retryInstance(originalRequest)
          if (returnFullResponse) {
            resolve(retryPromise as T)
          } else {
            retryPromise.then((res: AxiosResponse) => resolve(res.data as T)).catch(reject)
          }
        },
        (err: unknown) => {
          reject(err)
        }
      )
    })
  }

  originalRequest._retry = true
  isRefreshing = true

  try {
    const newToken = await doRefreshToken()

    // 通知等待的请求
    onTokenRefreshed(newToken)

    // 重试原请求
    if (originalRequest.headers) {
      originalRequest.headers.Authorization = `Bearer ${newToken}`
    }
    const retryResponse = await retryInstance(originalRequest)
    return (returnFullResponse ? retryResponse : retryResponse.data) as T
  } catch (refreshError) {
    // 刷新失败，记录时间并清除登录状态
    lastRefreshFailTime = Date.now()
    tokenManager.clearTokens()

    // 通知所有等待的请求失败
    onTokenRefreshFailed(refreshError)

    // 跳转到登录页
    if (window.location.pathname !== '/login') {
      message.error('登录已过期，请重新登录')
      window.location.href = '/login'
    }
    return Promise.reject(refreshError)
  } finally {
    isRefreshing = false
  }
}

// 请求拦截器：自动附加 Token
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenManager.getAccessToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误和 Token 刷新
request.interceptors.response.use(
  (response) => {
    // 直接返回数据部分
    return response.data
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // 判断是否是认证相关接口（登录/注册）
    const isAuthEndpoint =
      originalRequest?.url?.includes('/auth/login') ||
      originalRequest?.url?.includes('/auth/register')

    // 401 错误处理
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      return handle401Error(originalRequest, request, false)
    }

    // 处理其他错误（包括登录/注册的 401）
    const errorData = error.response?.data as
      | { detail?: string | Array<{ msg: string; loc?: string[] }> }
      | undefined
    let errorMessage = '请求失败'

    if (errorData?.detail) {
      if (typeof errorData.detail === 'string') {
        // 简单字符串错误
        errorMessage = errorData.detail
      } else if (Array.isArray(errorData.detail)) {
        // FastAPI 验证错误数组
        errorMessage = errorData.detail.map((err) => err.msg || JSON.stringify(err)).join('; ')
      }
    } else if (error.message) {
      errorMessage = error.message
    }

    // 显示错误消息
    message.error(errorMessage)

    return Promise.reject(error)
  }
)

export default request

/**
 * 原始 Axios 实例（不自动解包 response.data）
 * 用于 Blob 下载，保留完整的 response（包含 headers）
 * 也支持 401 自动刷新
 */
export const rawRequest = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`,
  timeout: 30000,
})

// 为 rawRequest 添加 Token
rawRequest.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenManager.getAccessToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 为 rawRequest 添加 401 处理（返回完整响应）
rawRequest.interceptors.response.use(
  (response) => response, // 保持完整响应
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // 401 错误处理 - 使用 rawRequest 重试，返回完整响应
    if (error.response?.status === 401 && !originalRequest._retry) {
      return handle401Error<AxiosResponse>(originalRequest, rawRequest, true)
    }

    return Promise.reject(error)
  }
)
