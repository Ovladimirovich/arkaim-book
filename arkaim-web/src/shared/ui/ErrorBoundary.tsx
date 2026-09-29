'use client';

import React from 'react';
import { Result, Button } from 'antd';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <Result
          status="error"
          title="Произошла ошибка"
          subTitle={this.state.error?.message || 'Неизвестная ошибка'}
          extra={
            <Button type="primary" onClick={() => this.setState({ hasError: false, error: null })}>
              Попробовать снова
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
