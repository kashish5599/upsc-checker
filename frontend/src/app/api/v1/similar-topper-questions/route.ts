import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const backendUrl = (
    process.env.BACKEND_API_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "");

  try {
    const query = new URL(request.url).searchParams.toString();
    const upstream = await fetch(
      `${backendUrl}/api/v1/similar-topper-questions${query ? `?${query}` : ""}`,
      { method: "GET", cache: "no-store" },
    );
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json(null, { status: 502 });
  }
}
