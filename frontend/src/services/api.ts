import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// API Base URL - uses the same backend as web app
const API_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://dribble-order-sync.preview.emergentagent.com';

// Create axios instance
const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token storage - use AsyncStorage for web, SecureStore for native
const TOKEN_KEY = 'auth_token';

export const setAuthToken = async (token: string) => {
  if (Platform.OS === 'web') {
    await AsyncStorage.setItem(TOKEN_KEY, token);
  } else {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  }
};

export const getAuthToken = async (): Promise<string | null> => {
  if (Platform.OS === 'web') {
    return await AsyncStorage.getItem(TOKEN_KEY);
  } else {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  }
};

export const removeAuthToken = async () => {
  if (Platform.OS === 'web') {
    await AsyncStorage.removeItem(TOKEN_KEY);
  } else {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }
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

// Orders API - Synced with DRIBBLE-NEW-2026
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
  
  // Changed from PATCH to PUT to match new backend
  updateOrderStatus: async (orderId: string, status: string) => {
    const response = await api.put(`/admin/orders/${orderId}/status`, { status });
    return response.data;
  },
  
  // New cancel order endpoint from DRIBBLE-NEW-2026
  cancelOrder: async (orderId: string, reason?: string) => {
    const response = await api.post(`/admin/orders/${orderId}/cancel`, { reason });
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
