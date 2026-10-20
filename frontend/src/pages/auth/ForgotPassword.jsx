import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'

import AuthLayout from '../../components/layout/AuthLayout'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { useAuth } from '../../context/auth-context'

export default function ForgotPassword() {
  const { requestPasswordReset } = useAuth()
  const [serverError, setServerError] = useState('')
  const [sent, setSent] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { email: '' } })

  const onSubmit = async (values) => {
    setServerError('')
    try {
      await requestPasswordReset(values.email.trim())
      setSent(true)
    } catch (error) {
      setServerError(error.message || 'Unable to send the reset email.')
    }
  }

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="We'll email you a secure link to choose a new one."
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      {sent ? (
        <Alert variant="success" title="Check your inbox">
          If an account exists for that address, a password reset link is on its way.
        </Alert>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {serverError && <Alert variant="error">{serverError}</Alert>}

          <Input
            label="Email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            {...register('email', {
              required: 'Enter your email address.',
              pattern: { value: /\S+@\S+\.\S+/, message: 'Enter a valid email address.' },
            })}
          />

          <Button type="submit" fullWidth isLoading={isSubmitting}>
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
