import { useState, useEffect, useRef, useCallback } from 'react';
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
  Input,
  Upload,
} from 'antd';
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  UploadOutlined,
  FileTextOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import {
  batchCheckCompliance,
  getMarkets,
  type CheckRequest,
  type CheckResponse,
  type MarketResponse,
} from '../api';

const { Text, Paragraph } = Typography;
const { Dragger } = Upload;

const riskLevelColor: Record<string, string> = {
  '高风险': 'red',
  '中风险': 'orange',
  '低风险': 'green',
};

/** 解析 CSV 文本内容，每行作为一个描述 */
function parseCSV(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => {
      // 如果行包含逗号/制表符，取第一列作为描述
      if (line.includes(',') || line.includes('\t')) {
        const sep = line.includes('\t') ? '\t' : ',';
        return line.split(sep)[0].trim();
      }
      return line;
    })
    .filter(Boolean);
}

export default function BatchCheckPage() {
  const [markets, setMarkets] = useState<MarketResponse[]>([]);
  const [market, setMarket] = useState<string>('EU');
  const [category, setCategory] = useState<string>('');
  const [descriptions, setDescriptions] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<CheckResponse[]>([]);
  const [summary, setSummary] = useState({ total: 0, high: 0, medium: 0, low: 0 });
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  /** 通过 Electron 原生对话框选择文件 */
  const handleFileSelect = async () => {
    if (!(window as any).api?.dialog) {
      message.warning('文件导入仅桌面端支持');
      return;
    }
    try {
      const result = await (window as any).api.dialog.openFile({
        title: '选择 CSV 文件',
        filters: [
          { name: 'CSV 文件', extensions: ['csv'] },
          { name: '文本文件', extensions: ['txt'] },
          { name: '所有文件', extensions: ['*'] },
        ],
      });
      if (result.canceled || !result.filePaths?.[0]) return;

      setImporting(true);
      const filePath = result.filePaths[0];
      const res = await (window as any).api.file.read(filePath);
      if (res.success && res.data) {
        const lines = parseCSV(res.data);
        if (lines.length === 0) {
          message.warning('文件中未找到有效内容');
        } else if (lines.length > 100) {
          message.warning('最多导入 100 条，已截断');
          setDescriptions(lines.slice(0, 100).join('\n'));
        } else {
          setDescriptions(lines.join('\n'));
          message.success(`已导入 ${lines.length} 条产品描述`);
        }
      } else {
        message.error('文件读取失败: ' + (res.error || '未知错误'));
      }
    } catch (e: unknown) {
      message.error('文件导入失败');
    } finally {
      setImporting(false);
    }
  };

  /** 拖拽文件处理 */
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    const file = files[0];
    if (!file.name.endsWith('.csv') && !file.name.endsWith('.txt')) {
      message.warning('仅支持 .csv 或 .txt 文件');
      return;
    }

    // 在 Electron 中通过 preload 读取拖拽文件
    if ((window as any).api?.file) {
      setImporting(true);
      try {
        const results = await (window as any).api.file.handleDrop([file.path]);
        if (results?.[0]?.success && results[0].content) {
          const lines = parseCSV(results[0].content);
          if (lines.length > 100) {
            setDescriptions(lines.slice(0, 100).join('\n'));
            message.warning('最多导入 100 条，已截断');
          } else {
            setDescriptions(lines.join('\n'));
            message.success(`已导入 ${lines.length} 条产品描述`);
          }
        }
      } catch {
        message.error('文件读取失败');
      } finally {
        setImporting(false);
      }
    }
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

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

      // 系统通知
      if ((window as any).api?.notification && res.high_risk_count > 0) {
        (window as any).api.notification.show(
          '批量检测完成',
          `检测 ${res.total} 条，高风险 ${res.high_risk_count} 条`
        );
      }
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
      render: (_: unknown, r: CheckResponse) => (r.violations ?? []).length,
    },
    {
      title: '主要违规',
      key: 'top_violations',
      render: (_: unknown, r: CheckResponse) => {
        const types = [...new Set((r.violations ?? []).map((v) => v.type_label))];
        return types.length > 0
          ? types.slice(0, 3).map((t) => <Tag key={t}>{t}</Tag>)
          : <Tag color="green">合规</Tag>;
      },
    },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 16px' }}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
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

        {/* 文件导入区域 */}
        <div
          style={{
            border: '2px dashed #d9d9d9',
            borderRadius: 8,
            padding: '16px',
            textAlign: 'center',
            marginBottom: 16,
            cursor: 'pointer',
            background: '#fafafa',
            transition: 'border-color 0.3s',
          }}
          onClick={handleFileSelect}
          onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = '#1890ff'; }}
          onDragLeave={(e) => { e.currentTarget.style.borderColor = '#d9d9d9'; }}
        >
          {importing ? (
            <Spin tip="正在读取文件..." />
          ) : (
            <Space orientation="vertical" size="small">
              <UploadOutlined style={{ fontSize: 32, color: '#1890ff' }} />
              <Text strong>导入 CSV 文件</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                点击选择文件，或拖拽 CSV/TXT 文件到此处（每行一条产品描述）
              </Text>
            </Space>
          )}
        </div>

        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          每行输入一条产品描述，最多 100 条
        </Typography.Text>
        <Input.TextArea
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
          <Spin size="large" description="正在批量检测..." />
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
              <Space orientation="vertical">
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
              rowKey={(_, index) => `result-${index}`}
              pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
            />
          </Card>
        </>
      )}
    </div>
  );
}
