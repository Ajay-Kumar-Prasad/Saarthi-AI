import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: [
    "3000-cs-199837079470-default.cs-asia-southeast1-fork.cloudshell.dev",
    "*.cloudshell.dev",
  ],
  webpack: (config) => {
    config.resolve.modules = [
      path.resolve(__dirname, "node_modules"),
      "node_modules",
    ];
    return config;
  },
};

export default nextConfig;