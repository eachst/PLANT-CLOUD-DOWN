import { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, Divider } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, CameraOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;

const RegisterPage = () => {
  const [form] = Form.useForm();
  const { register, isLoading, error, clearError } = useAuth();
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (values: {
    username: string;
    email: string;
    password: string;
    confirmPassword: string;
  }) => {
    try {
      setSubmitted(true);
      await register({
        username: values.username,
        email: values.email,
        password: values.password
      });
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
            创建新账户
          </Title>
          <Text className="mt-2 text-center text-sm text-secondary-600">
            注册以开始使用植物病害检测系统
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
            name="register"
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
                { max: 20, message: '用户名最多20个字符' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="请输入用户名"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="email"
              label="邮箱"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="请输入邮箱"
                autoComplete="email"
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="密码"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
                { max: 20, message: '密码最多20个字符' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="请输入密码"
                autoComplete="new-password"
              />
            </Form.Item>

            <Form.Item
              name="confirmPassword"
              label="确认密码"
              dependencies={['password']}
              rules={[
                { required: true, message: '请确认密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="请再次输入密码"
                autoComplete="new-password"
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
                注册
              </Button>
            </Form.Item>
          </Form>

          <Divider>或</Divider>

          <div className="text-center">
            <Text type="secondary">
              已有账户？{' '}
              <Link href="/login" className="font-medium text-primary-600 hover:text-primary-500">
                立即登录
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

export default RegisterPage;