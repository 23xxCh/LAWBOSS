import axios from 'axios';
import { message } from 'antd';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动注入 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('crossguard_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 全局错误拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail || '请求失败';
      if (status === 401) {
        // Token 过期或无效，清除登录状态
        localStorage.removeItem('crossguard_token');
        localStorage.removeItem('crossguard_user');
        // 避免在登录页重复提示
        if (!window.location.pathname.includes('/login')) {
          message.warning('登录已过期，请重新登录');
          window.location.href = '/login';
        }
      } else if (status === 400) {
        message.warning(detail);
      } else if (status === 404) {
        message.error('资源不存在');
      } else if (status === 403) {
        message.error('权限不足');
      } else {
        message.error(`请求错误 (${status}): ${detail}`);
      }
    } else if (error.request) {
      message.error('网络错误，请检查后端服务是否启动');
    } else {
      message.error('请求配置错误');
    }
    return Promise.reject(error);
  }
);

export default api;
