import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KOLA - Informal Credit Protocol",
  description: "Squad-verified credit intelligence for Ajo groups and lenders."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
