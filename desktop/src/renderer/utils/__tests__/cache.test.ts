import { describe, it, expect, vi, beforeEach } from 'vitest';
import { addCachedResult, getCachedResults, getCachedResultById } from '../cache';
import type { CheckResponse } from '../../api';

// Mock window.api.store
const mockStore = {
  data: new Map<string, unknown>(),
  get: vi.fn(async (key: string) => mockStore.data.get(key)),
  set: vi.fn(async (key: string, value: unknown) => { mockStore.data.set(key, value); }),
};

beforeEach(() => {
  mockStore.data.clear();
});

describe('cache utility', () => {
  it('returns empty array when no cached results exist', async () => {
    // No store available (web mode)
    const results = await getCachedResults();
    expect(results).toEqual([]);
  });

  it('stores and retrieves cached results', async () => {
    (window as any).api = { store: mockStore };

    const mockResult = { report_id: 'abc', risk_score: 50 } as CheckResponse;
    await addCachedResult('test description', mockResult);

    const results = await getCachedResults();
    expect(results).toHaveLength(1);
    expect(results[0].description).toBe('test description');
    expect(results[0].result.risk_score).toBe(50);
  });

  it('finds cached result by id', async () => {
    (window as any).api = { store: mockStore };

    const mockResult = { report_id: 'abc', risk_score: 50 } as CheckResponse;
    await addCachedResult('test', mockResult);

    const results = await getCachedResults();
    const found = results[0];
    const byId = await getCachedResultById(found.id);
    expect(byId).toBeDefined();
    expect(byId!.description).toBe('test');
  });

  it('limits cache size to 50', async () => {
    (window as any).api = { store: mockStore };

    for (let i = 0; i < 60; i++) {
      await addCachedResult(`desc ${i}`, { report_id: `id${i}`, risk_score: i } as unknown as CheckResponse);
    }

    const results = await getCachedResults();
    expect(results).toHaveLength(50);
    expect(results[0].description).toBe('desc 59'); // newest first
    expect(results[49].description).toBe('desc 10'); // oldest retained
  });

  it('handles missing store gracefully (web mode)', async () => {
    delete (window as any).api;
    const results = await getCachedResults();
    expect(results).toEqual([]);

    // Should not throw
    await addCachedResult('test', {} as CheckResponse);
  });
});
