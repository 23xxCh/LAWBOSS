import { useState, useEffect } from 'react';
import { Card, Input, Button, Space, Typography, Tag, Divider, message, Select, Popconfirm, Spin, Switch } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ApiOutlined, RobotOutlined, KeyOutlined, DeleteOutlined, SunOutlined, MoonOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { updateBaseURL } from '../api/client';
import { getLLMProviders, getLLMConfig, saveLLMConfig, deleteLLMConfig, testLLMConnection, type LLMProviderInfo } from '../api';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { useTheme } from '../contexts/ThemeContext';

const { Text, Title } = Typography;

export default function PreferencesPage() {
  const { t } = useTranslation();
  const { isDark, toggleTheme } = useTheme();
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem('crossguard_api_base') || 'http://127.0.0.1:8000');
  const [pingLoading, setPingLoading] = useState(false);
  const [pingResult, setPingResult] = useState<'success' | 'error' | null>(null);
  const [appVersion, setAppVersion] = useState('');
  const isWebMode = !(window as any).api;

  // LLM 配置状态
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [llmProvider, setLlmProvider] = useState('openai');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmApiBase, setLlmApiBase] = useState('https://api.openai.com/v1');
  const [llmModel, setLlmModel] = useState('gpt-4o-mini');
  const [llmConfigExists, setLlmConfigExists] = useState(false);
  const [llmTesting, setLlmTesting] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<'success' | 'error' | null>(null);
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmLoading, setLlmLoading] = useState(true);

  useEffect(() => {
    (window as any).api?.app?.getVersion?.().then(setAppVersion).catch(() => {});
  }, []);

  useEffect(() => {
    getLLMProviders()
      .then(setProviders)
      .catch(() => {})
      .finally(() => loadExistingConfig());
  }, []);

  function loadExistingConfig() {
    getLLMConfig()
      .then(config => {
        setLlmProvider(config.provider);
        setLlmApiKey('');
        setLlmApiBase(config.api_base);
        setLlmModel(config.model);
        setLlmConfigExists(true);
      })
      .catch(() => {
        setLlmConfigExists(false);
      })
      .finally(() => setLlmLoading(false));
  }

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

  const handleProviderChange = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId);
    if (provider) {
      setLlmProvider(providerId);
      setLlmApiBase(provider.default_api_base);
      if (provider.default_model) setLlmModel(provider.default_model);
    }
    setLlmTestResult(null);
  };

  const handleLLMTest = async () => {
    setLlmTesting(true);
    setLlmTestResult(null);
    try {
      const result = await testLLMConnection({
        provider: llmProvider,
        api_key: llmApiKey,
        api_base: llmApiBase,
        model: llmModel,
      });
      if (result.success) {
        setLlmTestResult('success');
        message.success(`${t('llm.test_success')} (${result.latency_ms}ms)`);
      } else {
        setLlmTestResult('error');
        message.error(`${t('llm.test_failure')}: ${result.message}`);
      }
    } catch {
      setLlmTestResult('error');
      message.error(t('llm.test_failure'));
    } finally {
      setLlmTesting(false);
    }
  };

  const handleLLMSave = async () => {
    setLlmSaving(true);
    try {
      await saveLLMConfig({
        provider: llmProvider,
        api_key: llmApiKey,
        api_base: llmApiBase,
        model: llmModel,
      });
      message.success(t('llm.save_success'));
      setLlmConfigExists(true);
    } catch (e: any) {
      message.error(e.response?.data?.detail || t('llm.save_failure'));
    } finally {
      setLlmSaving(false);
    }
  };

  const handleLLMDelete = async () => {
    try {
      await deleteLLMConfig();
      message.success('LLM 配置已删除');
      setLlmConfigExists(false);
      setLlmApiKey('');
      const defaultP = providers.find(p => p.id === 'openai');
      if (defaultP) {
        setLlmProvider('openai');
        setLlmApiBase(defaultP.default_api_base);
        setLlmModel(defaultP.default_model);
      }
    } catch (e: any) {
      message.error(e.response?.data?.detail || '删除失败');
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

      {/* LLM 配置卡片 */}
      <Card title={<><RobotOutlined /> AI 模型配置</>} style={{ marginBottom: 16 }}>
        <Spin spinning={llmLoading}>
          <Space orientation="vertical" style={{ width: '100%' }} size="middle">
            <Text type="secondary">配置 AI 语义检测使用的语言模型。配置后将自动启用 AI 深度检测。</Text>

            <div>
              <Text strong>模型提供商</Text>
              <Select
                value={llmProvider}
                onChange={handleProviderChange}
                style={{ width: '100%', marginTop: 4 }}
                options={providers.map(p => ({ label: p.name, value: p.id }))}
              />
            </div>

            <div>
              <Text strong>API 密钥</Text>
              <Input.Password
                value={llmApiKey}
                onChange={e => { setLlmApiKey(e.target.value); setLlmTestResult(null); }}
                placeholder={llmConfigExists ? '密钥已配置，如需更换请重新输入' : '输入 API 密钥'}
                style={{ width: '100%', marginTop: 4 }}
              />
            </div>

            <div>
              <Text strong>API 地址</Text>
              <Input
                value={llmApiBase}
                onChange={e => { setLlmApiBase(e.target.value); setLlmTestResult(null); }}
                placeholder="https://api.openai.com/v1"
                style={{ width: '100%', marginTop: 4 }}
              />
            </div>

            <div>
              <Text strong>模型名称</Text>
              <Select
                value={llmModel}
                onChange={setLlmModel}
                style={{ width: '100%', marginTop: 4 }}
                options={
                  (providers.find(p => p.id === llmProvider)?.models || []).map(m => ({ label: m, value: m }))
                }
              />
            </div>

            <Divider style={{ margin: '12px 0' }} />

            <Space>
              <Button onClick={handleLLMTest} loading={llmTesting} icon={<ApiOutlined />}>
                {llmTesting ? '测试中...' : '测试连接'}
              </Button>
              <Button type="primary" onClick={handleLLMSave} loading={llmSaving} icon={<KeyOutlined />}>
                {llmSaving ? '保存中...' : '保存配置'}
              </Button>
              {llmConfigExists && (
                <Popconfirm title="确定删除 AI 模型配置？删除后将恢复为环境变量配置。" onConfirm={handleLLMDelete}>
                  <Button danger icon={<DeleteOutlined />}>删除配置</Button>
                </Popconfirm>
              )}
            </Space>

            {llmTestResult === 'success' && <Tag icon={<CheckCircleOutlined />} color="success">连接正常</Tag>}
            {llmTestResult === 'error' && <Tag icon={<CloseCircleOutlined />} color="error">连接失败</Tag>}
          </Space>
        </Spin>
      </Card>

      <Card title="语言" style={{ marginBottom: 16 }}>
        <LanguageSwitcher />
      </Card>

      <Card title="主题" style={{ marginBottom: 16 }}>
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Space>
              {isDark ? <MoonOutlined style={{ fontSize: 18 }} /> : <SunOutlined style={{ fontSize: 18 }} />}
              <Text>{isDark ? '深色模式' : '亮色模式'}</Text>
            </Space>
            <Switch
              checked={isDark}
              onChange={toggleTheme}
              checkedChildren={<MoonOutlined />}
              unCheckedChildren={<SunOutlined />}
            />
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>切换应用主题，更改后立即生效。</Text>
        </Space>
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
