import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'

import AuthLayout from '../../components/layout/AuthLayout'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { useAuth } from '../../context/auth-context'

export default function Register() {
  const { signUp } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { fullName: '', email: '', password: '', confirm: '' } })

  const onSubmit = async (values) => {
    setServerError('')
    try {
      const result = await signUp(values.email.trim(), values.password, values.fullName.trim())
      if (result.session) navigate('/dashboard', { replace: true })
      else setAwaitingConfirmation(true)
    } catch (error) {
      setServerError(error.message || 'Unable to create your account.')
    }
  }

  if (awaitingConfirmation) {
    return (
      <AuthLayout
        title="Confirm your email"
        subtitle="One more step before you can sign in."
        footer={
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        }
      >
        <Alert variant="success" title="Check your inbox">
          We sent a confirmation link to your email address. Open it, then sign in normally.
        </Alert>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start tracking your money in a few minutes."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {serverError && <Alert variant="error">{serverError}</Alert>}

        <Input
          label="Full name"
          autoComplete="name"
          placeholder="Ada Lovelace"
          error={errors.fullName?.message}
          {...register('fullName', { maxLength: { value: 120, message: 'That name is too long.' } })}
        />

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

        <Input
          label="Password"
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
          label="Confirm password"
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
          Create account
        </Button>
      </form>
    </AuthLayout>
  )
}
