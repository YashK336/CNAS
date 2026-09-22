import { BookmarkPlus, Lock } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  Button,
  LinkButton,
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
} from '@/components/ui'
import { useAuth } from '@/hooks'
import {
  buildNetworkExplorerSnapshot,
  snapshotToInvestigationInput,
} from '@/lib/investigations'
import {
  createInvestigation,
  isForbidden,
  isUnauthorized,
  toErrorMessage,
} from '@/services'
import type { SavedInvestigation } from '@/types'

const INPUT_CLASS =
  'h-8 w-full rounded-sm border border-line-strong bg-surface-raised px-2 text-xs text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none'

export interface SaveInvestigationPanelProps {
  sourceId: string | null
  targetId: string | null
  selectionNodeId: string | null
  fromDatetime: string | null
  toDatetime: string | null
  onSaved?: (investigation: SavedInvestigation) => void
}

export function SaveInvestigationPanel({
  sourceId,
  targetId,
  selectionNodeId,
  fromDatetime,
  toDatetime,
  onSaved,
}: SaveInvestigationPanelProps) {
  const { isAuthenticated, canWriteInvestigations, isAdmin, user } = useAuth()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [jurisdiction, setJurisdiction] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)

  const jurisdictionRequired = useMemo(() => {
    if (isAdmin) return true
    return (user?.jurisdictions.length ?? 0) > 1
  }, [isAdmin, user?.jurisdictions.length])

  const jurisdictionOptions = useMemo(() => {
    if (isAdmin) return []
    return user?.jurisdictions ?? []
  }, [isAdmin, user?.jurisdictions])

  if (!isAuthenticated) {
    return (
      <Panel>
        <PanelHeader
          title="Save investigation"
          description="Sign in to persist this workspace."
          icon={<Lock size={15} strokeWidth={1.75} />}
        />
        <PanelBody className="p-2.5">
          <LinkButton to="/login" size="sm" variant="primary" className="w-full">
            Sign in to save
          </LinkButton>
        </PanelBody>
      </Panel>
    )
  }

  if (!canWriteInvestigations) {
    return (
      <Panel>
        <PanelHeader
          title="Save investigation"
          description="Viewer accounts have read-only access to saved investigations."
          icon={<Lock size={15} strokeWidth={1.75} />}
        />
        <PanelBody className="p-2.5 text-xs text-ink-muted">
          Contact an administrator if you need write access.
        </PanelBody>
      </Panel>
    )
  }

  const handleSave = () => {
    const trimmedName = name.trim()
    if (!trimmedName) {
      setError('Name is required.')
      return
    }

    const trimmedJurisdiction = jurisdiction.trim()
    if (jurisdictionRequired && !trimmedJurisdiction) {
      setError('Jurisdiction is required for this account.')
      return
    }

    const snapshot = buildNetworkExplorerSnapshot({
      sourceId,
      targetId,
      selectionNodeId,
      fromDatetime,
      toDatetime,
    })

    setIsSaving(true)
    setError(null)
    setSavedMessage(null)

    void createInvestigation(
      snapshotToInvestigationInput(
        snapshot,
        trimmedName,
        description.trim() || null,
        jurisdictionRequired ? trimmedJurisdiction : null,
      ),
    )
      .then((investigation) => {
        setSavedMessage(`Saved as ${investigation.name}`)
        onSaved?.(investigation)
      })
      .catch((saveError: unknown) => {
        if (isUnauthorized(saveError)) {
          setError('Session expired. Sign in again to save investigations.')
        } else if (isForbidden(saveError)) {
          setError('You do not have permission to save in this jurisdiction.')
        } else {
          setError(toErrorMessage(saveError))
        }
      })
      .finally(() => {
        setIsSaving(false)
      })
  }

  return (
    <Panel>
      <PanelHeader
        title="Save investigation"
        description="Persist the current trace, selection and temporal window."
        icon={<BookmarkPlus size={15} strokeWidth={1.75} />}
      />

      <PanelBody className="space-y-3 p-2.5">
        <div className="space-y-1">
          <label htmlFor="save-investigation-name" className="px-0.5 text-2xs text-ink-muted">
            Name
          </label>
          <input
            id="save-investigation-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="January drug-network trace"
            className={INPUT_CLASS}
          />
        </div>

        <div className="space-y-1">
          <label
            htmlFor="save-investigation-description"
            className="px-0.5 text-2xs text-ink-muted"
          >
            Description
          </label>
          <textarea
            id="save-investigation-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            placeholder="Optional analyst notes"
            className="w-full rounded-sm border border-line-strong bg-surface-raised px-2 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none"
          />
        </div>

        {jurisdictionRequired ? (
          <div className="space-y-1">
            <label
              htmlFor="save-investigation-jurisdiction"
              className="px-0.5 text-2xs text-ink-muted"
            >
              Jurisdiction
            </label>
            {jurisdictionOptions.length > 0 ? (
              <select
                id="save-investigation-jurisdiction"
                value={jurisdiction}
                onChange={(event) => setJurisdiction(event.target.value)}
                className={INPUT_CLASS}
              >
                <option value="">Select jurisdiction</option>
                {jurisdictionOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id="save-investigation-jurisdiction"
                type="text"
                value={jurisdiction}
                onChange={(event) => setJurisdiction(event.target.value)}
                placeholder="e.g. DEL"
                className={INPUT_CLASS}
              />
            )}
          </div>
        ) : null}

        {error ? (
          <>
            <SectionError message={error} onRetry={handleSave} compact />
            {error.includes('Sign in again') ? (
              <Link to="/login" className="text-xs text-accent hover:underline">
                Sign in
              </Link>
            ) : null}
          </>
        ) : null}
        {savedMessage ? (
          <p className="text-2xs text-signal-low">{savedMessage}</p>
        ) : null}

        <Button
          variant="primary"
          size="sm"
          className="w-full"
          disabled={isSaving || name.trim() === ''}
          onClick={handleSave}
          icon={<BookmarkPlus size={13} strokeWidth={1.75} />}
        >
          {isSaving ? 'Saving…' : 'Save investigation'}
        </Button>
      </PanelBody>
    </Panel>
  )
}
