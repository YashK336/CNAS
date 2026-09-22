import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

import { Button, EmptyState, Panel } from '@/components/ui'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * Keeps a render failure in one module from blanking the whole workstation.
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  override state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Unhandled UI error', error, info.componentStack)
  }

  private readonly reset = () => {
    this.setState({ error: null })
  }

  override render(): ReactNode {
    const { error } = this.state

    if (!error) return this.props.children

    return (
      <Panel>
        <EmptyState
          title="This module failed to render"
          description={error.message}
          actions={
            <Button variant="primary" size="sm" onClick={this.reset}>
              Try again
            </Button>
          }
        />
      </Panel>
    )
  }
}
