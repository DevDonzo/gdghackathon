import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans"
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono"
});

export const metadata: Metadata = {
  title: "RateDrop // Agent",
  description: "Autonomous negotiation agent. We fight the carriers so you don't have to.",
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="black"/><text y="50%" x="50%" dominant-baseline="middle" text-anchor="middle" fill="white" font-family="monospace" font-size="60" font-weight="bold">R</text></svg>'
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${mono.variable}`}>
        {children}
      </body>
    </html>
  );
}
