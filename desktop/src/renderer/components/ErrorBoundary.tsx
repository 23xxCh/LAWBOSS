import { Component } from 'react';
import { Card, Button, Typography } from 'antd';
import { WarningOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ maxWidth: 500, margin: '80px auto', padding: '0 16px' }}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <WarningOutlined style={{ fontSize: 48, color: '#ff4d4f', marginBottom: 16 }} />
              <Title level={4}>页面渲染异常</Title>
              <Paragraph type="secondary">
                应用遇到了意外错误，请尝试刷新页面。
                {this.state.error && (
                  <details style={{ marginTop: 8, textAlign: 'left' }}>
                    <summary>错误详情</summary>
                    <pre style={{ fontSize: 12, marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {this.state.error.message}
                    </pre>
                  </details>
                )}
              </Paragraph>
              <Button type="primary" onClick={() => window.location.reload()}>
                刷新页面
              </Button>
            </div>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}
