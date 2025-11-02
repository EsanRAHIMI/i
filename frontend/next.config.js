/** @type {import('next').NextConfig} */
const nextConfig = {
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  images: {
    domains: ['localhost'],
  },
  // Optimize for development hot reload
  webpack: (config, { dev }) => {
    // Enable polling in Docker for better file watching
    if (dev) {
      config.watchOptions = {
        poll: 1000, // Check for changes every second (useful in Docker)
        aggregateTimeout: 300, // Delay before reloading
      };
    }
    config.externals.push({
      'utf-8-validate': 'commonjs utf-8-validate',
      'bufferutil': 'commonjs bufferutil',
    });
    return config;
  },
};

module.exports = nextConfig;