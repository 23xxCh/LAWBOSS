import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Input, Select, Button, Space, Typography, Skeleton, Alert, message } from 'antd';
import { SearchOutlined, HistoryOutlined, DashboardOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { getMarkets, type MarketResponse } from '../api';

const { TextArea } = Input;
const { Title, Paragraph } = Typography;

export default function HomePage() {
  const navigate = useNavigate();
  const [markets, setMarkets] = useState<MarketResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [market, setMarket] = useState('EU');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    getMarkets()
      .then((data) => {
        setMarkets(data);
        if (data.length > 0) {
          setMarket(data[0].code);
          setCategory(data[0].categories[0] || '');
        }
      })
      .catch(() => {
        setError(true);
        message.error('无法连接后端服务');
      })
      .finally(() => setLoading(false));
  }, []);

  const currentMarket = markets.find((m) => m.code === market);
  const categories = currentMarket?.categories || [];

  const handleCheck = () => {
    if (!description.trim()) return;
    navigate('/check', { state: { description, market, category } });
  };

  if (loading) {
    return (
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '40px 16px' }}>
        <Skeleton active paragraph={{ rows: 1 }} title={{ width: '60%' }} />
        <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
          {[1, 2, 3].map((i) => (
            <Col span={8} key={i}>
              <Card><Skeleton active /></Card>
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '40px 16px' }}>
        <Alert
          type="error"
          message="无法连接后端服务"
          description="请确认后端已启动，或检查 API 地址配置。"
          showIcon
          action={
            <Button onClick={() => window.location.reload()}>重试</Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '40px 16px' }}>
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <Title level={2}>
          <SafetyCertificateOutlined style={{ marginRight: 8 }} />
          出海法盾 CrossGuard
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 16 }}>
          跨境电商智能合规检测工具 — 支持欧盟、美国、东南亚多市场法规
        </Paragraph>
      </div>

      <Card style={{ marginBottom: 32 }}>
        <Title level={4}><SearchOutlined /> 快速合规检测</Title>
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
          <Space wrap>
            <span>目标市场：</span>
            <Select
              value={market}
              onChange={(v) => {
                setMarket(v);
                const m = markets.find((mk) => mk.code === v);
                setCategory(m?.categories[0] || '');
              }}
              style={{ width: 140 }}
              options={markets.map((m) => ({ value: m.code, label: m.name }))}
            />
            <span>产品类别：</span>
            <Select
              value={category}
              onChange={setCategory}
              style={{ width: 140 }}
              options={categories.map((c) => ({ value: c, label: c }))}
            />
          </Space>
          <TextArea
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="请输入产品描述，例如：这款面霜能治疗痘痘，7天见效，是市面上最好的产品"
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            size="large"
            block
            disabled={!description.trim()}
            onClick={handleCheck}
          >
            开始检测
          </Button>
        </Space>
      </Card>

      <Row gutter={[24, 24]}>
        <Col span={8}>
          <Card
            hoverable
            onClick={() => navigate('/reports')}
          >
            <Space orientation="vertical" style={{ width: '100%', textAlign: 'center' }}>
              <HistoryOutlined style={{ fontSize: 36, color: '#1890ff' }} />
              <Title level={4}>检测历史</Title>
              <Paragraph type="secondary">查看所有合规检测记录和报告详情</Paragraph>
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card
            hoverable
            onClick={() => navigate('/dashboard')}
          >
            <Space orientation="vertical" style={{ width: '100%', textAlign: 'center' }}>
              <DashboardOutlined style={{ fontSize: 36, color: '#52c41a' }} />
              <Title level={4}>数据看板</Title>
              <Paragraph type="secondary">数据飞轮、检测统计、平台巡检概览</Paragraph>
            </Space>
          </Card>
        </Col>
        <Col span={8}>
          <Card
            hoverable
            onClick={() => navigate('/rules')}
          >
            <Space orientation="vertical" style={{ width: '100%', textAlign: 'center' }}>
              <SafetyCertificateOutlined style={{ fontSize: 36, color: '#722ed1' }} />
              <Title level={4}>合规规则</Title>
              <Paragraph type="secondary">查看各市场的法规要求和合规细则</Paragraph>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
