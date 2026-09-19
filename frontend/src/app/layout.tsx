import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "Price Pantry — UK Grocery Price Comparison",
  description:
    "Compare grocery prices across UK supermarkets. Phase 1: Tesco.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en-GB">
      <body>
        <Providers>
          <Header />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
          <footer className="border-t border-gray-200 py-6 text-center text-sm text-gray-400">
            Price Pantry · Phase 1 MVP · Data from Tesco
          </footer>
        </Providers>
      </body>
    </html>
  );
}
