import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OCR Foto Timemark - P3STE Sintelis",
  description: "Aplikasi modern koreksi watermark foto timemark dan penggabungan PDF perawatan sintelis.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className="dark">
      <body className="antialiased bg-slate-950 text-slate-100">
        {children}
      </body>
    </html>
  );
}
