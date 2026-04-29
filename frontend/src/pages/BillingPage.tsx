import React, { useEffect, useState } from 'react';
import { Card, Typography, Button, Progress, Space, Tag, Descriptions, Spin, Alert } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, SyncOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;

interface SubscriptionInfo {
  status: string;
  tier: string;
  trial_ends_at: string | null;
  quota_checks_monthly: number;
  quota_used: number;
}

const statusConfig: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
  free: { color: 'default', text: '免费版', icon: null },
  trialing: { color: 'processing', text: '试用中', icon: <SyncOutlined spin /> },
  active: { color: 'success', text: '已激活', icon: <CheckCircleOutlined /> },
  past_due: { color: 'warning', text: '支付逾期', icon: <CloseCircleOutlined /> },
  canceled: { color: 'error', text: '已取消', icon: <CloseCircleOutlined /> },
};

const tierNames: Record<string, string> = {
  free: '免费版',
  pro: '专业版 ($49/月)',
  enterprise: '企业版 ($199/月)',
};

const BillingPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const tier = searchParams.get('tier');

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const response = await axios.get('/api/v1/billing/subscription');
      setSubscription(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取订阅信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (selectedTier: string) => {
    try {
      const response = await axios.post('/api/v1/billing/checkout', {
        tier: selectedTier,
        success_url: `${window.location.origin}/billing?success=true`,
        cancel_url: `${window.location.origin}/billing?canceled=true`,
      });

      // 重定向到 Stripe Checkout
      window.location.href = response.data.checkout_url;
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建支付会话失败');
    }
  };

  const handleStartTrial = async () => {
    try {
      await axios.post('/api/v1/billing/trial');
      fetchSubscription();
    } catch (err: any) {
      setError(err.response?.data?.detail || '开始试用失败');
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
        <Alert type="error" message={error} />
      </div>
    );
  }

  if (!subscription) {
    return null;
  }

  const statusInfo = statusConfig[subscription.status] || statusConfig.free;
  const usagePercent = Math.min(
    100,
    (subscription.quota_used / subscription.quota_checks_monthly) * 100
  );

  return (
    <div style={{ padding: '24px', maxWidth: 800, margin: '0 auto' }}>
      <Title level={3}>订阅管理</Title>

      <Card style={{ marginBottom: 24 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="订阅状态">
            <Tag color={statusInfo.color} icon={statusInfo.icon}>
              {statusInfo.text}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="当前方案">
            {tierNames[subscription.tier]}
          </Descriptions.Item>
          {subscription.trial_ends_at && (
            <Descriptions.Item label="试用结束时间">
              {new Date(subscription.trial_ends_at).toLocaleDateString()}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="配额使用情况" style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <Text>本月检测次数</Text>
            <Text>
              {subscription.quota_used} / {subscription.quota_checks_monthly}
            </Text>
          </div>
          <Progress
            percent={usagePercent}
            status={usagePercent >= 100 ? 'exception' : usagePercent >= 80 ? 'normal' : 'success'}
          />
        </div>

        {subscription.quota_used >= subscription.quota_checks_monthly && (
          <Alert
            type="warning"
            message="配额已用尽"
            description="您已用完本月检测配额，升级订阅以获取更多检测次数。"
            showIcon
          />
        )}
      </Card>

      {/* 订阅操作 */}
      {subscription.status === 'free' && (
        <Card>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Paragraph>
              升级到专业版或企业版，解锁更多功能。
            </Paragraph>
            <Space>
              <Button type="primary" onClick={() => handleSubscribe('pro')}>
                升级到专业版 ($49/月)
              </Button>
              <Button onClick={() => handleSubscribe('enterprise')}>
                升级到企业版 ($199/月)
              </Button>
            </Space>
          </Space>
        </Card>
      )}

      {subscription.status === 'trialing' && (
        <Card>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Alert
              type="info"
              message="试用期"
              description={`您的试用期将于 ${subscription.trial_ends_at ? new Date(subscription.trial_ends_at).toLocaleDateString() : '未知'} 结束。立即订阅以继续使用专业版功能。`}
            />
            <Space>
              <Button type="primary" onClick={() => handleSubscribe('pro')}>
                订阅专业版
              </Button>
              <Button onClick={() => handleSubscribe('enterprise')}>
                订阅企业版
              </Button>
            </Space>
          </Space>
        </Card>
      )}

      {subscription.status === 'active' && (
        <Card>
          <Button danger>取消订阅</Button>
        </Card>
      )}

      {subscription.status === 'past_due' && (
        <Card>
          <Alert
            type="error"
            message="支付逾期"
            description="您的订阅支付失败，请更新支付方式以继续使用专业版功能。"
            showIcon
          />
          <Button type="primary" style={{ marginTop: 16 }}>
            更新支付方式
          </Button>
        </Card>
      )}
    </div>
  );
};

export default BillingPage;
