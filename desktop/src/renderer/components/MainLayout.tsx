import type { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Dropdown, Avatar, Space, Tag } from 'antd';
import {
  SafetyCertificateOutlined,
  HistoryOutlined,
  BookOutlined,
  ThunderboltOutlined,
  UserOutlined,
  LogoutOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { useAuth } from '../api/auth';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from './LanguageSwitcher';

const { Header, Content, Footer } = Layout;

export default function MainLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin, clearAuth } = useAuth();
  const { t } = useTranslation();

  const menuItems = [
    { key: '/check', icon: <SafetyCertificateOutlined />, label: t('nav.check') },
    { key: '/batch', icon: <ThunderboltOutlined />, label: t('nav.batch') },
    { key: '/reports', icon: <HistoryOutlined />, label: t('nav.reports') },
    { key: '/rules', icon: <BookOutlined />, label: t('nav.rules') },
    { key: '/dashboard', icon: <DashboardOutlined />, label: t('nav.dashboard') },
  ];

  const selectedKey = menuItems.find((item) =>
    location.pathname.startsWith(item.key)
  )?.key || '/check';

  const handleLogout = () => {
    clearAuth();
    navigate('/login', { replace: true });
  };

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: `${user?.username || '用户'} (${user?.role || '-'})` },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div
          style={{
            color: '#fff',
            fontSize: 18,
            fontWeight: 'bold',
            marginRight: 40,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
          onClick={() => navigate('/')}
        >
          出海法盾 CrossGuard
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1 }}
        />
        <div style={{ marginRight: 16 }}>
          <LanguageSwitcher />
        </div>
        <Dropdown
          menu={{
            items: userMenuItems,
            onClick: ({ key }) => {
              if (key === 'logout') handleLogout();
            },
          }}
          placement="bottomRight"
        >
          <Space style={{ cursor: 'pointer', marginLeft: 16 }}>
            <Avatar icon={<UserOutlined />} style={{ backgroundColor: isAdmin ? '#ff4d4f' : '#1890ff' }} />
            <span style={{ color: '#fff' }}>{user?.username}</span>
            {isAdmin && <Tag color="red" style={{ marginRight: 0 }}>管理员</Tag>}
          </Space>
        </Dropdown>
      </Header>
      <Content style={{ background: '#f5f5f5' }}>
        {children}
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        {t('app.title')} v0.2.0 — {t('app.subtitle')}
      </Footer>
    </Layout>
  );
}
