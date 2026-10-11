import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "DentalHelper - предварительная оценка улыбки", description: "Загрузите фото зубов для предварительной оценки и найдите стоматологию рядом.", icons: { icon: "/favicon.svg" } };

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru"><body>{children}</body></html>
  );
}
