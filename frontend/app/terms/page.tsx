import Link from 'next/link';
import { Surface } from '@/components/ui/Surface';
import { Button } from '@/components/ui/Button';

export const metadata = {
  title: 'Terms of Service | Ai Department',
};

export default function TermsOfServicePage() {
  return (
    <main className="min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <header className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-[0.28em] text-white/45">Legal</p>
          <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Terms of Service</h1>
          <p className="text-sm leading-6 text-white/60">Last updated: {new Date().toISOString().slice(0, 10)}</p>
        </header>

        <Surface material="regular" className="p-5 sm:p-7">
          <div className="prose prose-invert max-w-none prose-p:text-white/70 prose-li:text-white/70 prose-strong:text-white">
            <p>
              These Terms of Service govern your use of Ai Department. By using the service, you agree to these terms.
            </p>

            <h2>Use of the service</h2>
            <ul>
              <li>You must comply with applicable laws and regulations.</li>
              <li>You are responsible for the content you provide and actions you take using the service.</li>
              <li>Do not misuse the service (e.g., hacking, abuse, or violating others’ rights).</li>
            </ul>

            <h2>Accounts</h2>
            <ul>
              <li>You are responsible for keeping your account credentials secure.</li>
              <li>We may suspend accounts that violate these terms.</li>
            </ul>

            <h2>Third‑party services</h2>
            <p>
              If you connect third‑party services (such as Google), your use may be subject to their terms and policies.
            </p>

            <h2>Disclaimers</h2>
            <p>
              The service is provided “as is” without warranties. AI-generated suggestions are for informational purposes
              and may be inaccurate. Use your judgment before acting on recommendations.
            </p>

            <h2>Contact</h2>
            <p>
              For questions about these terms, contact: <strong>support@aidepartment.net</strong>
            </p>
          </div>
        </Surface>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/">
            <Button variant="secondary" size="md">Back to Home</Button>
          </Link>
          <Link href="/privacy" className="text-sm text-white/60 hover:text-white/80 transition-colors">
            View Privacy Policy →
          </Link>
        </div>
      </div>
    </main>
  );
}

