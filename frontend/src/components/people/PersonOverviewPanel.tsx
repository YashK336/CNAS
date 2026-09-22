import { IdCard } from 'lucide-react'

import { Panel, PanelBody, PanelHeader } from '@/components/ui'
import { cn } from '@/lib/cn'
import { cleanValue } from '@/lib/graph'
import type { Person } from '@/types'

interface Field {
  label: string
  value: string
  mono?: boolean
}

/** Only fields the backend actually returned for this person are listed. */
function overviewFields(person: Person): Field[] {
  const fields: Field[] = []

  const push = (label: string, raw: unknown, mono = false) => {
    const value = cleanValue(raw)
    if (value !== null) fields.push({ label, value, mono })
  }

  push('Name', person.name)
  push('Person ID', person.person_id, true)
  push('Phone', person.phone, true)
  push('Home city', person.home_city)
  push('Risk group', person.risk_group)
  push('Vehicle', person.vehicle_no, true)
  push('Bank account', person.bank_account, true)
  push('Social ID', person.social_id, true)

  return fields
}

export interface PersonOverviewPanelProps {
  person: Person
}

export function PersonOverviewPanel({ person }: PersonOverviewPanelProps) {
  const fields = overviewFields(person)

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Overview"
        description="Identity record from /entities/persons."
        icon={<IdCard size={15} strokeWidth={1.75} />}
      />

      <PanelBody className="flex-1 p-0">
        <dl className="divide-y divide-line">
          {fields.map((field) => (
            <div
              key={field.label}
              className="flex items-baseline justify-between gap-3 px-4 py-1.5"
            >
              <dt className="shrink-0 text-2xs text-ink-faint">
                {field.label}
              </dt>
              <dd
                className={cn(
                  'min-w-0 truncate text-right text-xs text-ink',
                  field.mono && 'font-mono tabular-nums',
                )}
                title={field.value}
              >
                {field.value}
              </dd>
            </div>
          ))}
        </dl>
      </PanelBody>
    </Panel>
  )
}
