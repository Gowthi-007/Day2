# Interface Contract: MedPulse Vitals Ingestion

## Endpoint
POST /v1/vitals

## Structural Constraints
* patient_id: String (Must conform strictly to standard RFC 4122 UUID format)
* heart_rate: Integer (Valid physical range: 30 to 250 BPM inclusive)
* status: Enum String (Mutually exclusive choices: [NORMAL, ELEVATED, CRITICAL])