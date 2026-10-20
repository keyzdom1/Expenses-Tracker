import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import AuthLayout from '../../components/layout/AuthLayout'
import { useAuth } from '../../context/auth-context'

export default function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { email: '', password: '' } })

  const onSubmit = async (values) => {
    setServerError('')
    try {
      await signIn(values.email.trim(), values.password)
      const target = location.state?.from?.pathname ?? '/dashboard'
      navigate(target, { replace: true })
    } catch (error) {
      setServerError(error.message || 'Unable to sign in.')
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to see your dashboard."
      footer={
        <>
          New here?{' '}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
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

        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          error={errors.password?.message}
          {...register('password', { required: 'Enter your password.' })}
        />

        <div className="text-right">
          <Link to="/forgot-password" className="text-xs font-medium text-primary hover:underline">
            Forgot your password?
          </Link>
        </div>

        <Button type="submit" fullWidth isLoading={isSubmitting}>
          Sign in
        </Button>
      </form>
    </AuthLayout>
  )
}
