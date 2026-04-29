import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import PreferencesPage from '../PreferencesPage';

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: {} }),
    create: vi.fn(() => ({
      get: vi.fn().mockResolvedValue({ data: {} }),
      post: vi.fn().mockResolvedValue({ data: {} }),
      put: vi.fn().mockResolvedValue({ data: {} }),
      delete: vi.fn().mockResolvedValue({ data: {} }),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}));

// Mock LanguageSwitcher
vi.mock('../../components/LanguageSwitcher', () => ({
  default: () => <div data-testid="language-switcher">LanguageSwitcher</div>,
}));

describe('PreferencesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    delete (window as any).api;
  });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <ConfigProvider>{children}</ConfigProvider>;
  }

  it('renders API address input with default value', () => {
    render(<PreferencesPage />, { wrapper: Wrapper });
    const input = screen.getByDisplayValue('http://127.0.0.1:8000');
    expect(input).toBeTruthy();
  });

  it('renders all preference sections', () => {
    render(<PreferencesPage />, { wrapper: Wrapper });
    // Use getAllByText since text appears multiple times
    expect(screen.getAllByText('API 地址').length).toBeGreaterThan(0);
    expect(screen.getAllByText('语言').length).toBeGreaterThan(0);
    expect(screen.getAllByText('主题').length).toBeGreaterThan(0);
    expect(screen.getAllByText('关于').length).toBeGreaterThan(0);
  });

  it('shows test connection button', () => {
    render(<PreferencesPage />, { wrapper: Wrapper });
    expect(screen.getAllByText('测试连接').length).toBeGreaterThan(0);
  });

  it('renders language switcher component', () => {
    render(<PreferencesPage />, { wrapper: Wrapper });
    expect(screen.getByTestId('language-switcher')).toBeTruthy();
  });

  it('disables API address editing in web mode', () => {
    render(<PreferencesPage />, { wrapper: Wrapper });
    const input = screen.getByDisplayValue('http://127.0.0.1:8000') as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });
});
