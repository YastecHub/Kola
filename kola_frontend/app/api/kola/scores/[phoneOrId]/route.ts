import { NextResponse } from "next/server";
import { proxyKolaJson } from "@/lib/kolaBackend";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: { phoneOrId: string } }) {
  try {
    const result = await proxyKolaJson(`/api/scores/trader/${encodeURIComponent(params.phoneOrId)}`);
    return NextResponse.json(result.body, { status: result.status });
  } catch (error) {
    console.error("Unable to fetch trader score from KOLA backend", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to reach KOLA backend." },
      { status: 502 },
    );
  }
}
