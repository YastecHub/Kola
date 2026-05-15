import { NextResponse } from "next/server";
import { proxyKolaJson } from "@/lib/kolaBackend";

export const dynamic = "force-dynamic";

const AMINAT_PHONE_OR_ID = process.env.AMINAT_PHONE_OR_ID ?? process.env.NEXT_PUBLIC_AMINAT_PHONE_OR_ID ?? "08012345678";

export async function GET() {
  try {
    const result = await proxyKolaJson(`/api/scores/trader/${encodeURIComponent(AMINAT_PHONE_OR_ID)}`);
    return NextResponse.json(result.body, { status: result.status });
  } catch (error) {
    console.error("Unable to fetch Aminat score from KOLA backend", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to reach KOLA backend." },
      { status: 502 },
    );
  }
}
