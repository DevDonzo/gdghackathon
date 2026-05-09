import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RateDrop",
  description: "Upload a telecom bill, run a sandbox negotiation, and see the savings."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
