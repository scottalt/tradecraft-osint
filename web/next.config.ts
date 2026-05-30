import type { NextConfig } from "next";

// When DEPLOY_TARGET=pages, build a static export suitable for GitHub Pages.
// In demo-only static mode the API routes don't exist (no Python backend);
// the form is rendered but submission shows a "design preview" notice.
const isPages = process.env.DEPLOY_TARGET === "pages";

const config: NextConfig = {
  reactStrictMode: true,
  ...(isPages
    ? {
        output: "export",
        basePath: "/tradecraft-osint",
        assetPrefix: "/tradecraft-osint",
        images: { unoptimized: true },
      }
    : {}),
};

export default config;
