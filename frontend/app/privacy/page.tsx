import Link from 'next/link';
import { Surface } from '@/components/ui/Surface';
import { Button } from '@/components/ui/Button';

export const metadata = {
  title: 'Privacy Policy | i Assistant',
};

export default function PrivacyPolicyPage() {
  return (
    <main className="min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <header className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-[0.28em] text-white/45">Legal</p>
          <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Privacy Policy</h1>
          <p className="text-sm leading-6 text-white/60">Last updated: {new Date().toISOString().slice(0, 10)}</p>
        </header>

        <Surface material="regular" className="p-5 sm:p-7">
          <div className="prose prose-invert max-w-none prose-p:text-white/70 prose-li:text-white/70 prose-strong:text-white">
            <p>
              This Privacy Policy describes how i Assistant collects, uses, and protects your information when you use
              our app and services.
            </p>

            <h2>Information we collect</h2>
            <ul>
              <li>Account information (email, profile details you provide)</li>
              <li>Usage data (features used, basic diagnostics)</li>
              <li>Content you submit (tasks, calendar data you connect, and voice transcripts if you use voice)</li>
            </ul>

            <h2>How we use information</h2>
            <ul>
              <li>Provide and improve the service (dashboard, tasks, calendar, voice)</li>
              <li>Security and fraud prevention</li>
              <li>Support and troubleshooting</li>
            </ul>

            <h2>Google data access</h2>
            <p>
              If you connect Google services (e.g., Calendar), we access only the data required to provide the requested
              features. You can revoke access at any time from your Google Account settings.
            </p>

            <h2>Data retention</h2>
            <p>
              We retain data only as long as needed to provide the service, meet legal obligations, and resolve disputes.
              You may request export or deletion where applicable.
            </p>

            <h2>Contact</h2>
            <p>If you have questions about privacy, contact us at: <strong>support@aidepartment.net</strong></p>
          </div>
        </Surface>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/">
            <Button variant="secondary" size="md">Back to Home</Button>
          </Link>
          <Link href="/terms" className="text-sm text-white/60 hover:text-white/80 transition-colors">
            View Terms of Service →
          </Link>
        </div>
      </div>
    </main>
  );
}

