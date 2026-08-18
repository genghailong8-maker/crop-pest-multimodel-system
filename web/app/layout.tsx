import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "田诊协同｜农作物病虫害识别与防治系统",
  description: "拍照识别农作物病虫害，查看诊断风险、田间严重度、下一步建议和可追溯报告。",
  openGraph: {
    title: "田诊协同｜农作物病虫害辅助识别",
    description: "拍照查看可疑病斑或害虫、诊断风险、田间严重度和下一步建议。",
    images: [{ url: "/phase9-social-preview.png", width: 1536, height: 1024, alt: "田诊协同农作物图片辅助识别" }],
  },
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
