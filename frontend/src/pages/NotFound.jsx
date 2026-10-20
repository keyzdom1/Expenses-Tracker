import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-4 text-center">
      <p className="text-xs font-medium uppercase tracking-widest text-text-muted">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-text">Page not found</h1>
      <p className="mt-2 max-w-sm text-sm text-text-muted">
        The page you were looking for does not exist or has moved.
      </p>
      <Link
        to="/dashboard"
        className="mt-6 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:opacity-90"
      >
        Go to dashboard
      </Link>
    </div>
  )
}
