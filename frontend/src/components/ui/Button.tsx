/**
 * Button — FROZEN.
 *
 * Props:
 *   variant?   'primary' | 'secondary' | 'ghost' | 'danger'   (default 'primary')
 *   block?     boolean   full width                            (default false)
 *   loading?   boolean   shows a spinner and sets aria-busy    (default false)
 *   icon?      ReactNode leading icon (decorative; label still required)
 *   as?        'button' | 'a'  render as a link                (default 'button')
 *   href?      string    when as='a'
 *   ...plus all native button/anchor attributes.
 *
 * Rules baked in: min 56px touch target, never icon-only (children are
 * required), disabled while loading so a double-tap on a boat cannot double-submit.
 */
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Spinner } from './Spinner'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface BaseProps {
  variant?: ButtonVariant
  block?: boolean
  loading?: boolean
  icon?: ReactNode
  children: ReactNode
}

type ButtonProps = BaseProps & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> & {
  as?: 'button'
}
type AnchorProps = BaseProps & { as: 'a'; href: string; target?: string; rel?: string; className?: string }

export function Button(props: ButtonProps | AnchorProps) {
  const { variant = 'primary', block, loading, icon, children, className = '' } = props
  const cls = `lk-btn lk-btn--${variant}${block ? ' lk-btn--block' : ''}${className ? ` ${className}` : ''}`

  if (props.as === 'a') {
    const { href, target, rel } = props
    return (
      <a className={cls} href={href} target={target} rel={rel}>
        {icon}{children}
      </a>
    )
  }

  const { as: _as, variant: _v, block: _b, loading: _l, icon: _i, children: _c, className: _cn, ...rest } =
    props as ButtonProps
  return (
    <button
      type={rest.type ?? 'button'}
      className={cls}
      aria-busy={loading || undefined}
      {...rest}
      disabled={rest.disabled || loading}
    >
      {loading ? <Spinner label="" /> : icon}
      {children}
    </button>
  )
}
