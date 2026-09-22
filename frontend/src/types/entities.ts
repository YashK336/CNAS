/**
 * Entity shapes returned by `/entities/*`.
 * Field names mirror the backend CSV columns exactly.
 */

/** `GET /entities/persons` and `GET /entities/persons/{person_id}`. */
export interface Person {
  person_id: string
  name: string
  phone: string | null
  vehicle_no: string | null
  bank_account: string | null
  social_id: string | null
  home_city: string | null
  risk_group: string | null
}

/** `GET /entities/vehicles`. */
export interface Vehicle {
  person_id: string
  vehicle_no: string
  registered_city: string | null
  vehicle_type: string | null
}

/**
 * `GET /entities/phones` — rows of the entity mapping table filtered to
 * `entity_type === 'phone'`.
 */
export interface EntityMapping {
  entity_id: string
  entity_type: string
  source: string
  source_id: string
}

/** `GET /entities/locations` — distinct home cities. */
export interface LocationRecord {
  location: string
}
