/**
 * 认证 API 服务
 */
import request from './request'
import { tokenManager } from './token'
import type {
  User,
  UserRegister,
  UserLogin,
  UserUpdate,
  PasswordUpdate,
  TokenResponse,
  TokenRefresh,
} from '@/types'

// 重新导出 tokenManager，保持向后兼容
export { tokenManager } from './token'

/**
 * 用户注册
 */
export async function register(data: UserRegister): Promise<User> {
  return request.post('/auth/register', data)
}

/**
 * 用户登录
 */
export async function login(data: UserLogin): Promise<TokenResponse> {
  // request 拦截器已经解包了 response.data，所以这里直接就是 TokenResponse
  const response = (await request.post('/auth/login/json', data)) as TokenResponse
  // 保存 Token
  tokenManager.setTokens(response.access_token, response.refresh_token)
  return response
}

/**
 * 刷新 Token
 */
export async function refreshToken(): Promise<TokenResponse> {
  const refresh_token = tokenManager.getRefreshToken()
  if (!refresh_token) {
    throw new Error('No refresh token')
  }

  const data: TokenRefresh = { refresh_token }
  // request 拦截器已经解包了 response.data，所以这里直接就是 TokenResponse
  const response = (await request.post('/auth/refresh', data)) as TokenResponse
  // 更新 Token
  tokenManager.setTokens(response.access_token, response.refresh_token)
  return response
}

/**
 * 登出
 */
export function logout(): void {
  tokenManager.clearTokens()
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<User> {
  return request.get('/auth/me')
}

/**
 * 更新用户信息
 */
export async function updateUser(data: UserUpdate): Promise<User> {
  return request.put('/auth/me', data)
}

/**
 * 修改密码
 */
export async function updatePassword(data: PasswordUpdate): Promise<{ message: string }> {
  return request.put('/auth/me/password', data)
}
