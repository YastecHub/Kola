import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.KOLA_API_URL ?? process.env.NEXT_PUBLIC_KOLA_API_URL ?? "http://127.0.0.1:8001";
const API_KEY = process.env.KOLA_API_KEY;

export async function POST(request: Request) {
  if (!API_KEY) {
    return NextResponse.json(
      { error: "KOLA_API_KEY is required for group creation." },
      { status: 500 },
    );
  }

  try {
    const payload = await request.json();
    const response = await fetch(`${API_BASE_URL}/api/groups/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const body = await response.json().catch(() => ({}));

    if (!response.ok) {
      return NextResponse.json(
        { error: body.detail ?? "Unable to create group in KOLA backend." },
        { status: response.status },
      );
    }

    return NextResponse.json(body, { status: response.status });
  } catch (error) {
    console.error("Unable to proxy KOLA group creation", error);
    return NextResponse.json({ error: "Unable to reach KOLA backend." }, { status: 502 });
  }
}
