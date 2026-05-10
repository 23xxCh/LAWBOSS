import { useState, useEffect } from 'react';
import {
  Card, Table, Button, Space, Modal, Form, Input, Select, message,
  Tag, Popconfirm, Tabs, Typography, Badge, Tooltip, Spin
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined, CheckOutlined,
  CloseOutlined, HistoryOutlined
} from '@ant-design/icons';
import api from '../api/client';

const { Title, Text } = Typography;

// Types
interface BannedWord {
  id: string;
  word: string;
  violation_type: string;
  market: string;
  category: string;
  severity: number;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

interface Replacement {
  id: string;
  original_word: string;
  replacement: string;
  market: string;
  category: string;
  version: number;
  is_active: boolean;
}

interface Suggestion {
  id: string;
  violation_type: string;
  content: string;
  suggestion_type: string;
  reason: string;
  confidence: number;
  feedback_count: number;
  status: string;
  created_at: string;
}

export default function AdminRulesPage() {
  const [activeTab, setActiveTab] = useState('banned-words');
  const [loading, setLoading] = useState(false);

  // Banned Words State
  const [bannedWords, setBannedWords] = useState<BannedWord[]>([]);
  const [bwTotal, setBwTotal] = useState(0);
  const [bwPage, setBwPage] = useState(1);
  const [bwFilters, setBwFilters] = useState({ market: '', category: '', violation_type: '' });

  // Replacements State
  const [replacements, setReplacements] = useState<Replacement[]>([]);
  const [rpTotal, setRpTotal] = useState(0);
  const [rpPage, setRpPage] = useState(1);

  // Suggestions State
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);

  // Modal State
  const [bwModalVisible, setBwModalVisible] = useState(false);
  const [rpModalVisible, setRpModalVisible] = useState(false);
  const [editingBw, setEditingBw] = useState<BannedWord | null>(null);
  const [bwForm] = Form.useForm();
  const [rpForm] = Form.useForm();

  // Load data
  useEffect(() => {
    if (activeTab === 'banned-words') loadBannedWords();
    else if (activeTab === 'replacements') loadReplacements();
    else if (activeTab === 'suggestions') loadSuggestions();
  }, [activeTab, bwPage, bwFilters, rpPage]);

  const loadBannedWords = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', String(bwPage));
      params.append('page_size', '20');
      if (bwFilters.market) params.append('market', bwFilters.market);
      if (bwFilters.category) params.append('category', bwFilters.category);
      if (bwFilters.violation_type) params.append('violation_type', bwFilters.violation_type);

