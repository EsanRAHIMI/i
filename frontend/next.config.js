/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['localhost', 'aidepartment.net', 'api.aidepartment.net'],
  },
  webpack: (config, { isServer }) => {
    config.externals.push({
      'utf-8-validate': 'commonjs utf-8-validate',
      'bufferutil': 'commonjs bufferutil',
    });
    
    // Ensure proper module resolution for workspace setup
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
      };
    }
    
    // Add resolve paths for workspace dependencies
    config.resolve.modules = [
      ...(config.resolve.modules || []),
      require('path').resolve(__dirname, 'node_modules'),
      require('path').resolve(__dirname, '../node_modules'),
    ];
    
    return config;
  },
  // متغیرهای محیطی NEXT_PUBLIC_ باید در build time تنظیم شوند
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  },
};

module.exports = nextConfig;