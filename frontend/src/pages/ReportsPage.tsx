import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Modal,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  getReports,
  deleteReport,
  type ReportItem,
} from '../api';

const { Text } = Typography;

const riskLevelColor: Record<string, string> = {
  '高风险': 'red',
  '中风险': 'orange',
  '低风险': 'green',
};

export default function ReportsPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<ReportItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [marketFilter, setMarketFilter] = useState<string | undefined>();
  const [riskFilter, setRiskFilter] = useState<string | undefined>();

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getReports({
        page,
        page_size: 20,
        market: marketFilter,
        risk_level: riskFilter,
      });
      setData(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page, marketFilter, riskFilter]);

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该检测报告吗？',
      onOk: async () => {
        await deleteReport(id);
        message.success('删除成功');
        fetchData();
      },
    });
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '市场',
      dataIndex: 'market',
      key: 'market',
      width: 80,
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 100,
    },
    {
      title: '风险评分',
      dataIndex: 'risk_score',
      key: 'risk_score',
      width: 100,
      render: (v: number) => <Text strong>{v}</Text>,
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
      dataIndex: 'violation_count',
      key: 'violation_count',
      width: 80,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: ReportItem) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/reports/${record.id}`)}
          />
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          />
        </Space>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 16px' }}>
      <Card title="检测历史">
        <Space style={{ marginBottom: 16 }} wrap>
          <span>市场：</span>
          <Select
            allowClear
            placeholder="全部"
            style={{ width: 100 }}
            value={marketFilter}
            onChange={(v) => {
              setMarketFilter(v);
              setPage(1);
            }}
            options={[
              { value: 'EU', label: '欧盟' },
              { value: 'US', label: '美国' },
              { value: 'SEA_SG', label: '新加坡' },
              { value: 'SEA_TH', label: '泰国' },
              { value: 'SEA_MY', label: '马来西亚' },
            ]}
          />
          <span>风险等级：</span>
          <Select
            allowClear
            placeholder="全部"
            style={{ width: 100 }}
            value={riskFilter}
            onChange={(v) => {
              setRiskFilter(v);
              setPage(1);
            }}
            options={[
              { value: '高风险', label: '高风险' },
              { value: '中风险', label: '中风险' },
              { value: '低风险', label: '低风险' },
            ]}
          />
        </Space>
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 条`,
          }}
        />
      </Card>
    </div>
  );
}
