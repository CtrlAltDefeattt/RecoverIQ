import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RecoverIQ Command Center",
  description:
    "Safety-constrained revenue recovery operations, learning, and audit dashboard.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
