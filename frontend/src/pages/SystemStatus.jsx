import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

import Alert from '../components/ui/Alert'
import { fetchHealth } from '../lib/api'

/** Developer-facing diagnostics page (also useful during deployment). */
export default function SystemStatus() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    retry: 0,
    refetchInterval: 30000,
  })

  return (
    <div className="min-h-screen bg-bg px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-2xl space-y-6">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
        >
          <ArrowLeft size={13} aria-hidden="true" />
          Back to the app
        </Link>

        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">System status</h1>
          <p className="mt-1 text-sm text-text-muted">
            Live connectivity between the browser and the FastAPI backend.
          </p>
        </div>

        <section className="card p-5" aria-labelledby="health-heading">
          <h2 id="health-heading" className="text-sm font-semibold text-text">
            Backend
          </h2>

          {isLoading ? (
            <p className="mt-3 text-sm text-text-muted">Checking…</p>
          ) : isError ? (
            <Alert variant="error" title="API not reachable" className="mt-3">
              {error?.message || 'Start the backend with uvicorn app.main:app --reload'}
            </Alert>
          ) : (
            <dl className="mt-3 divide-y divide-border text-sm">
              {[
                ['Status', data.status],
                ['Version', data.version],
                ['Environment', data.environment],
                ['API prefix', data.api_prefix],
                ['Database', data.database],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-4 py-2">
                  <dt className="text-text-muted">{label}</dt>
                  <dd className="font-mono text-xs text-text">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>

        <p className="text-xs text-text-muted">
          Interactive API documentation lives at{' '}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary hover:underline"
          >
            localhost:8000/docs
          </a>
          .
        </p>
      </div>
    </div>
  )
}
