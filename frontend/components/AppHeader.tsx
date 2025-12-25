
import { Layout, Menu, Avatar, Dropdown, Space, Badge, Button } from 'antd';
import {
  DashboardOutlined,
  CameraOutlined,
  HistoryOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
  BellOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { useUIStore } from '../store';
import Link from 'next/link';
import { useRouter } from 'next/router';

const { Header } = Layout;

const AppHeader = () => {
  const { user, logout } = useAuth();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const router = useRouter();

  // 用户菜单
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
      onClick: () => router.push('/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
      onClick: () => router.push('/settings'),
    },
    {
      key: 'divider',
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: logout,
    },
  ];

  // 导航菜单
  const navItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: <Link href="/dashboard">仪表板</Link>,
    },
    {
      key: 'detection',
      icon: <CameraOutlined />,
      label: <Link href="/detection">病害检测</Link>,
    },
    {
      key: 'history',
      icon: <HistoryOutlined />,
      label: <Link href="/history">历史记录</Link>,
    },
  ];

  return (
    <Header className="flex items-center justify-between px-4 bg-white shadow-sm">
      <div className="flex items-center">
        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={toggleSidebar}
          className="mr-4 lg:hidden"
        />
        <div className="flex items-center">
          <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center mr-3">
            <CameraOutlined className="text-white text-lg" />
          </div>
          <h1 className="text-xl font-semibold text-secondary-900 hidden sm:block">
            植物病害检测系统
          </h1>
        </div>
        <Menu
          mode="horizontal"
          selectedKeys={[router.pathname.split('/')[1] || 'dashboard']}
          items={navItems}
          className="border-0 ml-8 hidden md:flex"
        />
      </div>

      <div className="flex items-center space-x-4">
        <Badge count={0} showZero={false}>
          <Button
            type="text"
            icon={<BellOutlined />}
            className="flex items-center justify-center"
          />
        </Badge>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space className="cursor-pointer">
            <Avatar
              src={user?.avatar}
              icon={<UserOutlined />}
              className="bg-primary-100 text-primary-600"
            />
            <span className="hidden sm:block text-secondary-700">
              {user?.username || '用户'}
            </span>
          </Space>
        </Dropdown>
      </div>
    </Header>
  );
};

export default AppHeader;