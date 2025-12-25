import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  CameraOutlined,
  HistoryOutlined,
  SettingOutlined,
  FileTextOutlined,
  BarChartOutlined,
  TeamOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/router';
import { useUIStore } from '../store';
import Link from 'next/link';

const { Sider } = Layout;

const AppSidebar = () => {
  const { sidebarOpen } = useUIStore();
  const router = useRouter();

  // 菜单项
  const menuItems = [
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
    {
      key: 'models',
      icon: <DatabaseOutlined />,
      label: <Link href="/models">模型管理</Link>,
    },
    {
      key: 'statistics',
      icon: <BarChartOutlined />,
      label: <Link href="/statistics">统计分析</Link>,
    },
    {
      key: 'users',
      icon: <TeamOutlined />,
      label: <Link href="/users">用户管理</Link>,
    },
    {
      key: 'logs',
      icon: <FileTextOutlined />,
      label: <Link href="/logs">系统日志</Link>,
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: <Link href="/settings">系统设置</Link>,
    },
  ];

  // 获取当前选中的菜单项
  const selectedKey = router.pathname.split('/')[1] || 'dashboard';

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={!sidebarOpen}
      className="fixed left-0 top-0 h-full z-30 shadow-lg"
      theme="light"
      width={250}
      collapsedWidth={0}
    >
      <div className="flex flex-col h-full">
        {/* Logo区域 */}
        <div className="flex items-center justify-center h-16 border-b border-secondary-200">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center mr-3">
              <CameraOutlined className="text-white text-lg" />
            </div>
            <h1 className="text-lg font-semibold text-secondary-900">
              植物病害检测
            </h1>
          </div>
        </div>

        {/* 菜单区域 */}
        <div className="flex-1 overflow-y-auto py-4">
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={menuItems}
            className="border-0"
          />
        </div>

        {/* 底部信息 */}
        <div className="p-4 border-t border-secondary-200">
          <div className="text-xs text-secondary-500">
            版本: 1.0.0
          </div>
        </div>
      </div>
    </Sider>
  );
};

export default AppSidebar;