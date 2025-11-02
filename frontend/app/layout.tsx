import type { Metadata } from 'next';
import { ClientLayout } from './ClientLayout';
import './globals.css';

export const metadata: Metadata = {
  title: 'i Assistant - Your Intelligent AI Life Assistant',
  description: 'Next-generation Agentic AI Life Assistant designed to act as your conscious digital twin',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr">
      <body className="min-h-screen bg-gradient-to-b from-dark-950 to-dark-900 text-gray-100 antialiased">
        <div id="root" className="min-h-screen">
          <ClientLayout>{children}</ClientLayout>
        </div>
      </body>
    </html>
  );
}
