import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// API Base URL - uses the same backend as web app
const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://appweb-sync.preview.emergentagent.com';

// Create axios instance
const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
export const setAuthToken = async (token: string) => {
  await SecureStore.setItemAsync('auth_token', token);
};

export const getAuthToken = async (): Promise<string | null> => {
  return await SecureStore.getItemAsync('auth_token');
};

export const removeAuthToken = async () => {
  await SecureStore.deleteItemAsync('auth_token');
};

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    const token = await getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear it
      await removeAuthToken();
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// Orders API
export const ordersAPI = {
  getOrders: async (params?: {
    status?: string;
    page?: number;
    limit?: number;
    search?: string;
  }) => {
    const response = await api.get('/admin/orders', { params });
    return response.data;
  },
  
  getOrder: async (orderId: string) => {
    const response = await api.get(`/orders/${orderId}`);
    return response.data;
  },
  
  updateOrderStatus: async (orderId: string, status: string) => {
    const response = await api.patch(`/admin/orders/${orderId}/status`, { status });
    return response.data;
  },
  
  getOrderStats: async () => {
    const response = await api.get('/admin/orders/stats');
    return response.data;
  },
};

// Push Notifications API
export const notificationsAPI = {
  registerPushToken: async (token: string, deviceInfo: any) => {
    const response = await api.post('/admin/push-tokens', {
      push_token: token,
      device_info: deviceInfo,
    });
    return response.data;
  },
  
  unregisterPushToken: async (token: string) => {
    const response = await api.delete('/admin/push-tokens', {
      data: { push_token: token },
    });
    return response.data;
  },
};

export default api;
