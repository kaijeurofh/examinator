/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained Node server output so the production image can ship just
  // `.next/standalone` + `.next/static` + `public/` (see frontend/Dockerfile).
  output: "standalone",
  experimental: {},
  // Reverse-proxy `/api/*` to the FastAPI backend so the browser only ever
  // talks to the Next.js origin. This removes the need to bake a public
  // backend URL into the client bundle (which would break VPN / LAN access
  // where the browser cannot resolve `localhost` to the host machine) and
  // sidesteps CORS entirely. The destination is taken at runtime from
  // BACKEND_INTERNAL_URL so the same image can target any backend
  // location; inside docker-compose this defaults to the service DNS name.
  async rewrites() {
    const target = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${target}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
