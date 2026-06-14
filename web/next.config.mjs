/** @type {import('next').NextConfig} */
const nextConfig = {
  // Lint is run separately; don't fail production builds on style lint.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
