import { ArrowRight, KeyRound } from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Shown when the Supabase environment variables are missing, so the app fails
 * with clear instructions instead of a blank screen.
 */
export default function SetupNotice() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4 py-10">
      <div className="card w-full max-w-xl p-6 sm:p-8">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-warning-soft text-warning">
          <KeyRound size={18} aria-hidden="true" />
        </span>

        <h1 className="mt-4 text-xl font-semibold text-text">Connect your Supabase project</h1>
        <p className="mt-2 text-sm text-text-muted">
          Sign-in is powered by Supabase, and the frontend has no project credentials yet. Create a
          project at <span className="font-medium text-text">supabase.com</span>, then put its public
          values in <code className="font-mono text-xs">frontend/.env</code> and restart the dev
          server.
        </p>

        <pre className="mt-4 overflow-x-auto rounded-xl border border-border bg-surface-raised p-3 text-xs text-text">
{`VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_ANON_KEY`}
        </pre>

        <p className="mt-4 text-xs text-text-muted">
          Only the public anon key belongs in the browser. The service-role key and database
          password stay in <code className="font-mono">backend/.env</code>.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            to="/system"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:opacity-90"
          >
            Check backend status
            <ArrowRight size={14} aria-hidden="true" />
          </Link>
          <a
            href="https://supabase.com/dashboard"
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-primary hover:underline"
          >
            Open Supabase dashboard
          </a>
        </div>
      </div>
    </div>
  )
}
