import { FileText, Network, UserRound, Waypoints } from 'lucide-react'

import { RiskBadge } from '@/components/risk'
import {
  LinkButton,
  Panel,
  PanelBody,
  PanelHeader,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { EMPTY_VALUE, formatDate, formatText } from '@/lib/format'
import { cleanValue } from '@/lib/graph'
import type { CaseRow } from '@/types'

interface Field {
  label: string
  value: string
  mono?: boolean
}

function FieldList({ fields }: { fields: Field[] }) {
  return (
    <dl className="divide-y divide-line">
      {fields.map((field) => (
        <div
          key={field.label}
          className="flex items-baseline justify-between gap-3 px-4 py-1.5"
        >
          <dt className="shrink-0 text-2xs text-ink-faint">{field.label}</dt>
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
  )
}

export function CaseIdentificationPanel({ row }: { row: CaseRow }) {
  const fields: Field[] = [
    { label: 'FIR ID', value: formatText(row.fir.fir_id), mono: true },
    { label: 'Crime', value: formatText(row.fir.crime) },
    { label: 'Date', value: formatDate(row.fir.date), mono: true },
    { label: 'Location', value: formatText(row.fir.location) },
  ]

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Case identification"
        description="Fields recorded on the FIR."
        icon={<FileText size={15} strokeWidth={1.75} />}
      />
      <PanelBody className="flex-1 p-0">
        <FieldList fields={fields} />
      </PanelBody>
    </Panel>
  )
}

export function InvolvedPersonPanel({ row }: { row: CaseRow }) {
  const person = row.involvedPerson
  const personId =
    cleanValue(person?.entity_id) ?? cleanValue(row.fir.person_id)

  const fields: Field[] = [
    { label: 'Name', value: formatText(person?.name) },
    { label: 'Person ID', value: formatText(personId), mono: true },
    { label: 'Phone', value: formatText(person?.phone), mono: true },
    { label: 'Home city', value: formatText(person?.home_city) },
    { label: 'Risk group', value: formatText(person?.risk_group) },
    {
      label: 'Risk score',
      value:
        row.riskScore === null
          ? EMPTY_VALUE
          : String(row.riskScore),
      mono: true,
    },
  ]

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Involved person"
        description="Linked through person_id. Involvement is not a finding of guilt."
        icon={<UserRound size={15} strokeWidth={1.75} />}
        actions={
          row.riskLevel ? (
            typeof row.riskScore === 'number' ? (
              <RiskBadge level={row.riskLevel} score={row.riskScore} />
            ) : (
              <RiskBadge level={row.riskLevel} />
            )
          ) : null
        }
      />
      <PanelBody className="flex-1 p-0">
        <FieldList fields={fields} />
      </PanelBody>
    </Panel>
  )
}

export function CaseNetworkContextPanel({ row }: { row: CaseRow }) {
  const personId =
    cleanValue(row.involvedPerson?.entity_id) ??
    cleanValue(row.fir.person_id)

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Network context"
        description="Open the existing person profile or Network Explorer."
        icon={<Waypoints size={15} strokeWidth={1.75} />}
      />
      <PanelBody className="flex flex-1 flex-col gap-2">
        {personId ? (
          <>
            <LinkButton
              to={`/people/${encodeURIComponent(personId)}`}
              size="sm"
              icon={<UserRound size={13} strokeWidth={1.75} />}
            >
              View person
            </LinkButton>
            <LinkButton
              to={`/network?focus=${encodeURIComponent(personId)}`}
              size="sm"
              variant="primary"
              icon={<Network size={13} strokeWidth={1.75} />}
            >
              Investigate network
            </LinkButton>
          </>
        ) : (
          <p className="text-xs text-ink-muted">
            This FIR has no linked person_id, so person and network navigation
            are unavailable.
          </p>
        )}
      </PanelBody>
    </Panel>
  )
}
