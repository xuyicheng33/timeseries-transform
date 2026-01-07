/**
 * Axios 请求实例
 * 包含 Token 自动附加和刷新逻辑
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { message } from 'antd'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const API_PREFIX = (import.meta.env.VITE_API_PREFIX || '/api').replace(/\/$/, '')

const TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// 创建 axios 实例
const request = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`,
  timeout: 30000,
})

// 是否正在刷新 Token
let isRefreshing = false
// 等待刷新的请求队列
let refreshSubscribers: ((token: string) => void)[] = []

// 添加请求到等待队列
function subscribeTokenRefresh(callback: (token: string) => void) {
  refreshSubscribers.push(callback)
}

// 通知所有等待的请求
function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach((callback) => callback(token))
  refreshSubscribers = []
}

// 请求拦截器：自动附加 Token
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem(TOKEN_KEY)
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
    
    // 401 错误且不是刷新 Token 的请求
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
      
      // 如果没有 refresh token，直接清除登录状态
      if (!refreshToken) {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        // 不自动跳转，让页面自己处理
        return Promise.reject(error)
      }
      
      // 如果正在刷新，将请求加入队列
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            resolve(request(originalRequest))
          })
        })
      }
      
      originalRequest._retry = true
      isRefreshing = true
      
      try {
        // 刷新 Token
        const response = await axios.post(`${BASE_URL}${API_PREFIX}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        
        const { access_token, refresh_token: newRefreshToken } = response.data
        
        // 保存新 Token
        localStorage.setItem(TOKEN_KEY, access_token)
        localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken)
        
        // 通知等待的请求
        onTokenRefreshed(access_token)
        
        // 重试原请求
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`
        }
        return request(originalRequest)
      } catch (refreshError) {
        // 刷新失败，清除登录状态
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        refreshSubscribers = []
        
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
    
    // 处理其他错误
    const errorData = error.response?.data as { detail?: string } | undefined
    const errorMessage = errorData?.detail || error.message || '请求失败'
    
    // 显示错误消息（排除 401，因为会自动处理）
    if (error.response?.status !== 401) {
      message.error(errorMessage)
    }
    
    return Promise.reject(error)
  }
)

export default request

/**
 * 原始 Axios 实例（不自动解包 response.data）
 * 用于 Blob 下载，保留完整的 response（包含 headers）
 */
export const rawRequest = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`,
  timeout: 30000,
})

// 为 rawRequest 也添加 Token
rawRequest.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

