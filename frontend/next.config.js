/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  images: {
    // اگر از دامنه‌های خارجی استفاده می‌کنی اینجا اضافه کن
    domains: ['localhost', 'aidepartment.net', 'api.aidepartment.net', 'minio.aidepartment.net'],
  },
  webpack: (config, { dev }) => {
    // بهبود watch داخل Docker
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }

    // بعضی پکیج‌های WebSocket باینری لازم ندارند
    config.externals.push({
      'utf-8-validate': 'commonjs utf-8-validate',
      bufferutil: 'commonjs bufferutil',
    });

    // تضمین اینکه alias ریشه پروژه با @ کار کند (علاوه بر paths در tsconfig)
    config.resolve.alias['@'] = path.resolve(__dirname);

    return config;
  },
};

module.exports = nextConfig;