      const res = await api.get(`/admin/rules/banned-words?${params}`);
      setBannedWords(res.data.items);
      setBwTotal(res.data.total);
    } catch (e) {
      message.error('加载禁用词失败');
    } finally {
      setLoading(false);
    }
  };

  const loadReplacements = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/admin/rules/replacements?page=${rpPage}&page_size=20`);
      setReplacements(res.data.items);
      setRpTotal(res.data.total);
    } catch (e) {
      message.error('加载替换建议失败');
    } finally {
      setLoading(false);
    }
  };

  const loadSuggestions = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/rules/suggestions?limit=50');
      setSuggestions(res.data);
    } catch (e) {
      message.error('加载优化建议失败');
    } finally {
      setLoading(false);
    }
  };

  // Banned Words CRUD
  const handleCreateBw = async (values: any) => {
    try {
      await api.post('/admin/rules/banned-words', {
        ...values,
        market: values.market.toUpperCase(),
      });
      message.success('添加成功');
      setBwModalVisible(false);
      bwForm.resetFields();
      loadBannedWords();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '添加失败');
    }
  };

  const handleUpdateBw = async (id: string, values: any) => {
    try {
      await api.put(`/admin/rules/banned-words/${id}`, values);
      message.success('更新成功');
      loadBannedWords();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '更新失败');
    }
  };

  const handleDeleteBw = async (id: string) => {
    try {
      await api.delete(`/admin/rules/banned-words/${id}`);
      message.success('删除成功');
      loadBannedWords();
    } catch (e) {
      message.error('删除失败');
    }
  };

  // Replacements CRUD
  const handleCreateRp = async (values: any) => {
    try {
      await api.post('/admin/rules/replacements', {
        ...values,
        market: values.market.toUpperCase(),
      });
      message.success('添加成功');
      setRpModalVisible(false);
      rpForm.resetFields();
      loadReplacements();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '添加失败');
    }
  };

  const handleDeleteRp = async (id: string) => {
    try {
      await api.delete(`/admin/rules/replacements/${id}`);
      message.success('删除成功');
      loadReplacements();
    } catch (e) {
      message.error('删除失败');
    }
  };

  // Suggestions
  const handleApproveSuggestion = async (id: string) => {
    try {
      await api.post(`/admin/rules/suggestions/${id}/approve`);
      message.success('已批准并应用');
      loadSuggestions();
      loadBannedWords();
    } catch (e: any) {
      message.error(e.response?.data?.detail || '操作失败');
    }
  };

  const handleRejectSuggestion = async (id: string) => {
    try {
      await api.post(`/admin/rules/suggestions/${id}/reject`);
      message.success('已拒绝');
      loadSuggestions();
    } catch (e: any) {
      message.error('操作失败');
    }
  };

  // Banned Words Columns
  const bwColumns = [
    { title: '词汇', dataIndex: 'word', key: 'word', width: 150 },
    {
      title: '违规类型',
      dataIndex: 'violation_type',
      key: 'violation_type',
      width: 120,
      render: (v: string) => {
        const typeMap: Record<string, string> = {
          'medical_claim': '医疗宣称',
          'absolute_term': '绝对化用语',
          'banned_ingredient': '禁用成分',
          'medical': '医疗宣称',
        };
        return <Tag color="red">{typeMap[v] || v}</Tag>;
      }
    },
    { title: '市场', dataIndex: 'market', key: 'market', width: 80 },
    { title: '类别', dataIndex: 'category', key: 'category', width: 100 },
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (v: number) => (
        <Tag color={v >= 70 ? 'red' : v >= 40 ? 'orange' : 'green'}>{v}</Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => (
        <Badge status={v ? 'success' : 'default'} text={v ? '启用' : '禁用'} />
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: BannedWord) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingBw(record);
                bwForm.setFieldsValue({ severity: record.severity, is_active: record.is_active });
              }}
            />
          </Tooltip>
          <Popconfirm title="确定删除？" onConfirm={() => handleDeleteBw(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ];

  // Replacements Columns
  const rpColumns = [
    { title: '原词', dataIndex: 'original_word', key: 'original_word', width: 150 },
    { title: '替换词', dataIndex: 'replacement', key: 'replacement', width: 150 },
    { title: '市场', dataIndex: 'market', key: 'market', width: 80 },
    { title: '类别', dataIndex: 'category', key: 'category', width: 100 },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => (
        <Badge status={v ? 'success' : 'default'} text={v ? '启用' : '禁用'} />
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: any, record: Replacement) => (
        <Popconfirm title="确定删除？" onConfirm={() => handleDeleteRp(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      )
    }
  ];

  // Suggestions Columns
  const sugColumns = [
    {
      title: '类型',
      dataIndex: 'suggestion_type',
      key: 'suggestion_type',
      width: 100,
      render: (v: string) => (
        <Tag color={v === 'remove_word' ? 'orange' : 'blue'}>
          {v === 'remove_word' ? '移除词汇' : '添加词汇'}
        </Tag>
      )
    },
    { title: '违规类型', dataIndex: 'violation_type', key: 'violation_type', width: 120 },
    { title: '内容', dataIndex: 'content', key: 'content', ellipsis: true },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 80,
      render: (v: number) => `${Math.round(v * 100)}%`
    },
    { title: '反馈数', dataIndex: 'feedback_count', key: 'feedback_count', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (v: string) => {
        const colorMap: Record<string, string> = {
          pending: 'gold',
          approved: 'green',
          rejected: 'red',
        };
        const textMap: Record<string, string> = {
          pending: '待审核',
          approved: '已批准',
          rejected: '已拒绝',
        };
        return <Tag color={colorMap[v]}>{textMap[v]}</Tag>;
      }
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: Suggestion) => (
        record.status === 'pending' ? (
          <Space size="small">
            <Tooltip title="批准并应用">
              <Button
                size="small"
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => handleApproveSuggestion(record.id)}
              />
            </Tooltip>
            <Tooltip title="拒绝">
              <Button
                size="small"
                danger
                icon={<CloseOutlined />}
                onClick={() => handleRejectSuggestion(record.id)}
              />
            </Tooltip>
          </Space>
        ) : null
      )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>
        <HistoryOutlined /> 规则管理
      </Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'banned-words',
            label: `禁用词库 (${bwTotal})`,
            children: (
              <Card>
                <Space style={{ marginBottom: 16 }}>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setBwModalVisible(true)}
                  >
                    添加禁用词
                  </Button>
                  <Select
                    allowClear
                    placeholder="筛选市场"
                    style={{ width: 120 }}
                    value={bwFilters.market || undefined}
                    onChange={(v) => { setBwFilters({ ...bwFilters, market: v || '' }); setBwPage(1); }}
                    options={[
                      { value: 'EU', label: '欧盟' },
                      { value: 'US', label: '美国' },
                      { value: 'SEA_SG', label: '新加坡' },
                      { value: 'SEA_TH', label: '泰国' },
                      { value: 'SEA_MY', label: '马来西亚' },
                      { value: 'ALL', label: '通用' },
                    ]}
                  />
                  <Select
                    allowClear
                    placeholder="筛选违规类型"
                    style={{ width: 140 }}
                    value={bwFilters.violation_type || undefined}
                    onChange={(v) => { setBwFilters({ ...bwFilters, violation_type: v || '' }); setBwPage(1); }}
                    options={[
                      { value: 'medical_claim', label: '医疗宣称' },
                      { value: 'absolute_term', label: '绝对化用语' },
                      { value: 'banned_ingredient', label: '禁用成分' },
                    ]}
                  />
                </Space>

                <Table
                  columns={bwColumns}
                  dataSource={bannedWords}
                  rowKey="id"
                  loading={loading}
                  pagination={{
                    current: bwPage,
                    total: bwTotal,
                    pageSize: 20,
                    onChange: setBwPage,
                  }}
                  scroll={{ x: 800 }}
                  size="small"
                />
              </Card>
            ),
          },
          {
            key: 'replacements',
            label: `替换建议 (${rpTotal})`,
            children: (
              <Card>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  style={{ marginBottom: 16 }}
                  onClick={() => setRpModalVisible(true)}
                >
                  添加替换建议
                </Button>

                <Table
                  columns={rpColumns}
                  dataSource={replacements}
                  rowKey="id"
                  loading={loading}
                  pagination={{
                    current: rpPage,
                    total: rpTotal,
                    pageSize: 20,
                    onChange: setRpPage,
                  }}
                  size="small"
                />
              </Card>
            ),
          },
          {
            key: 'suggestions',
            label: `优化建议 (${suggestions.filter(s => s.status === 'pending').length})`,
            children: (
              <Card>
                <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                  基于用户反馈自动生成的规则优化建议，审核通过后将自动应用
                </Text>

                <Table
                  columns={sugColumns}
                  dataSource={suggestions}
                  rowKey="id"
                  loading={loading}
                  pagination={false}
                  size="small"
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Add Banned Word Modal */}
      <Modal
        title="添加禁用词"
        open={bwModalVisible}
        onCancel={() => { setBwModalVisible(false); bwForm.resetFields(); }}
        onOk={() => bwForm.submit()}
      >
        <Form form={bwForm} onFinish={handleCreateBw} layout="vertical">
          <Form.Item name="word" label="词汇" rules={[{ required: true }]}>
            <Input placeholder="输入禁用词" />
          </Form.Item>
          <Form.Item name="violation_type" label="违规类型" rules={[{ required: true }]}>
            <Select options={[
              { value: 'medical_claim', label: '医疗宣称' },
              { value: 'absolute_term', label: '绝对化用语' },
              { value: 'banned_ingredient', label: '禁用成分' },
            ]} />
          </Form.Item>
          <Form.Item name="market" label="市场" rules={[{ required: true }]}>
            <Select options={[
              { value: 'EU', label: '欧盟' },
              { value: 'US', label: '美国' },
              { value: 'SEA_SG', label: '新加坡' },
              { value: 'SEA_TH', label: '泰国' },
              { value: 'SEA_MY', label: '马来西亚' },
              { value: 'ALL', label: '通用' },
            ]} />
          </Form.Item>
          <Form.Item name="category" label="产品类别" rules={[{ required: true }]}>
            <Select options={[
              { value: '化妆品', label: '化妆品' },
              { value: '食品', label: '食品' },
              { value: '电子产品', label: '电子产品' },
              { value: '膳食补充剂', label: '膳食补充剂' },
              { value: 'all', label: '通用' },
            ]} />
          </Form.Item>
          <Form.Item name="severity" label="严重度 (0-100)" initialValue={50}>
            <Select options={[
              { value: 30, label: '低 (30)' },
              { value: 50, label: '中 (50)' },
              { value: 70, label: '高 (70)' },
              { value: 90, label: '严重 (90)' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Add Replacement Modal */}
      <Modal
        title="添加替换建议"
        open={rpModalVisible}
        onCancel={() => { setRpModalVisible(false); rpForm.resetFields(); }}
        onOk={() => rpForm.submit()}
      >
        <Form form={rpForm} onFinish={handleCreateRp} layout="vertical">
          <Form.Item name="original_word" label="原词" rules={[{ required: true }]}>
            <Input placeholder="需要替换的词汇" />
          </Form.Item>
          <Form.Item name="replacement" label="替换词" rules={[{ required: true }]}>
            <Input placeholder="合规的替换词汇" />
          </Form.Item>
          <Form.Item name="market" label="市场" rules={[{ required: true }]}>
            <Select options={[
              { value: 'EU', label: '欧盟' },
              { value: 'US', label: '美国' },
              { value: 'SEA_SG', label: '新加坡' },
              { value: 'SEA_TH', label: '泰国' },
              { value: 'SEA_MY', label: '马来西亚' },
              { value: 'ALL', label: '通用' },
            ]} />
          </Form.Item>
          <Form.Item name="category" label="产品类别" rules={[{ required: true }]}>
            <Select options={[
              { value: '化妆品', label: '化妆品' },
              { value: '食品', label: '食品' },
              { value: '电子产品', label: '电子产品' },
              { value: 'all', label: '通用' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Banned Word Modal */}
      <Modal
        title="编辑禁用词"
        open={!!editingBw}
        onCancel={() => setEditingBw(null)}
        onOk={() => {
          bwForm.validateFields().then((values) => {
            handleUpdateBw(editingBw!.id, values);
            setEditingBw(null);
          });
        }}
      >
        <Form form={bwForm} layout="vertical">
          <Form.Item name="severity" label="严重度">
            <Select options={[
              { value: 30, label: '低 (30)' },
              { value: 50, label: '中 (50)' },
              { value: 70, label: '高 (70)' },
              { value: 90, label: '严重 (90)' },
            ]} />
          </Form.Item>
          <Form.Item name="is_active" label="状态" valuePropName="checked">
            <Select options={[
              { value: true, label: '启用' },
              { value: false, label: '禁用' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
