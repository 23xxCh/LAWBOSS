import type { CheckResponse } from '../api';

const CACHE_KEY = 'detection_cache';
const MAX_CACHE_SIZE = 50;

export interface CachedItem {
  id: string;
  description: string;
  result: CheckResponse;
  created_at: string;
}

async function getStore(): Promise<{ get: (k: string) => Promise<unknown>; set: (k: string, v: unknown) => Promise<void> } | null> {
  const api = (window as any).api;
  return api?.store || null;
}

export async function getCachedResults(): Promise<CachedItem[]> {
  const store = await getStore();
  if (!store) return [];
  try {
    return (await store.get(CACHE_KEY)) || [];
  } catch {
    return [];
  }
}

export async function addCachedResult(description: string, result: CheckResponse): Promise<void> {
  const store = await getStore();
  if (!store) return;
  try {
    const cached = (await store.get(CACHE_KEY)) || [];
    cached.unshift({
      id: crypto.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
      description,
      result,
      created_at: new Date().toISOString(),
    });
    if (cached.length > MAX_CACHE_SIZE) cached.length = MAX_CACHE_SIZE;
    await store.set(CACHE_KEY, cached);
  } catch {
    // cache failure should not affect main flow
  }
}

export async function getCachedResultById(id: string): Promise<CachedItem | undefined> {
  const cached = await getCachedResults();
  return cached.find((c) => c.id === id);
}
