/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    // Product images are served from Tesco's CDN; we render them unoptimized
    // to avoid the Next image optimizer needing outbound access in Docker.
    unoptimized: true,
  },
};

export default nextConfig;
