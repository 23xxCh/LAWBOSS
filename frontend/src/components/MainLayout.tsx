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

const { Header, Content, Footer } = Layout;

const menuItems = [
  { key: '/check', icon: <SafetyCertificateOutlined />, label: '合规检测' },
  { key: '/batch', icon: <ThunderboltOutlined />, label: '批量检测' },
  { key: '/reports', icon: <HistoryOutlined />, label: '检测历史' },
  { key: '/rules', icon: <BookOutlined />, label: '法规查询' },
  { key: '/dashboard', icon: <DashboardOutlined />, label: '数据看板' },
];

export default function MainLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin, clearAuth } = useAuth();

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
        出海法盾 CrossGuard v0.2.0 — 跨境电商智能合规审查平台
      </Footer>
    </Layout>
  );
}
