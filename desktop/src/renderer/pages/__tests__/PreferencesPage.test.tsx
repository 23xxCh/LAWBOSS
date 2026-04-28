import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import PreferencesPage from '../PreferencesPage';
import * as client from '../../api/client';

// Mock axios for ping test
vi.mock('axios', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: {} }),
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
    expect(screen.getByText('API 地址')).toBeTruthy();
    expect(screen.getByText('语言')).toBeTruthy();
    expect(screen.getByText('主题')).toBeTruthy();
    expect(screen.getByText('关于')).toBeTruthy();
  });

  it('shows save and ping buttons for API address', () => {
    render(<PreferencesPage />, { wrapper: Wrapper });
    expect(screen.getByText('测试连接')).toBeTruthy();
    expect(screen.getByText('保存')).toBeTruthy();
  });

  it('renders language switcher component', () => {
    render(<PreferencesPage />, { wrapper: Wrapper });
    expect(screen.getByTestId('language-switcher')).toBeTruthy();
  });

  it('calls updateBaseURL on save', () => {
    const updateSpy = vi.spyOn(client, 'updateBaseURL');
    render(<PreferencesPage />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText('保存'));
    expect(updateSpy).toHaveBeenCalledWith('http://127.0.0.1:8000');
  });

  it('disables API address editing in web mode', () => {
    // Ensure no window.api so it's web mode
    delete (window as any).api;
    render(<PreferencesPage />, { wrapper: Wrapper });

    const input = screen.getByDisplayValue('http://127.0.0.1:8000') as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });
});
