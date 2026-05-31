import { type VercelConfig } from "@vercel/config/v1";

export const config: VercelConfig = {
  buildCommand: "npm run build",
  framework: "nextjs",
  // Vercel auto-detects the Python runtime from the .py file extension
  // (it provisions @vercel/python). Setting a custom `runtime` requires the
  // full versioned form like "@vercel/python@4.x.y"; "python3.13" alone
  // makes the build fail with "Function Runtimes must have a valid version".
  // Auto-detect avoids version churn.
  functions: {
    "api/compile.py": {
      memory: 1024,
      maxDuration: 60,
    },
    "api/ai.py": {
      memory: 512,
      maxDuration: 120,
    },
  },
};
