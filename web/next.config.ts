import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async redirects() {
    return [{ source: "/settings/fx", destination: "/planning-rates", permanent: true }];
  },
};

export default nextConfig;
