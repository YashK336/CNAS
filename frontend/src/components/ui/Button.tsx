import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { buttonClass } from './buttonStyles'
import type { ButtonSize, ButtonVariant } from './buttonStyles'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  /** Leading icon, typically a 13-14px Lucide glyph. */
  icon?: ReactNode
}

export function Button({
  variant = 'secondary',
  size = 'md',
  icon,
  className,
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClass(variant, size, className)}
      {...rest}
    >
      {icon}
      {children}
    </button>
  )
}
