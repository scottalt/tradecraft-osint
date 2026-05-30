import { NextRequest, NextResponse } from "next/server";

const HITS: Map<string, { count: number; resetAt: number }> = new Map();
const WINDOW_MS = 60 * 60 * 1000;
const LIMIT = 3;

function clientIp(req: NextRequest): string {
  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) return fwd.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "0.0.0.0";
}

export function middleware(req: NextRequest) {
  if (!req.nextUrl.pathname.startsWith("/api/compile")) {
    return NextResponse.next();
  }
  const ip = clientIp(req);
  const now = Date.now();
  const entry = HITS.get(ip);
  if (!entry || now >= entry.resetAt) {
    HITS.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return NextResponse.next();
  }
  if (entry.count >= LIMIT) {
    const retryAfter = Math.ceil((entry.resetAt - now) / 1000);
    return new NextResponse(
      JSON.stringify({ error: "rate limit exceeded", retry_after: retryAfter }),
      {
        status: 429,
        headers: {
          "Content-Type": "application/json",
          "Retry-After": String(retryAfter),
        },
      },
    );
  }
  entry.count += 1;
  return NextResponse.next();
}

export const config = {
  matcher: "/api/compile/:path*",
};
