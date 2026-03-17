/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'https',
        hostname: 'aidepartment.net',
      },
      {
        protocol: 'https',
        hostname: 'api.aidepartment.net',
      },
    ],
  },
  // متغیرهای محیطی NEXT_PUBLIC_ باید در build time تنظیم شوند
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_AUTH_API_URL: process.env.NEXT_PUBLIC_AUTH_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  },
};

module.exports = nextConfig;