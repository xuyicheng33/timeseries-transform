/**
 * 认证上下文
 * 提供全局的用户认证状态管理
 */

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import type { User, UserLogin, UserRegister } from '@/types'
import * as authApi from '@/api/auth'
import { tokenManager } from '@/api/auth'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (data: UserLogin) => Promise<void>
  register: (data: UserRegister) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // 获取当前用户信息
  const refreshUser = useCallback(async () => {
    if (!tokenManager.hasToken()) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const userData = await authApi.getCurrentUser()
      setUser(userData)
    } catch {
      // Token 无效，清除
      tokenManager.clearTokens()
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // 初始化时检查登录状态
  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  // 登录
  const login = async (data: UserLogin) => {
    await authApi.login(data)
    await refreshUser()
  }

  // 注册
  const register = async (data: UserRegister) => {
    await authApi.register(data)
    // 注册成功后自动登录
    await login({ username: data.username, password: data.password })
  }

  // 登出
  const logout = () => {
    authApi.logout()
    setUser(null)
  }

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext

