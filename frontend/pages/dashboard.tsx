import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { Row, Col, Card, Statistic, Typography, Progress, List, Avatar, Tag, Space } from 'antd';
import { 
  CameraOutlined, 
  HistoryOutlined, 
  CheckCircleOutlined, 
  ClockCircleOutlined,
  UserOutlined,
  FileTextOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { useTaskStore } from '../store';
import AppLayout from '../components/AppLayout';

const { Title, Text } = Typography;

const DashboardPage = () => {
  const { user } = useAuth();
  const { tasks, fetchTasks } = useTaskStore();
  const router = useRouter();

  useEffect(() => {
    // 获取任务数据
    fetchTasks();
  }, [fetchTasks]);

  // 统计数据
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(task => task.status === 'completed').length;
  const pendingTasks = tasks.filter(task => task.status === 'pending').length;
  const processingTasks = tasks.filter(task => task.status === 'processing').length;
  const failedTasks = tasks.filter(task => task.status === 'failed').length;

  // 计算完成率
  const completionRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  // 最近的任务
  const recentTasks = tasks.slice(0, 5);

  // 任务状态映射
  const statusMap = {
    pending: { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' },
    processing: { color: 'processing', icon: <ClockCircleOutlined />, text: '处理中' },
    completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
    failed: { color: 'error', icon: <ClockCircleOutlined />, text: '失败' },
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* 欢迎标题 */}
        <div>
          <Title level={2}>
            欢迎回来，{user?.username || '用户'}！
          </Title>
          <Text type="secondary">
            这是您的植物病害检测系统仪表板，您可以在这里查看系统概览和最新动态。
          </Text>
        </div>

        {/* 统计卡片 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="总任务数"
                value={totalTasks}
                prefix={<FileTextOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="已完成"
                value={completedTasks}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="处理中"
                value={processingTasks}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="失败"
                value={failedTasks}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 进度卡片和最近任务 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="任务完成率" extra={<BarChartOutlined />}>
              <div className="space-y-4">
                <Progress
                  type="circle"
                  percent={completionRate}
                  width={120}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
                <div className="text-center">
                  <Text strong>总体完成率</Text>
                  <div className="mt-2">
                    <Text type="secondary">{completedTasks} / {totalTasks} 任务已完成</Text>
                  </div>
                </div>
              </div>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="最近任务" extra={<HistoryOutlined />}>
              <List
                dataSource={recentTasks}
                renderItem={(task) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<Avatar icon={<CameraOutlined />} />}
                      title={
                        <Space>
                          <span>{task.title || '未知任务'}</span>
                          <Tag color={statusMap[task.status]?.color}>
                            {statusMap[task.status]?.text}
                          </Tag>
                        </Space>
                      }
                      description={
                        <Space direction="vertical" size="small">
                          <Text type="secondary" className="text-xs">
                            创建时间: {new Date(task.created_at).toLocaleString()}
                          </Text>
                          {task.status === 'completed' && task.result && (
                            <Text type="secondary" className="text-xs">
                              结果: {task.result.disease_name || '未知病害'}
                            </Text>
                          )}
                        </Space>
                      }
                    />
                  </List.Item>
                )}
                locale={{ emptyText: '暂无任务记录' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 快速操作 */}
        <Card title="快速操作">
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card 
            hoverable 
            className="text-center cursor-pointer"
            onClick={() => router.push('/detection')}
          >
                <CameraOutlined className="text-4xl text-primary-500 mb-2" />
                <div>开始检测</div>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card 
            hoverable 
            className="text-center cursor-pointer"
            onClick={() => router.push('/history')}
          >
                <HistoryOutlined className="text-4xl text-primary-500 mb-2" />
                <div>查看历史</div>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card 
            hoverable 
            className="text-center cursor-pointer"
            onClick={() => router.push('/models')}
          >
                <BarChartOutlined className="text-4xl text-primary-500 mb-2" />
                <div>模型管理</div>
              </Card>
            </Col>
          </Row>
        </Card>
      </div>
    </AppLayout>
  );
};

export default DashboardPage;