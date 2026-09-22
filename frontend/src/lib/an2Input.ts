import type { UnstructuredFirFindingInput } from '@/services/analytics'

const DEFAULT_SOURCE = 'unstructured_fir'
const DEFAULT_JURISDICTION = 'UNSPECIFIED'

const FIR_ID_KEYS = new Set(['fir_id'])
const TEXT_KEYS = new Set(['raw_text'])
const JURISDICTION_KEYS = new Set(['jurisdiction'])

export function parseAn2Records(value: string): UnstructuredFirFindingInput[] {
  const text = value.replace(/^\uFEFF/, '').trim()
  if (!text) return []

  if (text.startsWith('[') || text.startsWith('{')) {
    return parseJsonRecords(text)
  }
  return parseCsvRecords(text)
}

function parseJsonRecords(value: string): UnstructuredFirFindingInput[] {
  const parsed: unknown = JSON.parse(value)
  if (!Array.isArray(parsed)) throw new Error('The batch must be a JSON array.')
  return parsed as UnstructuredFirFindingInput[]
}

function parseCsvRecords(value: string): UnstructuredFirFindingInput[] {
  const rows = readCsvRows(value)
  const headerRow = rows[0]
  if (!headerRow) {
    throw new Error('CSV batch is missing a header row.')
  }

  const headers = headerRow.map((header) => header.trim().toLowerCase())
  const firIdIndex = headers.findIndex((header) => FIR_ID_KEYS.has(header))
  const textIndex = headers.findIndex((header) => TEXT_KEYS.has(header))
  const jurisdictionIndex = headers.findIndex((header) =>
    JURISDICTION_KEYS.has(header),
  )

  if (firIdIndex === -1 || textIndex === -1) {
    throw new Error(
      'CSV batch must include fir_id,raw_text or fir_id,jurisdiction,raw_text headers.',
    )
  }

  const records: UnstructuredFirFindingInput[] = []
  for (let index = 1; index < rows.length; index += 1) {
    const row = rows[index]
    if (!row) continue
    const sourceRef = (row[firIdIndex] ?? '').trim()
    const text = (row[textIndex] ?? '').trim()
    if (!sourceRef && !text) continue
    if (!sourceRef) {
      throw new Error(`CSV row ${index} is missing fir_id.`)
    }
    if (!text) {
      throw new Error(`CSV row ${index} is missing raw_text.`)
    }

    const jurisdiction =
      jurisdictionIndex === -1
        ? DEFAULT_JURISDICTION
        : (row[jurisdictionIndex] ?? '').trim() || DEFAULT_JURISDICTION

    records.push({
      source: DEFAULT_SOURCE,
      source_ref: sourceRef,
      jurisdiction,
      text,
    })
  }

  return records
}

function readCsvRows(value: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let inQuotes = false

  for (let index = 0; index < value.length; index += 1) {
    const char = value[index]

    if (inQuotes) {
      if (char === '"') {
        if (value[index + 1] === '"') {
          field += '"'
          index += 1
        } else {
          inQuotes = false
        }
        continue
      }
      field += char
      continue
    }

    if (char === '"') {
      inQuotes = true
      continue
    }

    if (char === ',') {
      row.push(field)
      field = ''
      continue
    }

    if (char === '\n' || char === '\r') {
      if (char === '\r' && value[index + 1] === '\n') index += 1
      row.push(field)
      field = ''
      if (row.some((cell) => cell.trim())) rows.push(row)
      row = []
      continue
    }

    field += char
  }

  if (inQuotes) {
    throw new Error('CSV batch has an unclosed quote.')
  }

  row.push(field)
  if (row.some((cell) => cell.trim())) rows.push(row)
  return rows
}
