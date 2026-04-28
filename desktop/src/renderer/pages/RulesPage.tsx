import { useState, useEffect } from 'react';
import { Card, Select, Tag, Space, Spin, Typography } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { getMarkets, getLabels, getCertifications, type MarketResponse } from '../api';

const { Paragraph } = Typography;

export default function RulesPage() {
  const [markets, setMarkets] = useState<MarketResponse[]>([]);
  const [market, setMarket] = useState<string>('EU');
  const [category, setCategory] = useState<string>('');
  const [labels, setLabels] = useState<string[]>([]);
  const [certs, setCerts] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getMarkets().then((data) => {
      setMarkets(data);
      if (data.length > 0) {
        setMarket(data[0].code);
        setCategory(data[0].categories[0] || '');
      }
    });
  }, []);

  useEffect(() => {
    if (market && category) {
      setLoading(true);
      Promise.all([
        getLabels(market, category),
        getCertifications(market, category),
      ])
        .then(([labelRes, certRes]) => {
          setLabels(labelRes.labels);
          setCerts(certRes.certifications);
        })
        .finally(() => setLoading(false));
    }
  }, [market, category]);

  const currentMarket = markets.find((m) => m.code === market);
  const categories = currentMarket?.categories || [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '24px 16px' }}>
      <Card title="法规查询">
        <Space wrap style={{ marginBottom: 16 }}>
          <span>目标市场：</span>
          <Select
            value={market}
            onChange={(v) => {
              setMarket(v);
              const m = markets.find((m) => m.code === v);
              setCategory(m?.categories[0] || '');
            }}
            style={{ width: 120 }}
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

        {loading ? (
          <Spin />
        ) : (
          <Space orientation="vertical" style={{ width: '100%' }} size="large">
            <Card type="inner" title="必需标签">
              {labels.length > 0 ? (
                <Space wrap>
                  {labels.map((label, i) => (
                    <Tag key={i} icon={<ExclamationCircleOutlined />} color="blue">
                      {label}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <Paragraph type="secondary">请查阅目标市场法规</Paragraph>
              )}
            </Card>

            <Card type="inner" title="必需认证">
              {certs.length > 0 ? (
                <Space wrap>
                  {certs.map((cert, i) => (
                    <Tag key={i} icon={<ExclamationCircleOutlined />} color="purple">
                      {cert}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <Paragraph type="secondary">请查阅目标市场法规</Paragraph>
              )}
            </Card>
          </Space>
        )}
      </Card>
    </div>
  );
}
