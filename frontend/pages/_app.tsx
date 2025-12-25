import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider } from '../contexts/AuthContext';
import { AppProps } from 'next/app';
import '../styles/globals.css';

// 自定义主题
const theme = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#f5222d',
    colorInfo: '#1890ff',
    borderRadius: 6,
    wireframe: false,
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      siderBg: '#ffffff',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#f0f5ff',
      itemHoverBg: '#f5f5f5',
    },
  },
};

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <AuthProvider>
        <Component {...pageProps} />
      </AuthProvider>
    </ConfigProvider>
  );
}

export default MyApp;