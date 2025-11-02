/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,

  images: {
    domains: ['localhost', 'aidepartment.net', 'api.aidepartment.net', 'minio.aidepartment.net'],
  },

  webpack: (config, { dev }) => {
    // بهبود hot reload برای Docker
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }

    // رفع خطای WebSocket باینری
    config.externals.push({
      'utf-8-validate': 'commonjs utf-8-validate',
      bufferutil: 'commonjs bufferutil',
    });

    // ✅ مسیر alias اصلاح شد تا در Dokploy و Docker درست resolve بشه
    config.resolve.alias['@'] = path.resolve(__dirname, '.');

    // اضافه کردن پشتیبانی از TS path mappings
    config.resolve.modules.push(path.resolve(__dirname));

    return config;
  },
};

module.exports = nextConfig;
