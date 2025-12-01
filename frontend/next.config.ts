import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',  // Static export for Firebase Hosting
  trailingSlash: true,  // Required for Firebase Hosting SPA routing
  images: {
    unoptimized: true,  // Required for static export
  },
};

export default nextConfig;
