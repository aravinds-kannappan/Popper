import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Popper: falsify the spec, then verify the proof",
  description:
    "An executable spec-faithfulness oracle for math and code, built on the Axiom Lean Engine (AXLE), with a benchmark, a research write-up, and a live Claude agent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
