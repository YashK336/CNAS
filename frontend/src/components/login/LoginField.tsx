import { Eye, EyeOff } from 'lucide-react'
import type { InputHTMLAttributes, ReactNode } from 'react'
import { useState } from 'react'

import { cn } from '@/lib/cn'

const FIELD_CLASS =
  'peer h-11 w-full rounded-[10px] border border-line-strong bg-surface-raised/70 px-3.5 text-sm text-ink transition-[border-color,box-shadow] duration-200 placeholder:text-ink-faint focus:border-accent/70 focus:shadow-[0_0_0_3px_rgba(75,141,248,0.14)] focus:outline-none disabled:opacity-50 aria-[invalid=true]:border-signal-critical/70 aria-[invalid=true]:focus:shadow-[0_0_0_3px_rgba(210,79,79,0.14)]'

export interface LoginFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: boolean
  hint?: ReactNode
}

export function LoginField({
  id,
  label,
  error = false,
  hint,
  className,
  ...rest
}: LoginFieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-2xs font-medium tracking-wide text-ink-muted">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          aria-invalid={error || undefined}
          className={cn(FIELD_CLASS, className)}
          {...rest}
        />
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-3 bottom-0 h-px origin-left scale-x-0 bg-accent/80 transition-transform duration-300 ease-out peer-focus:scale-x-100"
        />
      </div>
      {hint}
    </div>
  )
}

export interface LoginPasswordFieldProps extends Omit<LoginFieldProps, 'type'> {}

export function LoginPasswordField({
  id,
  label,
  error = false,
  className,
  ...rest
}: LoginPasswordFieldProps) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-2xs font-medium tracking-wide text-ink-muted">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          aria-invalid={error || undefined}
          className={cn(FIELD_CLASS, 'pr-11', className)}
          {...rest}
        />
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-3 bottom-0 h-px origin-left scale-x-0 bg-accent/80 transition-transform duration-300 ease-out peer-focus:scale-x-100"
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          disabled={rest.disabled}
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          className="absolute top-1/2 right-2.5 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-surface-hover hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-1 disabled:pointer-events-none disabled:opacity-40"
        >
          {visible ? <EyeOff size={15} strokeWidth={1.75} /> : <Eye size={15} strokeWidth={1.75} />}
        </button>
      </div>
    </div>
  )
}

export { FIELD_CLASS }
