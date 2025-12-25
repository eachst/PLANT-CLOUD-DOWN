import { createContext, useContext, useEffect, useState } from 'react';
import { useAuthStore } from '../store';
import apiClient from '../lib/api';

// 用户类型定义
interface User {
  id: number;
  username: string;
  email: string;
  avatar?: string;
  role: string;
  created_at: string;
}

// 认证上下文类型定义
interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (userData: {
    username: string;
    email: string;
    password: string;
  }) => Promise<void>;
  clearError: () => void;
}

// 创建认证上下文
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// 认证提供者组件
export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const {
    user,
    token,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    refreshToken,
    clearError,
  } = useAuthStore();

  // 初始化时检查令牌有效性
  useEffect(() => {
    if (token && isAuthenticated) {
      refreshToken();
    }
  }, [token, isAuthenticated, refreshToken]);

  // 定期刷新令牌
  useEffect(() => {
    if (!token || !isAuthenticated) return;

    const interval = setInterval(() => {
      refreshToken();
    }, 14 * 60 * 1000); // 14分钟刷新一次

    return () => clearInterval(interval);
  }, [token, isAuthenticated, refreshToken]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// 使用认证上下文的Hook
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// 受保护路由组件
interface ProtectedRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

export const ProtectedRoute = ({
  children,
  redirectTo = '/login',
}: ProtectedRouteProps) => {
  const { isAuthenticated, isLoading } = useAuth();

  // 如果正在加载，显示加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  // 如果未认证，重定向到登录页
  if (!isAuthenticated) {
    if (typeof window !== 'undefined') {
      window.location.href = redirectTo;
    }
    return null;
  }

  // 如果已认证，渲染子组件
  return <>{children}</>;
};

// 公共路由组件（已登录用户不能访问）
interface PublicRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

export const PublicRoute = ({
  children,
  redirectTo = '/dashboard',
}: PublicRouteProps) => {
  const { isAuthenticated, isLoading } = useAuth();

  // 如果正在加载，显示加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  // 如果已认证，重定向到仪表板
  if (isAuthenticated) {
    if (typeof window !== 'undefined') {
      window.location.href = redirectTo;
    }
    return null;
  }

  // 如果未认证，渲染子组件
  return <>{children}</>;
};