/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      { hostname: 'localhost' },
      { hostname: 'api-gateway' },
      { hostname: 'model-service' },
      { hostname: 'task-service' },
    ],
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://api-gateway';
    const normalizedApiUrl = apiUrl.endsWith('/api') ? apiUrl.slice(0, -4) : apiUrl;

    return [
      {
        source: '/api/:path*',
        // 让前端统一以 /api 为前缀；转发到后端时去掉 /api
        destination: `${normalizedApiUrl}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;