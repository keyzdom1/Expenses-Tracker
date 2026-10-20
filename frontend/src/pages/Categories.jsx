import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderTree, Pencil, Plus, Tags, Trash2 } from 'lucide-react'
import { useState } from 'react'

import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import Input from '../components/ui/Input'
import Modal from '../components/ui/Modal'
import Select from '../components/ui/Select'
import { useCategories } from '../hooks/useReferenceData'
import { api, apiErrorMessage } from '../lib/api'

const KINDS = [
  { value: 'expense', label: 'Expense categories' },
  { value: 'income', label: 'Income categories' },
]

function CategoryForm({ category, parent, kind, allCategories, onClose, onSaved }) {
  const queryClient = useQueryClient()
  const isEdit = Boolean(category)
  const [name, setName] = useState(category?.name ?? '')
  const [parentId, setParentId] = useState(category?.parent_id ?? parent?.id ?? '')
  const [error, setError] = useState('')

  const hasChildren = isEdit && allCategories.some((row) => row.parent_id === category.id)
  const parentOptions = allCategories
    .filter(
      (row) =>
        row.kind === kind &&
        row.parent_id === null &&
        (!isEdit || row.id !== category.id),
    )
    .map((row) => ({ value: row.id, label: row.name }))

  const mutation = useMutation({
    mutationFn: (payload) =>
      isEdit
        ? api.patch(`/categories/${category.id}`, payload)
        : api.post('/categories', { ...payload, kind }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      onSaved()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError)),
  })

  const handleSubmit = (event) => {
    event.preventDefault()
    setError('')
    if (!name.trim()) {
      setError('Give the category a name.')
      return
    }
    mutation.mutate({
      name: name.trim(),
      parent_id: parentId || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <Alert variant="error">{error}</Alert>}

      <Input
        label="Name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder={kind === 'expense' ? 'Groceries' : 'Side project'}
        maxLength={80}
        required
      />

      <Select
        label="Parent category"
        value={parentId}
        onChange={(event) => setParentId(event.target.value)}
        placeholder="None - top level"
        options={parentOptions}
        disabled={hasChildren}
        hint={
          hasChildren
            ? 'This category has subcategories; move or delete them before changing its parent.'
            : 'Categories can be nested one level deep.'
        }
      />

      <div className="flex justify-end gap-2 pt-1">
        <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button type="submit" isLoading={mutation.isPending}>
          {isEdit ? 'Save category' : 'Create category'}
        </Button>
      </div>
    </form>
  )
}

