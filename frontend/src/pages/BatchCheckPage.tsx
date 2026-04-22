import { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Button,
  Tag,
  Space,
  Typography,
  Alert,
  Spin,
  Progress,
  Table,
  message,
} from 'antd';
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  batchCheckCompliance,
  getMarkets,
  type CheckRequest,
  type CheckResponse,
  type MarketResponse,
} from '../api';

const { Text, Paragraph } = Typography;

const riskLevelColor: Record<string, string> = {
  '高风险': 'red',
  '中风险': 'orange',
  '低风险': 'green',
};

export default function BatchCheckPage() {
  const [markets, setMarkets] = useState<MarketResponse[]>([]);
  const [market, setMarket] = useState<string>('EU');
  const [category, setCategory] = useState<string>('');
  const [descriptions, setDescriptions] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<CheckResponse[]>([]);
  const [summary, setSummary] = useState({ total: 0, high: 0, medium: 0, low: 0 });

  useEffect(() => {
    getMarkets().then((data) => {
      setMarkets(data);
      if (data.length > 0) {
        setMarket(data[0].code);
        setCategory(data[0].categories[0] || '');
      }
    });
  }, []);

  const currentMarket = markets.find((m) => m.code === market);
  const categories = currentMarket?.categories || [];

  const handleBatchCheck = async () => {
    const lines = descriptions.split('\n').filter((l) => l.trim());
    if (lines.length === 0) {
      message.warning('请输入至少一条产品描述');
      return;
    }
    if (lines.length > 100) {
      message.warning('单次批量检测最多 100 条');
      return;
    }

    const items: CheckRequest[] = lines.map((desc) => ({
      description: desc.trim(),
      category,
      market,
    }));

    setLoading(true);
    try {
      const res = await batchCheckCompliance({ items });
      setResults(res.results);
      setSummary({
        total: res.total,
        high: res.high_risk_count,
        medium: res.medium_risk_count,
        low: res.low_risk_count,
      });
      message.success(`批量检测完成：${res.total} 条`);
    } catch {
      message.error('批量检测失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '#',
      key: 'index',
      width: 50,
      render: (_: unknown, __: unknown, i: number) => i + 1,
    },
    {
      title: '风险评分',
      dataIndex: 'risk_score',
      key: 'risk_score',
      width: 100,
      render: (v: number) => <Text strong style={{ color: v >= 70 ? '#ff4d4f' : v >= 40 ? '#faad14' : '#52c41a' }}>{v}</Text>,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: (v: string) => <Tag color={riskLevelColor[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '违规数',
      key: 'violation_count',
      width: 80,
      render: (_: unknown, r: CheckResponse) => r.violations.length,
    },
    {
      title: '主要违规',
      key: 'top_violations',
      render: (_: unknown, r: CheckResponse) => {
        const types = [...new Set(r.violations.map((v) => v.type_label))];
        return types.length > 0
          ? types.slice(0, 3).map((t) => <Tag key={t}>{t}</Tag>)
          : <Tag color="green">合规</Tag>;
      },
    },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 16px' }}>
      <Card title={<span><ThunderboltOutlined /> 批量合规检测</span>} style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <span>目标市场：</span>
          <Select
            value={market}
            onChange={(v) => {
              setMarket(v);
              const m = markets.find((m) => m.code === v);
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
        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          每行输入一条产品描述，最多 100 条
        </Typography.Text>
        <Typography.TextArea
          rows={10}
          value={descriptions}
          onChange={(e) => setDescriptions(e.target.value)}
          placeholder={`这款面霜能治疗痘痘，7天见效\nA premium skincare product with natural ingredients\n美白精华，消除色斑，100%有效`}
          style={{ marginBottom: 16 }}
        />
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          loading={loading}
          onClick={handleBatchCheck}
          disabled={!descriptions.trim()}
          size="large"
          block
        >
          批量检测 ({descriptions.split('\n').filter((l) => l.trim()).length} 条)
        </Button>
      </Card>

      {loading && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="正在批量检测..." />
        </Card>
      )}

      {results.length > 0 && !loading && (
        <>
          <Card title="检测概览" style={{ marginBottom: 16 }}>
            <Space size="large">
              <div style={{ textAlign: 'center' }}>
                <Progress type="circle" percent={Math.round((summary.low / summary.total) * 100)} strokeColor="#52c41a" size={80} />
                <div><Text type="secondary">合规率</Text></div>
              </div>
              <Space direction="vertical">
                <Text>总计：<Text strong>{summary.total}</Text> 条</Text>
                <Text>高风险：<Tag color="red">{summary.high}</Tag></Text>
                <Text>中风险：<Tag color="orange">{summary.medium}</Tag></Text>
                <Text>低风险：<Tag color="green">{summary.low}</Tag></Text>
              </Space>
            </Space>
          </Card>

          <Card title="检测结果">
            <Table
              columns={columns}
              dataSource={results}
              rowKey={(_, i) => String(i)}
              pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
            />
          </Card>
        </>
      )}
    </div>
  );
}
