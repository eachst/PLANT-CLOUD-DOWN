import { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, Divider } from 'antd';
import { UserOutlined, LockOutlined, CameraOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;

const LoginPage = () => {
  const [form] = Form.useForm();
  const { login, isLoading, error, clearError } = useAuth();
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (values: { username: string; password: string }) => {
    try {
      setSubmitted(true);
      await login(values.username, values.password);
    } catch (error) {
      setSubmitted(false);
    }
  };

  // 清除错误信息
  const handleFormChange = () => {
    if (error) {
      clearError();
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-primary-500 rounded-full flex items-center justify-center">
            <CameraOutlined className="text-white text-2xl" />
          </div>
          <Title level={2} className="mt-6 text-center text-3xl font-extrabold text-secondary-900">
            植物病害检测系统
          </Title>
          <Text className="mt-2 text-center text-sm text-secondary-600">
            登录您的账户以开始使用
          </Text>
        </div>

        <Card className="shadow-hard">
          {error && (
            <Alert
              message={error}
              type="error"
              showIcon
              closable
              onClose={clearError}
              className="mb-4"
            />
          )}

          <Form
            form={form}
            name="login"
            onFinish={handleSubmit}
            onChange={handleFormChange}
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="username"
              label="用户名"
              rules={[
                { required: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3个字符' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="请输入用户名"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="密码"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="请输入密码"
                autoComplete="current-password"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={isLoading}
                block
                className="h-12"
              >
                登录
              </Button>
            </Form.Item>
          </Form>

          <Divider>或</Divider>

          <div className="text-center">
            <Text type="secondary">
              还没有账户？{' '}
              <Link href="/register" className="font-medium text-primary-600 hover:text-primary-500">
                立即注册
              </Link>
            </Text>
          </div>
        </Card>

        <div className="text-center">
          <Text type="secondary" className="text-xs">
            © 2023 植物病害检测系统. 保留所有权利.
          </Text>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;