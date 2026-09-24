import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Laya Playground",
  description: "Run structured choice, score, and yes/no questions on the local Laya model.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