export default function Categories() {
  const queryClient = useQueryClient()
  const [kind, setKind] = useState('expense')
  const [modal, setModal] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const categoriesQuery = useCategories()
  const categories = categoriesQuery.data ?? []

  const visible = categories.filter((category) => category.kind === kind)
  const parents = visible
    .filter((category) => category.parent_id === null)
    .sort((a, b) => a.name.localeCompare(b.name))
  const childrenOf = (parentId) =>
    visible
      .filter((category) => category.parent_id === parentId)
      .sort((a, b) => a.name.localeCompare(b.name))

  const deleteMutation = useMutation({
    mutationFn: (category) => api.delete(`/categories/${category.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      setDeleteTarget(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Categories</h1>
          <p className="mt-1 text-sm text-text-muted">
            Group spending and income so reports stay meaningful. Defaults can be renamed or
            deleted.
          </p>
        </div>
        <Button onClick={() => setModal({ mode: 'create', kind })}>
          <Plus size={16} aria-hidden="true" />
          Add category
        </Button>
      </div>

      {categoriesQuery.isError && (
        <Alert variant="error" title="Could not load categories">
          {apiErrorMessage(categoriesQuery.error)}
        </Alert>
      )}

      <div
        className="inline-flex rounded-xl border border-border bg-surface p-1"
        role="tablist"
        aria-label="Category kind"
      >
        {KINDS.map((option) => (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={kind === option.value}
            onClick={() => setKind(option.value)}
            className={[
              'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              kind === option.value
                ? 'bg-primary/10 text-primary'
                : 'text-text-muted hover:bg-surface-raised hover:text-text',
            ].join(' ')}
          >
            {option.label}
          </button>
        ))}
      </div>

      {categoriesQuery.isLoading ? (
        <p className="text-sm text-text-muted">Loading categories…</p>
      ) : parents.length === 0 ? (
        <section className="card p-8 text-center">
          <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Tags size={20} aria-hidden="true" />
          </span>
          <h2 className="mt-3 text-sm font-semibold text-text">No categories here yet</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">
            Add a category to start classifying your {kind === 'expense' ? 'spending' : 'income'}.
          </p>
          <Button className="mt-4" onClick={() => setModal({ mode: 'create', kind })}>
            <Plus size={16} aria-hidden="true" />
            Add category
          </Button>
        </section>
      ) : (
        <section className="card divide-y divide-border" aria-label={`${kind} categories`}>
          {parents.map((parent) => {
            const children = childrenOf(parent.id)
            return (
              <div key={parent.id}>
                <div className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <FolderTree size={15} className="shrink-0 text-text-muted" aria-hidden="true" />
                    <span className="truncate text-sm font-medium text-text">{parent.name}</span>
                    {parent.is_system && (
                      <span className="badge bg-surface-raised text-text-muted">Default</span>
                    )}
                    {children.length > 0 && (
                      <span className="text-xs text-text-muted">
                        {children.length} {children.length === 1 ? 'subcategory' : 'subcategories'}
                      </span>
                    )}
                  </div>

                  <div className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      onClick={() => setModal({ mode: 'child', parent, kind })}
                      aria-label={`Add subcategory to ${parent.name}`}
                      className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-primary"
                    >
                      <Plus size={15} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setModal({ mode: 'edit', category: parent, kind })}
                      aria-label={`Edit ${parent.name}`}
                      className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
                    >
                      <Pencil size={15} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(parent)}
                      aria-label={`Delete ${parent.name}`}
                      className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-expense"
                    >
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </div>
                </div>

                {children.map((child) => (
                  <div
                    key={child.id}
                    className="flex items-center justify-between gap-3 border-t border-border bg-surface-raised px-4 py-2.5 pl-10"
                  >
                    <span className="truncate text-sm text-text-muted">{child.name}</span>
                    <div className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        onClick={() => setModal({ mode: 'edit', category: child, kind })}
                        aria-label={`Edit ${child.name}`}
                        className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface hover:text-text"
                      >
                        <Pencil size={14} aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(child)}
                        aria-label={`Delete ${child.name}`}
                        className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface hover:text-expense"
                      >
                        <Trash2 size={14} aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          })}
        </section>
      )}

      <Modal
        open={modal !== null}
        onClose={() => setModal(null)}
        title={
          modal?.mode === 'edit'
            ? 'Edit category'
            : modal?.mode === 'child'
              ? `Add subcategory to ${modal.parent.name}`
              : 'Add category'
        }
        description={
          modal?.mode === 'child'
            ? 'Subcategories appear under their parent in reports.'
            : 'Choose a short, recognisable name.'
        }
      >
        {modal && (
          <CategoryForm
            key={modal.category?.id ?? modal.parent?.id ?? 'new'}
            category={modal.category}
            parent={modal.parent}
            kind={modal.kind}
            allCategories={categories}
            onClose={() => setModal(null)}
            onSaved={() => setModal(null)}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => {
          setDeleteTarget(null)
          deleteMutation.reset()
        }}
        onConfirm={() => deleteMutation.mutate(deleteTarget)}
        title={`Delete ${deleteTarget?.name ?? 'category'}?`}
        description="Categories that are used by transactions cannot be deleted."
        confirmLabel="Delete category"
        isPending={deleteMutation.isPending}
        errorMessage={
          deleteMutation.isError ? apiErrorMessage(deleteMutation.error) : null
        }
      />
    </div>
  )
}
