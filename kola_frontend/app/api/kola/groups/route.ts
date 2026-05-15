import { NextResponse } from "next/server";
import { proxyKolaJson } from "@/lib/kolaBackend";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const result = await proxyKolaJson("/api/groups/", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    return NextResponse.json(result.body, { status: result.status });
  } catch (error) {
    console.error("Unable to proxy KOLA group creation", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to reach KOLA backend." },
      { status: 502 },
    );
  }
}
