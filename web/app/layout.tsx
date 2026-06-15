import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Popper: check the statement, then prove it",
  description:
    "Popper checks whether a formal statement is the one you meant, on math and code, built on the Axiom Lean Engine (AXLE), with a benchmark, a plain-English write-up, and a live Claude agent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
