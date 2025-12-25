import { Layout } from 'antd';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';
import { useUIStore } from '../store';

const { Content } = Layout;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout = ({ children }: AppLayoutProps) => {
  const { sidebarOpen } = useUIStore();

  return (
    <Layout className="min-h-screen">
      <AppSidebar />
      <Layout className={`transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
        <AppHeader />
        <Content className="p-6 bg-secondary-50 min-h-full">
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;