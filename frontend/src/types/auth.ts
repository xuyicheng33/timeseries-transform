/**
 * 用户认证相关类型定义
 */

// 用户信息
export interface User {
  id: number
  username: string
  email: string
  full_name: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  last_login: string | null
}

// 用户注册
export interface UserRegister {
  username: string
  email: string
  password: string
  full_name?: string
}

// 用户登录
export interface UserLogin {
  username: string
  password: string
}

// 用户信息更新
export interface UserUpdate {
  email?: string
  full_name?: string
}

// 密码更新
export interface PasswordUpdate {
  old_password: string
  new_password: string
}

// Token 响应
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// Token 刷新请求
export interface TokenRefresh {
  refresh_token: string
}

// 认证状态
export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}
