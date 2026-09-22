import type {
  HTMLAttributes,
  TableHTMLAttributes,
  TdHTMLAttributes,
  ThHTMLAttributes,
} from 'react'

import { cn } from '@/lib/cn'

/** Scroll container + dense base table. Compose with the cells below. */
export function Table({
  className,
  children,
  ...rest
}: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto">
      <table
        className={cn('w-full border-collapse text-left text-xs', className)}
        {...rest}
      >
        {children}
      </table>
    </div>
  )
}

export function TableHeader({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn('border-b border-line bg-surface-raised', className)}
      {...rest}
    >
      {children}
    </thead>
  )
}

export function TableBody({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody className={cn('divide-y divide-line', className)} {...rest}>
      {children}
    </tbody>
  )
}

export interface TableRowProps
  extends HTMLAttributes<HTMLTableRowElement> {
  interactive?: boolean
}

export function TableRow({
  interactive = false,
  className,
  children,
  ...rest
}: TableRowProps) {
  return (
    <tr
      className={cn(
        interactive && 'cursor-pointer transition-colors hover:bg-surface-hover',
        className,
      )}
      {...rest}
    >
      {children}
    </tr>
  )
}

export function TableHeaderCell({
  className,
  children,
  ...rest
}: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn(
        'px-3 py-2 text-2xs font-semibold tracking-wider text-ink-faint uppercase',
        className,
      )}
      {...rest}
    >
      {children}
    </th>
  )
}

export interface TableCellProps
  extends TdHTMLAttributes<HTMLTableCellElement> {
  /** Tabular monospace, for IDs and metrics. */
  mono?: boolean
}

export function TableCell({
  mono = false,
  className,
  children,
  ...rest
}: TableCellProps) {
  return (
    <td
      className={cn(
        'px-3 py-2 align-middle text-ink',
        mono && 'font-mono tabular-nums',
        className,
      )}
      {...rest}
    >
      {children}
    </td>
  )
}
