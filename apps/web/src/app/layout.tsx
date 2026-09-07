import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@fontsource/epilogue/400.css";
import "@fontsource/epilogue/500.css";
import "@fontsource/epilogue/600.css";
import "@fontsource/epilogue/700.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Memory Director",
  description: "A voice-led memory film producer for older adults.",
  icons: {
    icon: [{ type: "image/svg+xml", url: "/icon.svg" }],
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
