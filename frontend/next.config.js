/** @type {import('next').NextConfig} */
const path = require("path");

const nextConfig = {
  output: process.env.NODE_ENV === "production" ? "standalone" : undefined,

  images: {
    domains: ["localhost", "aidepartment.net", "api.aidepartment.net", "minio.aidepartment.net"],
  },

  webpack: (config, { dev, isServer }) => {
    // بهبود hot reload در Docker
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }

    // رفع خطاهای WebSocket
    config.externals.push({
      "utf-8-validate": "commonjs utf-8-validate",
      bufferutil: "commonjs bufferutil",
    });

    // ✅ مسیر alias دقیق و سازگار با Docker
    config.resolve.alias = {
      ...config.resolve.alias,
      "@": path.resolve(__dirname), // یعنی /app در Docker
    };

    // اضافه کردن مسیر پروژه به resolve.modules
    config.resolve.modules.push(path.resolve(__dirname));

    return config;
  },
};

module.exports = nextConfig;
