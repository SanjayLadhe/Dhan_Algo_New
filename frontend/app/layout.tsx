import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Dhan Algo Trading Platform',
  description: 'Advanced algorithmic trading platform for Indian markets',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-900 text-white">
        {children}
      </body>
    </html>
  );
}
