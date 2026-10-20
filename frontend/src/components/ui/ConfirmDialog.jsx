import Modal from './Modal'
import Alert from './Alert'
import Button from './Button'

/** Small confirmation dialog used before destructive actions. */
export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isPending = false,
  variant = 'danger',
  errorMessage = null,
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            {cancelLabel}
          </Button>
          <Button variant={variant} onClick={onConfirm} isLoading={isPending}>
            {confirmLabel}
          </Button>
        </div>
      }
    >
      {errorMessage ? (
        <Alert variant="error" title="That did not work">
          {errorMessage}
        </Alert>
      ) : (
        <p className="text-sm text-text-muted">
          This action takes effect immediately. You can close this dialog to keep things unchanged.
        </p>
      )}
    </Modal>
  )
}
