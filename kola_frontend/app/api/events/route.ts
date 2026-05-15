import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.KOLA_API_URL ?? process.env.NEXT_PUBLIC_KOLA_API_URL ?? "http://127.0.0.1:8001";
const AMINAT_PHONE_OR_ID = process.env.AMINAT_PHONE_OR_ID ?? process.env.NEXT_PUBLIC_AMINAT_PHONE_OR_ID ?? "08012345678";
const API_KEY = process.env.KOLA_API_KEY;

function eventTitle(event: Record<string, unknown>) {
  const type = String(event.event_type ?? "contribution");
  return type.toLowerCase().includes("trade") ? "Trade payment received" : "Contribution received";
}

function formatAmount(event: Record<string, unknown>) {
  const amount = Number(event.amount ?? 0);
  const currency = String(event.currency ?? "NGN");
  if (!Number.isFinite(amount) || amount <= 0) return currency === "NGN" ? "N0" : `${currency} 0`;
  return currency === "NGN" ? `N${amount.toLocaleString()}` : `${currency} ${amount.toLocaleString()}`;
}

function mapEvent(event: Record<string, unknown>, index: number) {
  const occurredAt = event.occurred_at ? new Date(String(event.occurred_at)) : new Date();
  const verified = Boolean(event.verified);

  return {
    id: String(event.id ?? event.transaction_reference ?? `${occurredAt.toISOString()}-${index}`),
    title: eventTitle(event),
    amount: formatAmount(event),
    meta: `${occurredAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · ${verified ? "Squad verified" : "Pending verification"}`,
  };
}

async function fetchEvents() {
  const response = await fetch(`${API_BASE_URL}/api/scores/trader/${AMINAT_PHONE_OR_ID}`, {
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined,
    cache: "no-store",
  });

  if (!response.ok) return [];

  const score = await response.json();
  const events = Array.isArray(score.events) ? score.events : [];
  return events.slice(0, 8).map(mapEvent);
}

export async function GET(request: Request) {
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      let closed = false;

      request.signal.addEventListener("abort", () => {
        closed = true;
        controller.close();
      });

      const send = async () => {
        if (closed) return;
        try {
          const events = await fetchEvents();
          controller.enqueue(encoder.encode(`event: kola-events\ndata: ${JSON.stringify(events)}\n\n`));
        } catch (error) {
          controller.enqueue(encoder.encode(`event: kola-error\ndata: ${JSON.stringify({ message: "Unable to stream KOLA events" })}\n\n`));
        }
      };

      await send();
      const timer = setInterval(send, 8000);

      request.signal.addEventListener("abort", () => {
        clearInterval(timer);
      });
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
