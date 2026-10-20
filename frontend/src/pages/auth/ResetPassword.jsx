import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'

import AuthLayout from '../../components/layout/AuthLayout'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { useAuth } from '../../context/auth-context'

/**
 * Reached from the emailed recovery link. Supabase creates a temporary
 * recovery session, which lets the user set a new password.
 */
export default function ResetPassword() {
  const { updatePassword, session } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { password: '', confirm: '' } })

  const onSubmit = async (values) => {
    setServerError('')
    try {
      await updatePassword(values.password)
      navigate('/dashboard', { replace: true })
    } catch (error) {
      setServerError(error.message || 'Unable to update your password.')
    }
  }

  if (!session) {
    return (
      <AuthLayout
        title="Link expired"
        subtitle="This password reset link is no longer valid."
        footer={
          <Link to="/forgot-password" className="font-medium text-primary hover:underline">
            Request a new link
          </Link>
        }
      >
        <Alert variant="warning">
          Reset links expire quickly for your security. Request a fresh one and try again.
        </Alert>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Choose a new password"
      subtitle="You'll be signed in once it's saved."
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {serverError && <Alert variant="error">{serverError}</Alert>}

        <Input
          label="New password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 8 characters"
          error={errors.password?.message}
          {...register('password', {
            required: 'Choose a password.',
            minLength: { value: 8, message: 'Use at least 8 characters.' },
          })}
        />

        <Input
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          placeholder="Repeat your password"
          error={errors.confirm?.message}
          {...register('confirm', {
            required: 'Repeat your password.',
            validate: (value, formValues) =>
              value === formValues.password || 'Passwords do not match.',
          })}
        />

        <Button type="submit" fullWidth isLoading={isSubmitting}>
          Save new password
        </Button>
      </form>
    </AuthLayout>
  )
}
