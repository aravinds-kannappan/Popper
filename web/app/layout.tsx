import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Popper: falsify the statement, then prove it",
  description:
    "Popper is a semantic-fault-tolerant screen in front of formal provers like AXLE and AxiomProver. It breaks a statement before you pay to prove it, returning the exact counterexample, with a benchmark, a research note, and a live Claude agent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
