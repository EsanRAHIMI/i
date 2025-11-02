/** @type {import('next').NextConfig} */
const path = require("path");

const isProd = process.env.NODE_ENV === "production";

const nextConfig = {
  reactStrictMode: true,

  // فقط در پروداکشن خروجی standalone بساز
  output: isProd ? "standalone" : undefined,

  images: {
    // اگر CDN/دامنه‌های جدید اضافه می‌کنی اینجا اضافه کن
    domains: ["localhost", "aidepartment.net", "api.aidepartment.net", "minio.aidepartment.net"],
  },

  // بیلد پروداکشن را به خاطر ESLint/TS ارور متوقف نکن (اختیاری ولی کمک‌کننده در CI)
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false }, // اگر خواستی موقتاً عبور کند: true

  // اگر پکیج‌های ESM/مونورپو داری که باید ترنسپایل شوند، اضافه کن
  // transpilePackages: ["your-shared-ui", "some-esm-only-lib"],

  // بهینه‌سازی درخواست‌ها
  httpAgentOptions: { keepAlive: true },

  webpack: (config, { dev, isServer }) => {
    // Hot reload داخل Docker
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }

    // جلو‌گیری از خطای ماژول‌های نیتیو ws در کلاینت
    config.externals = config.externals || [];
    config.externals.push({
      "utf-8-validate": "commonjs utf-8-validate",
      bufferutil: "commonjs bufferutil",
    });

    // فالبک برای ماژول‌های Node در کلاینت
    if (!isServer) {
      config.resolve.fallback = {
        ...(config.resolve.fallback || {}),
        fs: false,
        net: false,
        tls: false,
      };
    }

    // alias ریشه پروژه
    // جلوگیری از دو نسخه React - همیشه از نسخه اصلی استفاده کن
    // این مشکل معمولاً در مونورپو/سیم‌لینک رخ می‌دهد
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "@": path.resolve(__dirname),
      react: path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
    };

    // امکان import از ریشه (بدون '../')
    if (!config.resolve.modules.includes(path.resolve(__dirname))) {
      config.resolve.modules.push(path.resolve(__dirname));
    }

    return config;
  },
};

module.exports = nextConfig;
