import { Link } from 'react-router-dom'

import { BackendStatusChip } from './BackendStatusChip'
import { BrandMark } from './BrandMark'
import { GlobalSearch } from './GlobalSearch'
import { UserSessionMenu } from '@/components/auth/UserSessionMenu'

export function Header() {
  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-line bg-surface px-3">
      <Link
        to="/"
        className="flex shrink-0 items-center gap-2.5 rounded-sm pr-1"
        title="CNAS — Criminal Network Analysis System"
      >
        <BrandMark size={24} />
        <span className="flex flex-col leading-none">
          <span className="text-sm font-semibold tracking-[0.14em] text-ink">
            CNAS
          </span>
          <span className="mt-0.5 hidden text-2xs tracking-wide text-ink-faint lg:block">
            Sūtradhāra · Criminal Network Analysis
          </span>
        </span>
      </Link>

      <div className="mx-auto flex min-w-0 flex-1 justify-center px-2">
        <GlobalSearch />
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <BackendStatusChip />
        <span aria-hidden className="h-5 w-px bg-line" />
        <UserSessionMenu />
      </div>
    </header>
  )
}
