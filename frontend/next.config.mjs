/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained Node server output so the production image can ship just
  // `.next/standalone` + `.next/static` + `public/` (see frontend/Dockerfile).
  output: "standalone",
  experimental: {},
};

export default nextConfig;
