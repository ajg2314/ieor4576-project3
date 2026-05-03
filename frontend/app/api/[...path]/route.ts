import { NextRequest } from "next/server";
import { GoogleAuth } from "google-auth-library";

const DEFAULT_API_URL = "http://localhost:8000";
const auth = new GoogleAuth();

function isLocalApiUrl(apiUrl: string): boolean {
  try {
    const { hostname } = new URL(apiUrl);
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  } catch {
    return false;
  }
}

async function getAuthorizationHeader(apiUrl: string): Promise<string | null> {
  if (isLocalApiUrl(apiUrl)) {
    return null;
  }

  const audience = process.env.IAP_CLIENT_ID?.trim();
  if (!audience) {
    console.error("IAP_CLIENT_ID is required for authenticated backend proxy calls");
    return null;
  }
  try {
    const client = await auth.getIdTokenClient(audience);
    const headers = await client.getRequestHeaders(apiUrl);
    const authorization = headers.get("authorization");
    return typeof authorization === "string" ? authorization : null;
  } catch (error) {
    console.error("Failed to obtain backend identity token", error);
    return null;
  }
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
  const targetUrl = `${apiUrl.replace(/\/$/, "")}/${path.join("/")}${request.nextUrl.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("authorization");
  const authorization = await getAuthorizationHeader(apiUrl);
  if (authorization) {
    headers.set("authorization", authorization);
  }

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  const response = await fetch(targetUrl, {
    method: request.method,
    headers,
    body,
    redirect: "manual",
  });

  return new Response(response.body, {
    status: response.status,
    headers: response.headers,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
