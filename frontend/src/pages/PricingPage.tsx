import React from 'react';
import { Card, Button, Typography, Space, Tag, List } from 'antd';
import { CheckOutlined, CrownOutlined, RocketOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const { Title, Text, Paragraph } = Typography;

interface PricingPlan {
  key: string;
  name: string;
  price: string;
  period: string;
  checks: number;
  markets: number;
  patrolSkus: number;
  apiCalls: number;
  features: string[];
  highlight?: boolean;
  ctaText: string;
}

const plans: PricingPlan[] = [
  {
    key: 'free',
    name: '免费版',
    price: '$0',
    period: '/月',
    checks: 50,
    markets: 1,
    patrolSkus: 0,
    apiCalls: 0,
    features: ['基础合规检测', '1 个目标市场', '检测历史记录'],
    ctaText: '当前方案',
  },
  {
    key: 'pro',
    name: '专业版',
    price: '$49',
    period: '/月',
    checks: 500,
    markets: 5,
    patrolSkus: 50,
    apiCalls: 500,
    features: [
      '500 次/月检测',
      '5 个目标市场',
      '实时巡检 (50 SKU)',
      '法规变更推送',
      'API 调用 500 次/月',
    ],
    highlight: true,
    ctaText: '开始订阅',
  },
  {
    key: 'enterprise',
    name: '企业版',
    price: '$199',
    period: '/月',
    checks: 2000,
    markets: 5,
    patrolSkus: 200,
    apiCalls: 2000,
    features: [
      '2000 次/月检测',
      '5 个目标市场',
      '实时巡检 (200 SKU)',
      '智能修复建议',
      'API 调用 2000 次/月',
      '优先技术支持',
    ],
    ctaText: '开始订阅',
  },
];

const PricingPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleSubscribe = (tier: string) => {
    // 跳转到订阅流程
    navigate(`/billing?tier=${tier}`);
  };

  return (
    <div style={{ padding: '40px 24px', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <Title level={2}>选择适合您的方案</Title>
        <Paragraph type="secondary">
          从免费版开始，随时升级获取更多功能
        </Paragraph>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: 24,
        }}
      >
        {plans.map((plan) => (
          <Card
            key={plan.key}
            style={{
              borderColor: plan.highlight ? '#1890ff' : undefined,
              position: 'relative',
            }}
          >
            {plan.highlight && (
              <Tag
                color="blue"
                style={{ position: 'absolute', top: -8, left: 16 }}
              >
                推荐
              </Tag>
            )}

            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                <Title level={4}>
                  {plan.key === 'enterprise' && <CrownOutlined />}{' '}
                  {plan.key === 'pro' && <RocketOutlined />}{' '}
                  {plan.name}
                </Title>
                <div>
                  <Text style={{ fontSize: 32, fontWeight: 'bold' }}>
                    {plan.price}
                  </Text>
                  <Text type="secondary">{plan.period}</Text>
                </div>
              </div>

              <List
                dataSource={plan.features}
                renderItem={(item) => (
                  <List.Item style={{ border: 'none', padding: '8px 0' }}>
                    <CheckOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                    <Text>{item}</Text>
                  </List.Item>
                )}
              />

              <Button
                type={plan.highlight ? 'primary' : 'default'}
                block
                size="large"
                onClick={() => handleSubscribe(plan.key)}
                disabled={plan.key === 'free'}
              >
                {plan.ctaText}
              </Button>
            </Space>
          </Card>
        ))}
      </div>

      <div style={{ marginTop: 48, textAlign: 'center' }}>
        <Paragraph type="secondary">
          所有方案均支持 14 天免费试用 · 随时可取消 · 无隐藏费用
        </Paragraph>
      </div>
    </div>
  );
};

export default PricingPage;
