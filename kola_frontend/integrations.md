The AI API is deployed. You need to replace the hardcoded data in
`lib/data.ts` with a real fetch. Here is exactly what to do.

---

## API Details

- URL: `https://web-production-48a47.up.railway.app`
- Key: `kola-dev-key-2025`
- Endpoint: `POST /score`
- Interactive docs: `https://web-production-48a47.up.railway.app/docs`

---

## Step 1 — Create this file: `lib/kolaApi.ts`

```typescript
const KOLA_API = "https://web-production-48a47.up.railway.app";
const KOLA_KEY = "kola-dev-key-2025";

export interface KolaScore {
  score: number;
  probability: number;
  shap: {
    streak: number;
    catchup: number;
    amount_std: number;
    collector: number;
    trade: number;
  };
  anomaly_flag: boolean;
  anomaly_reason: string | null;
  weeks_of_history: number;
  confidence: string;
  confidence_detail: string;
}

export async function fetchAminatScore(): Promise<KolaScore> {
  const res = await fetch(`${KOLA_API}/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Api-Key": KOLA_KEY,
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

  if (!res.ok) throw new Error("KOLA API error");
  return res.json();
}
```

---

## Step 2 — Use it in the score page

In whichever component renders Aminat's score page, replace the hardcoded
imports with a live fetch. Example using React:

```typescript
import { useEffect, useState } from "react";
import { fetchAminatScore, KolaScore } from "@/lib/kolaApi";

export default function AminatScorePage() {
  const [data, setData] = useState<KolaScore | null>(null);

  useEffect(() => {
    fetchAminatScore().then(setData).catch(console.error);
  }, []);

  if (!data) return <div>Loading score...</div>;

  // Replace hardcoded values:
  // data.score           → the KOLA score (828)
  // data.shap.streak     → streak bar value (+32)
  // data.shap.trade      → supplier bar value (+10)
  // data.shap.catchup    → recovery bar value (-1)
  // data.shap.collector  → collector bar value (+14)
  // data.shap.amount_std → amount bar value (+28)
  // data.confidence      → "High" / "Medium" / "Low — provisional"
  // data.anomaly_flag    → show warning banner if true

  return (
    // your existing JSX, just swap hardcoded numbers for data.score etc.
  );
}
```

---

## Mapping: old hardcoded → new live values

| What's on screen now | Where it comes from now |
|----------------------|------------------------|
| Score: 714 | `data.score` (will show 828) |
| Payment streak: +18 | `data.shap.streak` |
| Supplier consistency: +12 | `data.shap.trade` |
| Recovery speed: +8 | `data.shap.catchup` |
| Collector trust: +4 | `data.shap.collector` |
| Amount variation: -6 | `data.shap.amount_std` |

---

## CORS

The API already allows `*.vercel.app`. No extra config needed on your end.

## If the API is slow on first load

Railway free tier sleeps after inactivity. Hit
`https://web-production-48a47.up.railway.app/health` once before the demo
 