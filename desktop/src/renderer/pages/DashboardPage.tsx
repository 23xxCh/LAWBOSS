import { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Typography,
  Spin,
  Button,
  Select,
  Alert,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  DashboardOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import {
  getAccuracyMetrics,
  getPlatformStatus,
  triggerPatrol,
  type AccuracyMetrics,
  type PlatformStatus,
} from '../api';
import api from '../api/client';

const { Text, Title, Paragraph } = Typography;

interface AccuracyMetrics {
  total_feedbacks: number;
  false_positive_count: number;
  false_negative_count: number;
  correct_count: number;
  false_positive_rate: number;
  false_negative_rate: number;
  accuracy: number;
  by_violation_type: Record<string, {
    total: number;
    fp: number;
    fn: number;
    correct: number;
    accuracy: number;
    fp_rate: number;
    fn_rate: number;
  }>;
}

interface PlatformStatus {
  platform: string;
  status: string;
}

interface OptimizationSuggestion {
  id: string;
  violation_type: string;
  content: string;
  suggestion_type: string;
  reason: string;
  confidence: number;
  feedback_count: number;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<AccuracyMetrics | null>(null);
  const [platforms, setPlatforms] = useState<PlatformStatus[]>([]);
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [patrolLoading, setPatrolLoading] = useState(false);
  const [patrolPlatform, setPatrolPlatform] = useState('amazon');
  const [patrolMarket, setPatrolMarket] = useState('US');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [metricsData, platformsData, suggestionsRes] = await Promise.all([
        getAccuracyMetrics(),
        getPlatformStatus(),
        api.get('/feedback/suggestions', { params: { limit: 10 } }),
      ]);
      setMetrics(metricsData);
      setPlatforms(platformsData);
      setSuggestions(suggestionsRes.data);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  };

  const handlePatrol = async () => {
    setPatrolLoading(true);
    try {
      const { data } = await triggerPatrol({
        platform: patrolPlatform,
        market: patrolMarket,
        limit: 50,
      });
      message.success(`巡检完成：检测 ${data.checked_listings} 条，高风险 ${data.high_risk_count} 条`);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail || '巡检失败，请检查平台配置');
    } finally {
      setPatrolLoading(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  }

  const suggestionColumns = [
    {
      title: '违规类型',
      dataIndex: 'violation_type',
      key: 'violation_type',
      width: 120,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: '建议类型',
      dataIndex: 'suggestion_type',
      key: 'suggestion_type',
      width: 120,
      render: (v: string) => (
        <Tag color={v === 'remove_word' ? 'red' : 'green'}>
          {v === 'remove_word' ? '移除词汇' : '补充词库'}
        </Tag>
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 100,
      render: (v: number) => <Progress percent={Math.round(v * 100)} size="small" />,
    },
    {
      title: '反馈数',
      dataIndex: 'feedback_count',
      key: 'feedback_count',
      width: 80,
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
      <Title level={3}><DashboardOutlined /> 数据看板</Title>

      {/* 数据飞轮概览 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总反馈数"
              value={metrics?.total_feedbacks || 0}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="检测准确率"
              value={metrics?.accuracy || 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: (metrics?.accuracy || 0) >= 90 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="误报率"
              value={metrics?.false_positive_rate || 0}
              suffix="%"
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="漏报率"
              value={metrics?.false_negative_rate || 0}
              suffix="%"
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 数据飞轮说明 */}
      <Card style={{ marginBottom: 16 }}>
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Title level={5}>数据飞轮</Title>
          <Paragraph type="secondary">
            用户反馈 → 统计分析 → 规则优化建议 → 人工审核 → 规则更新 → 精度提升
          </Paragraph>
          <Row gutter={16}>
            <Col span={8}>
              <Card type="inner" title="误报 (False Positive)">
                <Text>系统报了但实际不违规</Text>
                <br />
                <Text type="danger" strong>{metrics?.false_positive_count || 0} 条</Text>
                <br />
                <Text type="secondary">→ 建议移除该词或添加白名单</Text>
              </Card>
            </Col>
            <Col span={8}>
              <Card type="inner" title="漏报 (False Negative)">
                <Text>系统没报但实际违规</Text>
                <br />
                <Text type="warning" strong>{metrics?.false_negative_count || 0} 条</Text>
                <br />
                <Text type="secondary">→ 建议补充禁用词库</Text>
              </Card>
            </Col>
            <Col span={8}>
              <Card type="inner" title="正确 (Correct)">
                <Text>检测结果准确</Text>
                <br />
                <Text type="success" strong>{metrics?.correct_count || 0} 条</Text>
                <br />
                <Text type="secondary">→ 增强规则置信度</Text>
              </Card>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* 按违规类型的精度 */}
      {metrics?.by_violation_type && Object.keys(metrics.by_violation_type).length > 0 && (
        <Card title="各违规类型精度" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            {Object.entries(metrics.by_violation_type).map(([type, data]) => (
              <Col span={8} key={type}>
                <Card type="inner" size="small">
                  <Statistic title={type} value={data.accuracy} suffix="%" />
                  <div style={{ marginTop: 8 }}>
                    <Tag color="red">误报 {data.fp_rate}%</Tag>
                    <Tag color="orange">漏报 {data.fn_rate}%</Tag>
                    <Tag color="green">正确 {data.accuracy}%</Tag>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* 规则优化建议 */}
      <Card title="规则优化建议（数据飞轮输出）" style={{ marginBottom: 16 }}>
        {suggestions.length > 0 ? (
          <Table
            columns={suggestionColumns}
            dataSource={suggestions}
            rowKey="id"
            pagination={false}
            size="small"
          />
        ) : (
          <Alert
            type="info"
            message="暂无优化建议"
            description="当用户反馈积累到一定数量后，系统将自动生成规则优化建议。请在检测后对结果提交反馈。"
          />
        )}
      </Card>

      {/* 平台对接 + 巡检 */}
      <Card title="电商平台对接" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={12}>
            <Title level={5}>平台连接状态</Title>
            <Space orientation="vertical" style={{ width: '100%' }}>
              {platforms.map((p) => (
                <div key={p.platform}>
                  <Tag color={p.status === 'connected' ? 'green' : 'default'} icon={<ApiOutlined />}>
                    {p.platform}
                  </Tag>
                  <Text type={p.status === 'connected' ? 'success' : 'secondary'}>
                    {p.status === 'connected' ? '已连接' : '未配置'}
                  </Text>
                </div>
              ))}
            </Space>
          </Col>
          <Col span={12}>
            <Title level={5}>手动触发巡检</Title>
            <Space wrap style={{ marginBottom: 16 }}>
              <Select
                value={patrolPlatform}
                onChange={setPatrolPlatform}
                style={{ width: 120 }}
                options={[
                  { value: 'amazon', label: 'Amazon' },
                  { value: 'shopee', label: 'Shopee' },
                ]}
              />
              <Select
                value={patrolMarket}
                onChange={setPatrolMarket}
                style={{ width: 120 }}
                options={[
                  { value: 'US', label: '美国' },
                  { value: 'EU', label: '欧盟' },
                  { value: 'SEA_SG', label: '新加坡' },
                  { value: 'SEA_TH', label: '泰国' },
                  { value: 'SEA_MY', label: '马来西亚' },
                ]}
              />
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={patrolLoading}
                onClick={handlePatrol}
              >
                开始巡检
              </Button>
            </Space>
            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              巡检将自动拉取平台 Listing 并执行合规检测，高风险项将触发 Webhook 告警。
            </Paragraph>
          </Col>
        </Row>
      </Card>
    </div>
  );
}
