/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
  // خروجی standalone برای Docker و Dokploy
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,

  // پشتیبانی از تصاویر
  images: {
    domains: [
      'localhost',
      'aidepartment.net',
      'api.aidepartment.net',
      'minio.aidepartment.net',
    ],
  },

  webpack: (config, { dev, isServer }) => {
    // بهبود عملکرد hot reload در Docker
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }

    // حذف وابستگی‌های باینری غیرضروری WebSocket
    config.externals.push({
      'utf-8-validate': 'commonjs utf-8-validate',
      bufferutil: 'commonjs bufferutil',
    });

    // ✅ اصلاح alias برای Docker build و path resolve
    config.resolve.alias['@'] = path.resolve(__dirname);

    return config;
  },
};

module.exports = nextConfig;
