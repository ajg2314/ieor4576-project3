import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StoryCoach — AI Communication Coach",
  description: "Multi-agent feedback for academic presentations and papers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
