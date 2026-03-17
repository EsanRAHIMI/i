import type { Metadata } from 'next';
import { Inter, Vazirmatn } from 'next/font/google';
import { cookies } from 'next/headers';
import { ClientLayout } from './ClientLayout';
import './globals.css';
import { getLocaleConfig } from '@/lib/utils';
import type { Language } from '@/types';

const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-inter',
});

const vazirmatn = Vazirmatn({
  subsets: ['arabic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-persian',
});

export const metadata: Metadata = {
  title: 'i Assistant - Your Intelligent AI Life Assistant',
  description: 'Next-generation Agentic AI Life Assistant designed to act as your conscious digital twin',
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon.ico',
    apple: '/favicon.ico',
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get('i_locale')?.value;
  const safeLanguage: Language =
    cookieLocale === 'fa-IR' || cookieLocale === 'ar-UA' || cookieLocale === 'en-US' ? cookieLocale : 'en-US';
  const initialLocale = getLocaleConfig(safeLanguage);

  return (
    <html
      lang={initialLocale.code}
      dir={initialLocale.direction}
      className={`${inter.variable} ${vazirmatn.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-linear-to-b from-dark-950 to-dark-900 text-gray-100 antialiased">
        <div id="root" className="min-h-screen">
          <ClientLayout>{children}</ClientLayout>
        </div>
      </body>
    </html>
  );
}
