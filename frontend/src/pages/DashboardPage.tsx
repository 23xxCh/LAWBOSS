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
  Divider,
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
  getCostSavings,
  type AccuracyMetrics,
  type PlatformStatus,
  type CostSavingsResponse,
} from '../api';
import api from '../api/client';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  PieChart, Pie, Cell, ResponsiveContainer,
} from 'recharts';

const { Text, Title, Paragraph } = Typography;

const PIE_COLORS = ['#ff4d4f', '#faad14', '#52c41a'];

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<AccuracyMetrics | null>(null);
  const [platforms, setPlatforms] = useState<PlatformStatus[]>([]);
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [costData, setCostData] = useState<CostSavingsResponse | null>(null);
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
      getCostSavings().then(setCostData).catch(() => null);
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

      {/* 准确率可视化图表 */}
      <Card title="准确率看板" style={{ marginBottom: 16 }}>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Title level={5}>反馈分布 (FP / FN / Correct)</Title>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={[
                    { name: '误报 (FP)', value: metrics?.false_positive_count || 0 },
                    { name: '漏报 (FN)', value: metrics?.false_negative_count || 0 },
                    { name: '正确', value: metrics?.correct_count || 0 },
                  ]}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }: { name: string; percent: number }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  <Cell fill="#ff4d4f" />
                  <Cell fill="#faad14" />
                  <Cell fill="#52c41a" />
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Col>
          <Col xs={24} md={12}>
            <Title level={5}>各类型准确率对比</Title>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={Object.entries(metrics?.by_violation_type || {}).map(([type, data]) => ({
                  name: type,
                  accuracy: data.accuracy,
                  fp_rate: data.fp_rate,
                  fn_rate: data.fn_rate,
                }))}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} unit="%" />
                <YAxis type="category" dataKey="name" width={100} fontSize={12} />
                <RechartsTooltip formatter={(v: number) => `${v}%`} />
                <Bar dataKey="accuracy" name="准确率" fill="#52c41a" radius={[0, 4, 4, 0]} />
                <Bar dataKey="fp_rate" name="误报率" fill="#ff4d4f" radius={[0, 4, 4, 0]} />
                <Bar dataKey="fn_rate" name="漏报率" fill="#faad14" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Col>
          <Col span={24}>
            <Title level={5}>精度摘要</Title>
            <Paragraph>
              准确率 <Text strong style={{ color: (metrics?.accuracy || 0) >= 90 ? '#52c41a' : '#faad14' }}>{metrics?.accuracy || 0}%</Text> |
              正确 <Text type="success">{metrics?.correct_count || 0}</Text> 条 |
              误报 <Text type="danger">{metrics?.false_positive_count || 0}</Text> 条 |
              漏报 <Text type="warning">{metrics?.false_negative_count || 0}</Text> 条 |
              <Text type="secondary"> 基于 {metrics?.total_feedbacks || 0} 条用户反馈</Text>
            </Paragraph>
          </Col>
        </Row>
      </Card>

      {/* 合规成本计算器 */}
      <Card title="合规成本计算器" style={{ marginBottom: 16 }}>
        {costData ? (
          <>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="总风险敞口"
                  value={costData.total_risk_exposure}
                  prefix="$"
                  valueStyle={{ color: '#ff4d4f', fontSize: 28 }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="年节省估算"
                  value={costData.annual_savings}
                  prefix="$"
                  valueStyle={{ color: '#52c41a', fontSize: 28 }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="每次检测节省"
                  value={costData.savings_per_check}
                  prefix="$"
                  suffix="/次"
                  valueStyle={{ color: '#1890ff', fontSize: 28 }}
                />
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Text strong>各市场罚款估算</Text>
            <Table
              dataSource={costData.market_penalties}
              columns={[
                { title: '市场', dataIndex: 'market_label', key: 'market' },
                { title: '最低罚款', dataIndex: 'min_penalty', key: 'min', render: (v: number) => `$${v.toLocaleString()}` },
                { title: '最高罚款', dataIndex: 'max_penalty', key: 'max', render: (v: number) => `$${v.toLocaleString()}` },
                { title: '估计罚款', dataIndex: 'estimated_penalty', key: 'est', render: (v: number) => `$${v.toLocaleString()}` },
                { title: '货币', dataIndex: 'currency', key: 'currency' },
              ]}
              pagination={false}
              size="small"
              rowKey="market"
              style={{ marginTop: 8 }}
            />
            <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8 }}>
              {costData.disclaimer}
            </Paragraph>
          </>
        ) : (
          <Alert
            type="info"
            message="合规成本数据"
            description="完成一次检测后，系统将基于违规项估算潜在罚款风险与合规节省成本。"
            showIcon
          />
        )}
      </Card>

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
