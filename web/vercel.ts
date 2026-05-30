import { type VercelConfig } from "@vercel/config/v1";

export const config: VercelConfig = {
  buildCommand: "npm run build",
  framework: "nextjs",
  functions: {
    "api/compile.py": {
      runtime: "python3.13",
      memory: 1024,
      maxDuration: 60,
    },
    "api/ai.py": {
      runtime: "python3.13",
      memory: 512,
      maxDuration: 120,
    },
  },
};
