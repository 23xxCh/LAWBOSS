import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Tag,
  Typography,
  Button,
  Space,
  Progress,
  List,
  Alert,
  Spin,
  message,
  Tooltip,
} from 'antd';
import {
  ArrowLeftOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  DownloadOutlined,
  CopyOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import { getReportDetail, exportReportPdf, submitFeedback, type ReportDetailResponse, type ViolationItem } from '../api';

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

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<ReportDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    if (id) {
      getReportDetail(id)
        .then(setData)
        .finally(() => setLoading(false));
    }
  }, [id]);

  const handleExportPdf = async () => {
    if (!id) return;
    setPdfLoading(true);
    try {
      const blob = await exportReportPdf(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `crossguard_report_${id.slice(0, 8)}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('PDF 报告已下载');
    } catch {
      message.error('PDF 导出失败');
    } finally {
      setPdfLoading(false);
    }
  };

  const handleCopyCompliant = () => {
    if (!data) return;
    navigator.clipboard.writeText(data.result.compliant_version).then(() => {
      message.success('合规版本已复制到剪贴板');
    });
  };

  const handleFeedback = async (feedbackType: 'false_positive' | 'correct', v: ViolationItem) => {
    if (!data) return;
    try {
      await submitFeedback({
        report_id: id || '',
        feedback_type: feedbackType,
        violation_type: v.type,
        violation_content: v.content,
        market: data.result.market,
        category: data.result.category,
        original_description: data.description,
        risk_score: data.result.risk_score,
      });
      const label = feedbackType === 'false_positive' ? '误报' : '正确';
      message.success(`已标记为${label}，感谢反馈！数据飞轮将据此优化规则。`);
    } catch {
      message.error('反馈提交失败');
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return <Alert type="error" title="报告不存在" />;
  }

  const result = data.result;
  const riskProgressColor =
    result.risk_score >= 70 ? '#ff4d4f' : result.risk_score >= 40 ? '#faad14' : '#52c41a';

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 16px' }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/reports')}>
          返回列表
        </Button>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          loading={pdfLoading}
          onClick={handleExportPdf}
        >
          导出 PDF 报告
        </Button>
      </Space>

      <Card title="报告详情" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="检测时间">
            {new Date(data.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="市场">{result.market}</Descriptions.Item>
          <Descriptions.Item label="产品类别">{result.category}</Descriptions.Item>
          <Descriptions.Item label="违规数量">{result.violations.length}</Descriptions.Item>
        </Descriptions>
        <Divider />
        <Typography.Title level={5}>原始描述</Typography.Title>
        <Paragraph
          style={{
            background: '#f5f5f5',
            padding: '12px 16px',
            borderRadius: 6,
          }}
        >
          {data.description}
        </Paragraph>
      </Card>

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
            <Tag
              color={riskLevelColor[result.risk_level] || 'default'}
              style={{ fontSize: 16, padding: '4px 12px' }}
            >
              {result.risk_level}
            </Tag>
            <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
              {result.risk_description}
            </Paragraph>
          </div>
        </Space>
      </Card>

      {/* 违规项 */}
      {result.violations.length > 0 && (
        <Card
          title={
            <Space>
              <WarningOutlined style={{ color: '#ff4d4f' }} />
              <span>违规项 ({result.violations.length})</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          {result.violations.map((v: ViolationItem, i: number) => (
            <Card key={i} size="small" style={{ marginBottom: 8 }}
              title={
                <Space>
                  <Tag color={severityColor[v.severity]}>{v.severity_label}</Tag>
                  <Text strong>{v.type_label}</Text>
                </Space>
              }
              extra={
                <Space size="small">
                  <Tooltip title="标记为误报">
                    <Button type="text" size="small" danger icon={<DislikeOutlined />} onClick={() => handleFeedback('false_positive', v)} />
                  </Tooltip>
                  <Tooltip title="标记为正确">
                    <Button type="text" size="small" icon={<LikeOutlined />} style={{ color: '#52c41a' }} onClick={() => handleFeedback('correct', v)} />
                  </Tooltip>
                </Space>
              }
            >
              <Descriptions column={1} size="small">
                <Descriptions.Item label="违规内容">
                  <Text mark>{v.content}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="法规依据">{v.regulation}</Descriptions.Item>
                <Descriptions.Item label="法规详情">{v.regulation_detail}</Descriptions.Item>
                <Descriptions.Item label="修改建议">
                  <Text type="success">{v.suggestion}</Text>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          ))}
        </Card>
      )}

      {result.violations.length === 0 && (
        <Alert
          type="success"
          title="未检测到违规内容"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 合规版本 + 一键复制 */}
      {result.compliant_version && result.compliant_version !== data.description && (
        <Card
          title="合规版本"
          style={{ marginBottom: 16 }}
          extra={
            <Tooltip title="复制合规版本到剪贴板">
              <Button
                type="primary"
                icon={<CopyOutlined />}
                onClick={handleCopyCompliant}
                size="small"
              >
                一键复制
              </Button>
            </Tooltip>
          }
        >
          <Paragraph
            style={{
              background: '#f6ffed',
              border: '1px solid #b7eb8f',
              borderRadius: 6,
              padding: '12px 16px',
              marginBottom: 0,
            }}
          >
            {result.compliant_version}
          </Paragraph>
        </Card>
      )}

      {/* 修改建议 */}
      {result.suggestions.length > 0 && (
        <Card title="修改建议">
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
    </div>
  );
}

function Divider(props: { style?: React.CSSProperties }) {
  return <hr style={{ border: 'none', borderTop: '1px solid #f0f0f0', margin: '16px 0', ...props.style }} />;
}
