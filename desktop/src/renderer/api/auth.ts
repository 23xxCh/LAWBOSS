/**
 * 认证状态管理 — Token 持久化 + 用户信息
 */
import { useState, useCallback, useEffect } from 'react';
import type { UserInfo } from './api';

const TOKEN_KEY = 'crossguard_token';
const USER_KEY = 'crossguard_user';

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUserState] = useState<UserInfo | null>(() => {
    const stored = localStorage.getItem(USER_KEY);
    return stored ? JSON.parse(stored) : null;
  });

  const setAuth = useCallback((newToken: string, newUser: UserInfo) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
    setTokenState(newToken);
    setUserState(newUser);
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setTokenState(null);
    setUserState(null);
  }, []);

  const isLoggedIn = !!token && !!user;
  const isAdmin = user?.role === 'admin';

  return { token, user, isLoggedIn, isAdmin, setAuth, clearAuth };
}
