import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { SkipLink } from "@/components/layout/SkipLink";
import { LocaleProvider } from "@/lib/i18n/LocaleProvider";
import { getCommonContent } from "@/lib/i18n/content";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const defaultContent = getCommonContent();

export const metadata: Metadata = {
  title: {
    default: defaultContent.brandName,
    template: `%s | ${defaultContent.brandName}`,
  },
  description: defaultContent.brandTagline,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} min-h-screen overflow-x-hidden antialiased`}>
        <LocaleProvider>
          <SkipLink />
          <div className="flex min-h-screen min-w-0 flex-col">
            <Header />
            <div className="min-w-0 flex-1">{children}</div>
            <Footer />
          </div>
        </LocaleProvider>
      </body>
    </html>
  );
}
