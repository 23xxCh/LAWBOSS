import { useState, useEffect } from 'react';
import { Card, Input, Button, Space, Typography, Tag, Divider, message, Select } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ApiOutlined } from '@ant-design/icons';
import axios from 'axios';
import { updateBaseURL } from '../api/client';
import LanguageSwitcher from '../components/LanguageSwitcher';

const { Text, Title } = Typography;

export default function PreferencesPage() {
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem('crossguard_api_base') || 'http://127.0.0.1:8000');
  const [pingLoading, setPingLoading] = useState(false);
  const [pingResult, setPingResult] = useState<'success' | 'error' | null>(null);
  const [appVersion, setAppVersion] = useState('');
  const isWebMode = !(window as any).api;

  useEffect(() => {
    (window as any).api?.app?.getVersion?.().then(setAppVersion).catch(() => {});
  }, []);

  const handleApiUrlChange = (value: string) => {
    setApiUrl(value);
    setPingResult(null);
  };

  const handleSaveApiUrl = () => {
    updateBaseURL(apiUrl);
    message.success('API 地址已更新');
  };

  const handlePing = async () => {
    setPingLoading(true);
    setPingResult(null);
    try {
      await axios.get(apiUrl + '/api/v1/', { timeout: 5000 });
      setPingResult('success');
      message.success('连接成功');
    } catch {
      setPingResult('error');
      message.error('连接失败，请检查地址');
    } finally {
      setPingLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '24px 16px' }}>
      <Title level={3}>设置</Title>

      <Card title={<><ApiOutlined /> API 地址</>} style={{ marginBottom: 16 }}>
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
          <Text type="secondary">后端服务地址，修改后立即生效，无需重启。</Text>
          <Space style={{ width: '100%' }}>
            <Input
              value={apiUrl}
              onChange={(e) => handleApiUrlChange(e.target.value)}
              placeholder="http://127.0.0.1:8000"
              disabled={isWebMode}
              style={{ width: 320 }}
            />
            <Button onClick={handlePing} loading={pingLoading}>
              测试连接
            </Button>
            <Button type="primary" onClick={handleSaveApiUrl} disabled={isWebMode}>
              保存
            </Button>
            {pingResult === 'success' && <Tag icon={<CheckCircleOutlined />} color="success">连接正常</Tag>}
            {pingResult === 'error' && <Tag icon={<CloseCircleOutlined />} color="error">连接失败</Tag>}
          </Space>
          {isWebMode && (
            <Text type="warning" style={{ fontSize: 12 }}>
              Web 模式下 API 地址由 Vite 代理固定，不可修改。
            </Text>
          )}
        </Space>
      </Card>

      <Card title="语言" style={{ marginBottom: 16 }}>
        <LanguageSwitcher />
      </Card>

      <Card title="主题" style={{ marginBottom: 16 }}>
        <Text>当前模式：亮色模式</Text>
        <br />
        <Text type="secondary" style={{ fontSize: 12 }}>深色模式将在后续版本支持。</Text>
      </Card>

      <Card title="关于" style={{ marginBottom: 16 }}>
        <Space orientation="vertical">
          <Text>应用名称：出海法盾 CrossGuard</Text>
          <Text>应用版本：{appVersion || '-'}</Text>
        </Space>
      </Card>
    </div>
  );
}
