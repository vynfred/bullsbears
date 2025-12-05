// src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider } from "@/hooks/useAuth";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "BullsBears - AI Stock & Options Analysis",
  description: "AI-powered stock picks platform with ML-based targets and confluence scoring",
  manifest: "/site.webmanifest",
  icons: {
    icon: [
      { url: '/BB-favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/BB-favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/BB-favicon-512x512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/BB-favicon-180x180.png', sizes: '180x180', type: 'image/png' },
    ],
    shortcut: '/BB-favicon-32x32.png',
  },
  themeColor: '#10b981',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'BullsBears',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <ThemeProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
