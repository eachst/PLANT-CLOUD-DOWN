import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// API基础URL常量
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// 用户状态
interface User {
  id: number;
  username: string;
  email: string;
  avatar?: string;
  role: string;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // 操作
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (userData: {
    username: string;
    email: string;
    password: string;
  }) => Promise<void>;
  refreshToken: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
          });
          
          const data = await response.json();
          
          if (!response.ok) {
            throw new Error(data.message || '登录失败');
          }
          
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : '登录失败',
          });
          throw error;
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        });
      },

      register: async (userData) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData),
          });
          
          const data = await response.json();
          
          if (!response.ok) {
            throw new Error(data.message || '注册失败');
          }
          
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : '注册失败',
          });
          throw error;
        }
      },

      refreshToken: async () => {
        const { token } = get();
        
        if (!token) {
          return;
        }
        
        try {
          const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          const data = await response.json();
          
          if (!response.ok) {
            throw new Error(data.message || '令牌刷新失败');
          }
          
          set({
            token: data.access_token,
          });
        } catch (error) {
          // 刷新失败，退出登录
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            error: null,
          });
        }
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// 通知状态
interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  timestamp: string;
  read: boolean;
}

interface NotificationState {
  notifications: Notification[];
  
  // 操作
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  removeNotification: (id: string) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],

  addNotification: (notification) => {
    const id = Date.now().toString();
    const timestamp = new Date().toISOString();
    
    set({
      notifications: [
        ...get().notifications,
        {
          ...notification,
          id,
          timestamp,
          read: false,
        },
      ],
    });
    
    // 5秒后自动移除
    setTimeout(() => {
      get().removeNotification(id);
    }, 5000);
  },

  removeNotification: (id) => {
    set({
      notifications: get().notifications.filter(n => n.id !== id),
    });
  },

  markAsRead: (id) => {
    set({
      notifications: get().notifications.map(n =>
        n.id === id ? { ...n, read: true } : n
      ),
    });
  },

  markAllAsRead: () => {
    set({
      notifications: get().notifications.map(n => ({ ...n, read: true })),
    });
  },

  clearNotifications: () => {
    set({ notifications: [] });
  },
}));

// 任务状态
interface Task {
  id: string;
  title: string;
  description?: string;
  type: 'prediction' | 'segmentation' | 'analysis';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  result?: any;
  error?: string;
}

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;
  
  // 操作
  fetchTasks: () => Promise<void>;
  fetchTask: (id: string) => Promise<void>;
  createTask: (taskData: {
    title: string;
    type: 'prediction' | 'segmentation' | 'analysis';
    description?: string;
    data: any;
  }) => Promise<Task>;
  updateTask: (id: string, updates: Partial<Task>) => void;
  clearCurrentTask: () => void;
  clearError: () => void;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  currentTask: null,
  isLoading: false,
  isCreating: false,
  error: null,

  fetchTasks: async () => {
    // 使用api.ts中的配置，避免循环依赖
    const { token } = useAuthStore.getState();
    
    if (!token) {
      return;
    }
    
    set({ isLoading: true, error: null });
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || '获取任务列表失败');
      }
      
      set({
        tasks: data.items || [],
        isLoading: false,
        error: null,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '获取任务列表失败',
      });
    }
  },

  fetchTask: async (id: string) => {
    const { token } = useAuthStore.getState();
    
    if (!token) {
      return;
    }
    
    set({ isLoading: true, error: null });
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || '获取任务详情失败');
      }
      
      set({
        currentTask: data,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '获取任务详情失败',
      });
    }
  },

  createTask: async (taskData) => {
    const { token } = useAuthStore.getState();
    
    if (!token) {
      throw new Error('未登录');
    }
    
    set({ isCreating: true, error: null });
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(taskData),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || '创建任务失败');
      }
      
      // 添加到任务列表
      set({
        tasks: [data, ...get().tasks],
        currentTask: data,
        isCreating: false,
        error: null,
      });
      
      return data;
    } catch (error) {
      set({
        isCreating: false,
        error: error instanceof Error ? error.message : '创建任务失败',
      });
      throw error;
    }
  },

  updateTask: (id: string, updates: Partial<Task>) => {
    set({
      tasks: get().tasks.map(task =>
        task.id === id ? { ...task, ...updates } as Task : task
      ),
      currentTask: get().currentTask?.id === id
        ? { ...get().currentTask, ...updates } as Task
        : get().currentTask,
    });
  },

  clearCurrentTask: () => {
    set({ currentTask: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));

// 模型状态
interface Model {
  id: string;
  name: string;
  description: string;
  type: 'detection' | 'classification' | 'segmentation';
  version: string;
  accuracy: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  metadata?: any;
}

interface ModelState {
  models: Model[];
  currentModel: Model | null;
  isLoading: boolean;
  error: string | null;
  
  // 操作
  fetchModels: () => Promise<void>;
  fetchModel: (id: string) => Promise<void>;
  selectModel: (model: Model) => void;
  clearCurrentModel: () => void;
  clearError: () => void;
}

export const useModelStore = create<ModelState>((set, get) => ({
  models: [],
  currentModel: null,
  isLoading: false,
  error: null,

  fetchModels: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await fetch(`${API_BASE_URL}/models`);
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || '获取模型列表失败');
      }
      
      set({
        models: data.items || [],
        isLoading: false,
        error: null,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '获取模型列表失败',
      });
    }
  },

  fetchModel: async (id: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await fetch(`${API_BASE_URL}/models/${id}`);
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || '获取模型详情失败');
      }
      
      set({
        currentModel: data,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '获取模型详情失败',
      });
    }
  },

  selectModel: (model: Model) => {
    set({ currentModel: model });
  },

  clearCurrentModel: () => {
    set({ currentModel: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));

// UI状态
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  language: 'zh' | 'en';
  
  // 操作
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  setLanguage: (language: 'zh' | 'en') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: false,
      theme: 'light',
      language: 'zh',

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      setSidebarOpen: (open: boolean) => {
        set({ sidebarOpen: open });
      },

      setTheme: (theme: 'light' | 'dark') => {
        set({ theme });
        // 应用主题到文档（仅在浏览器环境中）
        if (typeof window !== 'undefined') {
          if (theme === 'dark') {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        }
      },

      setLanguage: (language: 'zh' | 'en') => {
        set({ language });
      },
    }),
    {
      name: 'ui-storage',
    }
  )
);