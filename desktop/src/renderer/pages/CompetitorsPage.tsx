import { Card, Table, Tag, Typography, Row, Col, Divider, Alert } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, SafetyOutlined, BulbOutlined, TeamOutlined, GlobalOutlined, ExperimentOutlined, ThunderboltOutlined } from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

const competitionData = [
  { feature: '商品内容合规检测', crossguard: true, linksafe: false, trademo: false, gaia: false },
  { feature: 'AI 混合检测引擎（规则+语义）', crossguard: true, linksafe: false, trademo: false, gaia: false },
  { feature: '多 LLM 自由切换', crossguard: true, linksafe: false, trademo: false, gaia: false },
  { feature: '欧盟 GPSR 合规', crossguard: true, linksafe: true, trademo: false, gaia: false },
  { feature: '美国 FDA/FCC 合规', crossguard: true, linksafe: false, trademo: true, gaia: true },
  { feature: '东南亚各国合规', crossguard: true, linksafe: false, trademo: false, gaia: false },
  { feature: '多语言支持（中/英/泰）', crossguard: true, linksafe: false, trademo: false, gaia: false },
  { feature: '数据飞轮（反馈优化）', crossguard: true, linksafe: false, trademo: false, gaia: false },
  { feature: '免费使用', crossguard: true, linksafe: false, trademo: false, gaia: false },
];

const columns = [
  { title: '功能特性', dataIndex: 'feature', key: 'feature', width: 240 },
  {
    title: 'CrossGuard', dataIndex: 'crossguard', key: 'crossguard', render: (v: boolean) => v
      ? <Tag icon={<CheckCircleOutlined />} color="green">✓</Tag>
      : <Tag icon={<CloseCircleOutlined />} color="red">✗</Tag>,
  },
  {
    title: 'LinkSafe', dataIndex: 'linksafe', key: 'linksafe', render: (v: boolean) => v
      ? <Tag icon={<CheckCircleOutlined />} color="green">✓</Tag>
      : <Tag icon={<CloseCircleOutlined />} color="red">✗</Tag>,
  },
  {
    title: 'Trademo', dataIndex: 'trademo', key: 'trademo', render: (v: boolean) => v
      ? <Tag icon={<CheckCircleOutlined />} color="green">✓</Tag>
      : <Tag icon={<CloseCircleOutlined />} color="red">✗</Tag>,
  },
  {
    title: 'Gaia Dynamics', dataIndex: 'gaia', key: 'gaia', render: (v: boolean) => v
      ? <Tag icon={<CheckCircleOutlined />} color="green">✓</Tag>
      : <Tag icon={<CloseCircleOutlined />} color="red">✗</Tag>,
  },
];

const advantages = [
  { icon: <ExperimentOutlined />, title: '混合智能引擎', desc: '关键词规则 + LLM 语义两级检测，同时保证高召回率与低误报率' },
  { icon: <ThunderboltOutlined />, title: '多 LLM 自由切换', desc: '不绑定任何 AI 提供商，可在 OpenAI/DeepSeek/GLM/Kimi/Ollama 间自由切换' },
  { icon: <GlobalOutlined />, title: '全球多市场覆盖', desc: '欧盟、美国、东南亚（新加坡/泰国/马来西亚）— 一个工具覆盖主流出海目的地' },
  { icon: <SafetyOutlined />, title: '数据飞轮', desc: '用户反馈持续提升准确率，使用越多越准，网络效应构建竞争壁垒' },
  { icon: <TeamOutlined />, title: '本地化优势', desc: '完整中/英/泰界面，专注服务中国跨境卖家，东南亚市场是竞品盲区' },
  { icon: <BulbOutlined />, title: '零成本起步', desc: '免费使用核心功能，降低中小卖家合规门槛，打破合规服务贵族化' },
];

export default function CompetitorsPage() {
  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 16px' }}>
      <Title level={3}>竞品对比</Title>
      <Paragraph type="secondary">
        CrossGuard 专注于"商品内容合规"这一细分赛道，与现有竞品形成差异化竞争。
        以下对比展示各产品在关键功能上的覆盖情况。
      </Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Table
          dataSource={competitionData}
          columns={columns}
          pagination={false}
          bordered
          size="middle"
          rowKey="feature"
        />
      </Card>

      <Divider />

      <Title level={4}>CrossGuard 核心优势</Title>
      <Row gutter={[16, 16]}>
        {advantages.map((adv) => (
          <Col key={adv.title} xs={24} sm={12}>
            <Card hoverable>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <span style={{ fontSize: 24, color: '#1890ff' }}>{adv.icon}</span>
                <div>
                  <Text strong>{adv.title}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 13 }}>{adv.desc}</Text>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Divider />

      <Alert
        type="info"
        message="市场定位"
        description={
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>不跟 LinkSafe 比税务合规（他们深耕 5 年，不做正面竞争）</li>
            <li>专注于"内容合规"新品类 — 商品描述、标签、成分、功效声明</li>
            <li>强调多市场覆盖 + AI 创新混合引擎 + 数据飞轮</li>
          </ul>
        }
        showIcon
      />
    </div>
  );
}
