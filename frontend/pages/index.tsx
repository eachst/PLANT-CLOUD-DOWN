import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import { ProtectedRoute } from '../contexts/AuthContext';
import AppLayout from '../components/AppLayout';

const IndexPage = () => {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // 如果用户已登录，重定向到仪表板
    if (!isLoading && user) {
      router.push('/dashboard');
    }
  }, [user, isLoading, router]);

  // 如果正在加载用户信息，显示加载状态
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-secondary-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto"></div>
          <p className="mt-4 text-secondary-600">加载中...</p>
        </div>
      </div>
    );
  }

  // 如果用户未登录，显示登录页面
  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-secondary-900 mb-4">
          植物病害检测系统
        </h1>
        <p className="text-secondary-600 mb-8">
          请先登录以使用系统功能
        </p>
      </div>
    </div>
  );
};

export default IndexPage;