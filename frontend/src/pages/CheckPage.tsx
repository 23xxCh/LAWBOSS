import { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Input,
  Button,
  Tag,
  Descriptions,
  List,
  Space,
  Typography,
  Alert,
  Spin,
  Progress,
  message,
  Upload,
  Tabs,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
  PictureOutlined,
  CopyOutlined,
  RobotOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import {
  checkCompliance,
  checkImage,
  getMarkets,
  submitFeedback,
  checkMultiMarket,
  type CheckResponse,
  type ViolationItem,
  type MarketResponse,
  type MultiMarketCheckResponse,
} from '../api';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const severityColor: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'blue',
};

const riskLevelColor: Record<string, string> = {
  '高风险': 'red',
  '中风险': 'orange',
  '低风险': 'green',
};

function ViolationCard({ violation, market, category, onFeedback }: { violation: ViolationItem; market: string; category: string; onFeedback: (type: 'false_positive' | 'correct', violation: ViolationItem) => void }) {
  return (
    <Card
      size="small"
      style={{ marginBottom: 8 }}
      title={
        <Space>
          <Tag color={severityColor[violation.severity]}>
            {violation.severity_label}
          </Tag>
          <Text strong>{violation.type_label}</Text>
        </Space>
      }
      extra={
        <Space size="small">
          <Tooltip title="标记为误报（系统报了但实际不违规）">
            <Button
              type="text"
              size="small"
              danger
              icon={<DislikeOutlined />}
              onClick={() => onFeedback('false_positive', violation)}
            />
          </Tooltip>
          <Tooltip title="标记为正确（检测结果准确）">
            <Button
              type="text"
              size="small"
              icon={<LikeOutlined />}
              style={{ color: '#52c41a' }}
              onClick={() => onFeedback('correct', violation)}
            />
          </Tooltip>
        </Space>
      }
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="违规内容">
          <Text mark>{violation.content}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="法规依据">
          {violation.regulation}
        </Descriptions.Item>
        <Descriptions.Item label="法规详情">
          {violation.regulation_detail}
        </Descriptions.Item>
        <Descriptions.Item label="修改建议">
          <Text type="success">{violation.suggestion}</Text>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

/** Diff 对比：高亮原文与合规版本之间的差异 */
function DiffView({ original, compliant }: { original: string; compliant: string }) {
  if (original === compliant) return <Paragraph>{compliant}</Paragraph>;

  // 简单的逐字对比：找出不同的片段
  const segments: { text: string; changed: boolean }[] = [];
  let i = 0, j = 0;
  while (i < original.length || j < compliant.length) {
    if (i < original.length && j < compliant.length && original[i] === compliant[j]) {
      segments.push({ text: compliant[j], changed: false });
      i++; j++;
    } else {
      // 找到下一个匹配点
      let changedText = '';
      while (j < compliant.length && (i >= original.length || original[i] !== compliant[j])) {
        changedText += compliant[j];
        j++;
      }
      if (changedText) {
        segments.push({ text: changedText, changed: true });
      }
      // 跳过原文中已删除的字符
      while (i < original.length && (j >= compliant.length || original[i] !== compliant[j])) {
        i++;
      }
    }
  }

  return (
    <Paragraph style={{ marginBottom: 0 }}>
      {segments.map((seg, idx) =>
        seg.changed ? (
          <Text key={idx} style={{ backgroundColor: '#e6f7ff', border: '1px solid #91d5ff', borderRadius: 2, padding: '0 2px' }}>
            {seg.text}
          </Text>
        ) : (
          <span key={idx}>{seg.text}</span>
        )
      )}
    </Paragraph>
  );
}

/** 在原文中高亮违规内容 */
function HighlightedDescription({ text, violations }: { text: string; violations: ViolationItem[] }) {
  if (violations.length === 0) return <Paragraph>{text}</Paragraph>;

  // 收集所有违规位置
  const positions: { start: number; end: number; type: string }[] = [];
  for (const v of violations) {
    const content = v.content;
    let searchFrom = 0;
    while (true) {
      const idx = text.indexOf(content, searchFrom);
      if (idx === -1) break;
      positions.push({ start: idx, end: idx + content.length, type: v.type });
      searchFrom = idx + 1;
    }
  }
  positions.sort((a, b) => a.start - b.start);

  // 合并重叠区间
  const merged: { start: number; end: number; type: string }[] = [];
  for (const pos of positions) {
    if (merged.length > 0 && pos.start < merged[merged.length - 1].end) {
      merged[merged.length - 1].end = Math.max(merged[merged.length - 1].end, pos.end);
    } else {
      merged.push({ ...pos });
    }
  }

  // 渲染
  const parts: React.ReactNode[] = [];
  let lastEnd = 0;
  for (const m of merged) {
    if (m.start > lastEnd) {
      parts.push(<span key={`t${lastEnd}`}>{text.slice(lastEnd, m.start)}</span>);
    }
    const color = m.type === 'medical_claim' ? '#ff4d4f' : m.type === 'banned_ingredient' ? '#ff4d4f' : '#faad14';
    parts.push(
      <Text key={`h${m.start}`} mark style={{ backgroundColor: color + '22', borderColor: color, padding: '0 2px' }}>
        {text.slice(m.start, m.end)}
      </Text>
    );
    lastEnd = m.end;
  }
  if (lastEnd < text.length) {
    parts.push(<span key="end">{text.slice(lastEnd)}</span>);
  }

  return <Paragraph style={{ marginBottom: 0 }}>{parts}</Paragraph>;
}

export default function CheckPage() {
  const [markets, setMarkets] = useState<MarketResponse[]>([]);
  const [market, setMarket] = useState<string>('EU');
  const [category, setCategory] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [multiMarketResult, setMultiMarketResult] = useState<MultiMarketCheckResponse | null>(null);
  const [multiMarketLoading, setMultiMarketLoading] = useState(false);

  useEffect(() => {
    getMarkets().then((data) => {
      setMarkets(data);
      if (data.length > 0) {
        setMarket(data[0].code);
        setCategory(data[0].categories[0] || '');
      }
    }).catch(() => {
      message.error('无法连接后端服务');
    });
  }, []);

  const currentMarket = markets.find((m) => m.code === market);
  const categories = currentMarket?.categories || [];

  const handleCheck = async () => {
    if (!description.trim()) return;
    setLoading(true);
    try {
      const res = await checkCompliance({ description, category, market });
      setResult(res);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleImageCheck = async () => {
    if (!imageFile) return;
    setLoading(true);
    try {
      const res = await checkImage(imageFile, category, market);
      setResult(res);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = (file: File) => {
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target?.result as string);
    reader.readAsDataURL(file);
    setResult(null);
    return false; // prevent auto upload
  };

  const handleMultiMarket = async () => {
    if (!description.trim()) return;
    setMultiMarketLoading(true);
    setMultiMarketResult(null);
    try {
      const res = await checkMultiMarket({ description, category, market });
      setMultiMarketResult(res);
    } catch {
      message.error('跨市场对比请求失败');
    } finally {
      setMultiMarketLoading(false);
    }
  };

  const handleFeedback = async (feedbackType: 'false_positive' | 'correct', violation: ViolationItem) => {
    try {
      await submitFeedback({
        report_id: 'current',  // 当前检测无持久化ID，使用标记
        feedback_type: feedbackType,
        violation_type: violation.type,
        violation_content: violation.content,
        market,
        category,
        original_description: description,
        risk_score: result?.risk_score || 0,
      });
      const label = feedbackType === 'false_positive' ? '误报' : '正确';
      message.success(`已标记为${label}，感谢反馈！数据飞轮将据此优化规则。`);
    } catch {
      message.error('反馈提交失败');
    }
  };

  const riskProgressColor = result
    ? result.risk_score >= 70
      ? '#ff4d4f'
      : result.risk_score >= 40
        ? '#faad14'
        : '#52c41a'
    : '#1890ff';

  const marketCategorySelector = (
    <Space wrap>
      <span>目标市场：</span>
      <Select
        value={market}
        onChange={(v) => {
          setMarket(v);
          const m = markets.find((m) => m.code === v);
          setCategory(m?.categories[0] || '');
          setResult(null);
        }}
        style={{ width: 140 }}
        options={markets.map((m) => ({ value: m.code, label: m.name }))}
      />
      <span>产品类别：</span>
      <Select
        value={category}
        onChange={(v) => { setCategory(v); setResult(null); }}
        style={{ width: 140 }}
        options={categories.map((c) => ({ value: c, label: c }))}
      />
    </Space>
  );

  const resultSection = result && !loading && (
    <>
      {/* 风险评分 */}
      <Card style={{ marginBottom: 16 }}>
        <Space align="center" size="large">
          <Progress
            type="dashboard"
            percent={result.risk_score}
            strokeColor={riskProgressColor}
            format={(p) => <span style={{ fontSize: 24 }}>{p}</span>}
            size={120}
          />
          <div>
            <Tag color={riskLevelColor[result.risk_level] || 'default'} style={{ fontSize: 16, padding: '4px 12px' }}>
              {result.risk_level}
            </Tag>
            <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
              {result.risk_description}
            </Paragraph>
          </div>
        </Space>
      </Card>

      {/* 原文高亮 */}
      {result.violations.length > 0 && description && (
        <Card title="违规内容高亮" style={{ marginBottom: 16 }}>
          <div style={{ background: '#fafafa', padding: '12px 16px', borderRadius: 6 }}>
            <HighlightedDescription text={description} violations={result.violations} />
          </div>
        </Card>
      )}

      {/* 违规项 */}
      {result.violations.length > 0 && (
        <Card
          title={<Space><WarningOutlined style={{ color: '#ff4d4f' }} /><span>违规项 ({result.violations.length})</span></Space>}
          style={{ marginBottom: 16 }}
          extra={
            result.violations.some(v => v.type === 'implicit_violation' || v.regulation === 'AI 语义分析判定')
              ? <Tag icon={<RobotOutlined />} color="purple">含 AI 语义检测</Tag>
              : null
          }
        >
          {result.violations.map((v, i) => <ViolationCard key={i} violation={v} market={market} category={category} onFeedback={handleFeedback} />)}
        </Card>
      )}

      {result.violations.length === 0 && (
        <Alert
          type="success"
          title="恭喜！未检测到违规内容"
          description="该产品描述符合目标市场的法规要求。"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 合规版本 diff 对比 */}
      {result.compliant_version && result.compliant_version !== description && (
        <Card
          title="合规版本（修改处已高亮）"
          style={{ marginBottom: 16 }}
          extra={
            <Button
              type="primary"
              icon={<CopyOutlined />}
              size="small"
              onClick={() => {
                navigator.clipboard.writeText(result.compliant_version);
                message.success('合规版本已复制到剪贴板');
              }}
            >
              一键复制
            </Button>
          }
        >
          <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6, padding: '12px 16px' }}>
            <DiffView original={description} compliant={result.compliant_version} />
          </div>
        </Card>
      )}

      {/* 必需标签 & 认证 */}
      <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        {result.required_labels.length > 0 && (
          <Card title="必需标签" size="small">
            <Space wrap>
              {result.required_labels.map((label, i) => (
                <Tag key={i} icon={<ExclamationCircleOutlined />} color="blue">{label}</Tag>
              ))}
            </Space>
          </Card>
        )}
        {result.required_certifications.length > 0 && (
          <Card title="必需认证" size="small">
            <Space wrap>
              {result.required_certifications.map((cert, i) => (
                <Tag key={i} icon={<ExclamationCircleOutlined />} color="purple">{cert}</Tag>
              ))}
            </Space>
          </Card>
        )}
      </Space>

      {/* 修改建议 */}
      {result.suggestions.length > 0 && (
        <Card title="修改建议" style={{ marginTop: 16 }}>
          <List
            size="small"
            dataSource={result.suggestions}
            renderItem={(item) => <List.Item><Text>{item}</Text></List.Item>}
          />
        </Card>
      )}

      {/* 免责声明 */}
      <Alert
        type="warning"
        title="免责声明"
        description="本工具提供的检测结果和修改建议仅供参考，不构成法律意见，不保证检测的完整性和准确性。产品合规性应以目标市场监管机构的最终判定为准。建议在重要合规决策前咨询专业法律顾问。"
        showIcon
        style={{ marginTop: 16, fontSize: 12 }}
      />
    </>
  );

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 16px' }}>
      <Card title="合规检测" style={{ marginBottom: 16 }}>
        {marketCategorySelector}
        <Tabs
          style={{ marginTop: 16 }}
          items={[
            {
              key: 'text',
              label: <span><SearchOutlined /> 文本检测</span>,
              children: (
                <Space orientation="vertical" style={{ width: '100%' }} size="middle">
                  <TextArea
                    rows={6}
                    value={description}
                    onChange={(e) => { setDescription(e.target.value); setResult(null); }}
                    placeholder="请输入产品描述，例如：这款面霜能治疗痘痘，7天见效，是市面上最好的产品"
                  />
                  <Button
                    type="primary"
                    icon={<SearchOutlined />}
                    loading={loading}
                    onClick={handleCheck}
                    disabled={!description.trim()}
                    size="large"
                    block
                  >
                    开始检测
                  </Button>
                </Space>
              ),
            },
            {
              key: 'image',
              label: <span><PictureOutlined /> 图片检测</span>,
              children: (
                <Space orientation="vertical" style={{ width: '100%' }} size="middle">
                  <Upload
                    beforeUpload={handleImageUpload}
                    accept=".png,.jpg,.jpeg,.webp"
                    maxCount={1}
                    showUploadList={false}
                  >
                    <Button icon={<UploadOutlined />} size="large">
                      选择产品图片
                    </Button>
                  </Upload>
                  {imagePreview && (
                    <div style={{ marginTop: 8 }}>
                      <img src={imagePreview} alt="preview" style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8, border: '1px solid #d9d9d9' }} />
                      <div style={{ marginTop: 4 }}>
                        <Text type="secondary">{imageFile?.name}</Text>
                      </div>
                    </div>
                  )}
                  <Button
                    type="primary"
                    icon={<PictureOutlined />}
                    loading={loading}
                    onClick={handleImageCheck}
                    disabled={!imageFile}
                    size="large"
                    block
                  >
                    OCR 识别 + 合规检测
                  </Button>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    支持 PNG/JPG/WEBP 格式，最大 10MB。将自动识别图片中的文字并进行合规检测。
                  </Text>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {loading && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" description="正在检测..." />
        </Card>
      )}

      {resultSection}

      {/* Demo 模式区 */}
      {result && !loading && (
        <Card title="演示模式" style={{ marginTop: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Alert
              type="info"
              message="跨市场对比演示 — 同一商品在 EU、US、东南亚市场分别检测"
              description="一键查看同一商品在不同目标市场的合规差异，快速识别最适合销售的市场。"
              showIcon
            />
            <Button
              icon={<SearchOutlined />}
              loading={multiMarketLoading}
              onClick={handleMultiMarket}
              size="large"
              block
            >
              跨市场对比演示 (EU / US / SEA)
            </Button>
          </Space>
        </Card>
      )}

      {/* 跨市场对比结果 */}
      {multiMarketResult && (
        <div style={{ marginTop: 16 }}>
          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: '#faad14' }} />
                <span>跨市场对比结果</span>
              </Space>
            }
            extra={
              <Space>
                <Tag color="green">最佳市场: {multiMarketResult.best_market}</Tag>
                <Tag color="red">最差市场: {multiMarketResult.worst_market}</Tag>
              </Space>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {multiMarketResult.results.map((mr) => (
                <Card
                  key={mr.market}
                  size="small"
                  type="inner"
                  title={
                    <Space>
                      <Text strong>{mr.market_name} ({mr.market})</Text>
                      <Tag color={mr.risk_score >= 70 ? 'red' : mr.risk_score >= 40 ? 'orange' : 'green'}>
                        风险 {mr.risk_score} 分 - {mr.risk_level}
                      </Tag>
                    </Space>
                  }
                >
                  {mr.violations.length > 0 ? (
                    <List
                      size="small"
                      dataSource={mr.violations}
                      renderItem={(v) => (
                        <List.Item>
                          <Space>
                            <Tag color={severityColor[v.severity]}>{v.severity_label}</Tag>
                            <Text>{v.content}</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>{v.type_label}</Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Text type="success">未检测到违规</Text>
                  )}
                </Card>
              ))}
            </Space>
          </Card>
        </div>
      )}

      {/* 免责声明（如有结果显示） */}
      {result && !loading && (
        <Alert
          type="warning"
          title="免责声明"
          description="本工具提供的检测结果和修改建议仅供参考，不构成法律意见，不保证检测的完整性和准确性。产品合规性应以目标市场监管机构的最终判定为准。建议在重要合规决策前咨询专业法律顾问。"
          showIcon
          style={{ marginTop: 16, fontSize: 12 }}
        />
      )}
    </div>
  );
}
