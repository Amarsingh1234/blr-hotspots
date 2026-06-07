import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "blr-hotspots — Bangalore events map",
  description: "Discover what's happening in Bangalore tonight. Music, comedy, parties, workshops and more.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="bg-[#0b0f14]">
      <body className={`${geistSans.variable} bg-[#0b0f14] antialiased`}>{children}</body>
    </html>
  );
}
