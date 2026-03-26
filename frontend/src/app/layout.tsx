import type { Metadata } from "next";

import { QueryProvider } from "@/components/query-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "PubChem Compound Explorer",
  description: "Интерфейс для поиска соединений в PubChem в ручном и агентном режимах.",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
