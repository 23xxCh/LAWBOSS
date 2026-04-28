import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import HomePage from '../HomePage';

// Mock API
vi.mock('../../api', () => ({
  getMarkets: vi.fn().mockResolvedValue([
    { code: 'EU', name: '欧盟', categories: ['化妆品', '电子产品'] },
    { code: 'US', name: '美国', categories: ['化妆品'] },
  ]),
}));

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider>
      <BrowserRouter>{children}</BrowserRouter>
    </ConfigProvider>
  );
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading skeleton on mount', () => {
    render(<HomePage />, { wrapper: Wrapper });
    // Skeleton should be visible while loading
    expect(document.querySelector('.ant-skeleton')).toBeTruthy();
  });

  it('renders 3 navigation cards after loading', async () => {
    render(<HomePage />, { wrapper: Wrapper });

    // Wait for loading to finish
    const checkText = await screen.findByText('检测历史', {}, { timeout: 3000 });
    expect(checkText).toBeTruthy();

    expect(screen.getByText('数据看板')).toBeTruthy();
    expect(screen.getByText('合规规则')).toBeTruthy();
  });

  it('renders quick check form with market selectors', async () => {
    render(<HomePage />, { wrapper: Wrapper });

    const formTitle = await screen.findByText('快速合规检测', {}, { timeout: 3000 });
    expect(formTitle).toBeTruthy();

    expect(screen.getByPlaceholderText(/请输入产品描述/)).toBeTruthy();
    expect(screen.getByText('开始检测')).toBeTruthy();
  });

  it('has disabled check button when description is empty', async () => {
    render(<HomePage />, { wrapper: Wrapper });

    const button = await screen.findByText('开始检测', {}, { timeout: 3000 });
    expect(button.closest('button')).toBeDisabled();
  });

  it('shows error state when API fails', async () => {
    const api = await import('../../api');
    (api.getMarkets as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('API error'));

    render(<HomePage />, { wrapper: Wrapper });

    const errorText = await screen.findByText('无法连接后端服务', {}, { timeout: 3000 });
    expect(errorText).toBeTruthy();
  });
});
