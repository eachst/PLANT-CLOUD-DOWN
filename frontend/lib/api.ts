import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { useAuthStore } from '../store';

// API客户端配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || '/api';

// 确保API_BASE_URL不以/api结尾，避免重复
const normalizedBaseUrl = API_BASE_URL.endsWith('/api') ? API_BASE_URL : `${API_BASE_URL}/api`;

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: normalizedBaseUrl,
      timeout: 60000, // 预测可能需要更长时间
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器 - 延迟获取token，避免循环依赖
    this.client.interceptors.request.use(
      (config) => {
        // FormData 请求：移除默认 JSON Content-Type，让浏览器/axios 自动设置 boundary
        if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
          const headers: any = config.headers || {};
          headers['Content-Type'] = undefined;
          headers['content-type'] = undefined;
          config.headers = headers;
        }

        // 添加认证令牌
        const authStore = require('../store').useAuthStore;
        const token = authStore.getState().token;
        if (token) {
          (config.headers as any).Authorization = `Bearer ${token}`;
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器 - 延迟获取authStore，避免循环依赖
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      async (error) => {
        const originalRequest = error.config;
        
        // 处理401未授权错误
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            // 尝试刷新令牌
            const authStore = require('../store').useAuthStore;
            await authStore.getState().refreshToken();
            
            // 重新发送原始请求
            const token = authStore.getState().token;
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            
            return this.client(originalRequest);
          } catch (refreshError) {
            // 刷新失败，退出登录
            const authStore = require('../store').useAuthStore;
            authStore.getState().logout();
            return Promise.reject(refreshError);
          }
        }
        
        return Promise.reject(error);
      }
    );
  }

  // GET请求
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  // POST请求
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  // PUT请求
  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  // DELETE请求
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  // PATCH请求
  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  // 上传文件
  async upload<T = any>(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, formData, {
      ...config,
      headers: {
        // 移除硬编码的Content-Type，让浏览器自动设置
        // 浏览器会自动添加正确的boundary
        ...config?.headers,
      },
    });
    return response.data;
  }

  // 下载文件
  async download(url: string, filename?: string, config?: AxiosRequestConfig): Promise<void> {
    // 首先检查是否在浏览器环境中
    if (typeof window === 'undefined') {
      throw new Error('Download function can only be called in browser environment');
    }
    
    const response = await this.client.get(url, {
      ...config,
      responseType: 'blob',
    });
    
    // 创建下载链接
    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }
}

// 创建API客户端实例
const apiClient = new ApiClient();

export default apiClient;