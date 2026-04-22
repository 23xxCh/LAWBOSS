import { useState } from 'react';
import { Card, Form, Input, Button, Typography, Space, Alert, message } from 'antd';
import { SafetyCertificateOutlined, UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { login, type LoginRequest } from '../api';
import { useAuth } from '../api/auth';

const { Title, Text, Paragraph } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setAuth } = useAuth();

  const handleLogin = async (values: LoginRequest) => {
    setLoading(true);
    setError(null);
    try {
      const res = await login(values);
      setAuth(res.access_token, res.user);
      message.success(`欢迎回来，${res.user.username}`);
      navigate('/check', { replace: true });
    } catch (e: unknown) {
      setError('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <Card style={{ width: 420, borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ textAlign: 'center' }}>
            <SafetyCertificateOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            <Title level={3} style={{ marginTop: 12, marginBottom: 4 }}>出海法盾 CrossGuard</Title>
            <Text type="secondary">跨境电商智能合规审查平台</Text>
          </div>

          {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}

          <Form<LoginRequest>
            onFinish={handleLogin}
            autoComplete="off"
            size="large"
          >
            <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block size="large">
                登录
              </Button>
            </Form.Item>
          </Form>

          <Paragraph type="secondary" style={{ textAlign: 'center', fontSize: 12, marginBottom: 0 }}>
            没有账户？<a onClick={() => navigate('/register')}>立即注册</a>
          </Paragraph>
        </Space>
      </Card>
    </div>
  );
}
