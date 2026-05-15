import { NextResponse } from "next/server";
import { demoAminatScore } from "@/lib/kolaApi";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.KOLA_API_URL ?? process.env.NEXT_PUBLIC_KOLA_API_URL ?? "http://127.0.0.1:8001";
const API_KEY = process.env.KOLA_API_KEY;

export async function GET(_request: Request, { params }: { params: { phoneOrId: string } }) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/scores/trader/${encodeURIComponent(params.phoneOrId)}`, {
      headers: API_KEY ? { "X-API-Key": API_KEY } : undefined,
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Unable to fetch trader score from KOLA backend", error);
    return NextResponse.json(
      {
        ...demoAminatScore,
        source: "demo-fallback",
      },
      { status: 200 },
    );
  }
}
