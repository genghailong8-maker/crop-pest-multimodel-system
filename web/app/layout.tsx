import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "田诊协同｜农作物病虫害识别与防治系统",
  description: "基于视觉模型、多模态分析和人工复核的农作物病虫害诊断工作台。",
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
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
