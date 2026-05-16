export type KolaScore = {
  member_id?: string;
  score: number;
  confidence: string;
  anomaly_flag: boolean;
  shap: {
    streak: number;
    trade: number;
    catchup: number;
    collector: number;
    amount_std: number;
  };
  verified_events_count?: number;
  streak_weeks?: number;
  last_updated?: string;
  events?: KolaEconomicEvent[];
};

export type KolaEconomicEvent = {
  id?: string;
  source?: string;
  event_type?: string;
  transaction_reference?: string | null;
  amount?: string | number | null;
  currency?: string;
  occurred_at?: string;
  verified?: boolean;
};

export type KolaMember = {
  id: string;
  group_id: string;
  full_name: string;
  phone: string;
  email: string | null;
  squad_customer_id: string | null;
  squad_va_id: string | null;
  squad_va_number: string | null;
  squad_va_bank: string | null;
  created_at: string;
};

export type KolaGroup = {
  id: string;
  name: string;
  description: string | null;
  contribution_amount: string | null;
  contribution_frequency: string;
  created_at: string;
  members: KolaMember[];
};

export type CreateGroupPayload = {
  name: string;
  description?: string;
  contribution_amount?: string;
  contribution_frequency: string;
  members: Array<{
    full_name: string;
    phone: string;
    email?: string;
    bvn?: string;
    dob?: string;
    gender?: string;
    address?: string;
  }>;
};

type BackendScore = {
  member_id?: string;
  score?: number;
  kola_score?: number;
  confidence?: string;
  anomaly_flag?: boolean;
  shap?: Partial<KolaScore["shap"]>;
  explanation?: {
    confidence?: string;
    anomaly_flag?: boolean;
    shap?: Partial<KolaScore["shap"]>;
  };
  verified_events_count?: number;
  streak_weeks?: number;
  last_updated?: string;
  events?: KolaEconomicEvent[];
};

export const demoAminatScore: KolaScore = {
  score: 714,
  confidence: "Good - Low Risk",
  anomaly_flag: false,
  shap: {
    streak: 18,
    trade: 12,
    catchup: 8,
    collector: 4,
    amount_std: -6,
  },
};

function normalizeScore(data: BackendScore): KolaScore {
  const shap = data.shap ?? data.explanation?.shap ?? {};

  return {
    member_id: data.member_id,
    score: data.score ?? data.kola_score ?? 0,
    confidence: data.confidence ?? data.explanation?.confidence ?? "Good - Low Risk",
    anomaly_flag: data.anomaly_flag ?? data.explanation?.anomaly_flag ?? false,
    shap: {
      streak: shap.streak ?? 0,
      trade: shap.trade ?? 0,
      catchup: shap.catchup ?? 0,
      collector: shap.collector ?? 0,
      amount_std: shap.amount_std ?? 0,
    },
    verified_events_count: data.verified_events_count,
    streak_weeks: data.streak_weeks,
    last_updated: data.last_updated,
    events: data.events ?? [],
  };
}

export async function fetchAminatScore(): Promise<KolaScore> {
  const response = await fetch("/api/kola/aminat-score");

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error ?? `Failed to fetch Aminat score: ${response.status}`);
  }

  return normalizeScore((await response.json()) as BackendScore);
}

export async function fetchTraderScore(phoneOrId: string): Promise<KolaScore> {
  const response = await fetch(`/api/kola/scores/${encodeURIComponent(phoneOrId)}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error ?? `Failed to fetch trader score: ${response.status}`);
  }

  return normalizeScore((await response.json()) as BackendScore);
}

export async function createKolaGroup(payload: CreateGroupPayload): Promise<KolaGroup> {
  const response = await fetch("/api/kola/groups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error ?? `Failed to create group: ${response.status}`);
  }

  return response.json() as Promise<KolaGroup>;
}

const AI_API_URL = process.env.KOLA_AI_URL ?? "https://web-production-48a47.up.railway.app";
const AI_API_KEY = process.env.KOLA_AI_KEY ?? "kola-dev-key-2025";

export async function fetchAminatAiScore(): Promise<KolaScore> {
  const res = await fetch(`${AI_API_URL}/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Api-Key": AI_API_KEY,
    },
    body: JSON.stringify({
      member_id: "aminat-001",
      collector_trust: 1,
      events: [
        { type: "contribution", week: 1,  amount: 5200, date: "2025-01-07", days_late: 0 },
        { type: "contribution", week: 2,  amount: 4900, date: "2025-01-14", days_late: 0 },
        { type: "contribution", week: 3,  amount: 5000, date: "2025-01-21", days_late: 0 },
        { type: "contribution", week: 4,  amount: 5100, date: "2025-01-28", days_late: 0 },
        { type: "contribution", week: 5,  amount: 4800, date: "2025-02-04", days_late: 0 },
        { type: "contribution", week: 6,  amount: 5000, date: "2025-02-11", days_late: 0 },
        { type: "contribution", week: 7,  amount: 5300, date: "2025-02-21", days_late: 3 },
        { type: "contribution", week: 8,  amount: 4700, date: "2025-02-25", days_late: 0 },
        { type: "contribution", week: 9,  amount: 5100, date: "2025-03-04", days_late: 0 },
        { type: "contribution", week: 10, amount: 4900, date: "2025-03-11", days_late: 0 },
        { type: "contribution", week: 11, amount: 5000, date: "2025-03-18", days_late: 0 },
        { type: "contribution", week: 12, amount: 5200, date: "2025-03-25", days_late: 0 },
        { type: "contribution", week: 13, amount: 4800, date: "2025-04-01", days_late: 0 },
      ],
      trade_events: [
        { type: "trade", amount: 47500, date: "2025-05-05", counterparty_nuban: "9034512987" },
        { type: "trade", amount: 52000, date: "2025-03-10", counterparty_nuban: "9034512987" },
      ],
    }),
  });

  if (!res.ok) throw new Error("KOLA AI API error");

  const data = await res.json();

  return {
    score: data.score,
    confidence: data.confidence,
    anomaly_flag: data.anomaly_flag ?? false,
    shap: {
      streak: data.shap?.streak ?? 0,
      trade: data.shap?.trade ?? 0,
      catchup: data.shap?.catchup ?? 0,
      collector: data.shap?.collector ?? 0,
      amount_std: data.shap?.amount_std ?? 0,
    },
    verified_events_count: data.weeks_of_history,
  };
}