import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useNotifications } from '../../hooks/useReferenceData'
import { api, apiErrorMessage } from '../../lib/api'
import { formatDateTime } from '../../lib/format'

export default function NotificationBell() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  const notificationsQuery = useNotifications({ limit: 10 })
  const notifications = notificationsQuery.data?.data ?? []
  const unreadCount = notificationsQuery.data?.meta?.unread_count ?? 0

  useEffect(() => {
    if (!open) return undefined

    const handlePointerDown = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false)
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['notifications'] })

  const markReadMutation = useMutation({
    mutationFn: (notification) => api.post(`/notifications/${notification.id}/read`),
    onSuccess: invalidate,
  })

  const markAllMutation = useMutation({
    mutationFn: () => api.post('/notifications/read-all'),
    onSuccess: invalidate,
  })

  const label = unreadCount > 0 ? `Notifications (${unreadCount} unread)` : 'Notifications'

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={label}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="relative rounded-lg border border-border p-2 text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
      >
        <Bell size={16} aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-expense px-1 text-[10px] font-semibold leading-none text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-border bg-surface shadow-xl"
        >
          <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Notifications
            </p>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => markAllMutation.mutate()}
                disabled={markAllMutation.isPending}
                className="inline-flex items-center gap-1 rounded-lg px-1.5 py-1 text-[11px] font-medium text-primary transition-colors hover:bg-surface-raised disabled:opacity-60"
              >
                <CheckCheck size={13} aria-hidden="true" />
                Mark all read
              </button>
            )}
          </div>

          {notificationsQuery.isError ? (
            <p role="alert" className="px-3 py-4 text-xs text-expense">
              {apiErrorMessage(notificationsQuery.error, 'Could not load notifications.')}
            </p>
          ) : notificationsQuery.isLoading ? (
            <p className="px-3 py-4 text-xs text-text-muted">Loading notifications…</p>
          ) : notifications.length === 0 ? (
            <p className="px-3 py-6 text-center text-xs text-text-muted">
              You are all caught up. Bill reminders and budget alerts appear here.
            </p>
          ) : (
            <ul className="max-h-80 divide-y divide-border overflow-y-auto">
              {notifications.map((notification) => {
                const unread = !notification.read_at
                return (
                  <li key={notification.id}>
                    <button
                      type="button"
                      onClick={() => {
                        if (unread) markReadMutation.mutate(notification)
                      }}
                      className="flex w-full items-start gap-2 px-3 py-2.5 text-left transition-colors hover:bg-surface-raised"
                    >
                      <span
                        className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                          unread ? 'bg-primary' : 'bg-transparent'
                        }`}
                        aria-hidden="true"
                      />
                      <span className="min-w-0 flex-1">
                        <span
                          className={`block text-xs ${
                            unread ? 'font-semibold text-text' : 'font-medium text-text-muted'
                          }`}
                        >
                          {notification.title}
                        </span>
                        {notification.body && (
                          <span className="mt-0.5 block text-[11px] text-text-muted">
                            {notification.body}
                          </span>
                        )}
                        <span className="mt-1 block text-[10px] uppercase tracking-wide text-text-muted">
                          {formatDateTime(notification.created_at)}
                          {unread ? ' · Unread' : ''}
                        </span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
