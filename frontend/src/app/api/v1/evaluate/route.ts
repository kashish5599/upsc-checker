import { NextResponse } from "next/server";

/** Same-origin proxy keeps browser uploads compatible with the backend's current CORS setup. */
export async function POST(request: Request) {
  const backendUrl = (
    process.env.BACKEND_API_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/$/, "");

  try {
    const formData = await request.formData();
    const upstream = await fetch(`${backendUrl}/api/v1/evaluate`, {
      method: "POST",
      body: formData,
      cache: "no-store",
    });
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "The evaluation service is unavailable. Check that the backend is running, then try again." },
      { status: 502 },
    );
  }
}
