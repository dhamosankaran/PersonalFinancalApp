/** @type {import('next').NextConfig} */
const nextConfig = {
  // API rewrites for development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },

  // Disable strict mode for recharts compatibility
  reactStrictMode: false,

  // Image domains if needed
  images: {
    domains: ['localhost'],
  },
};

export default nextConfig;
