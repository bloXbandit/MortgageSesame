/**
 * Central config for the admin app.
 * All operator-specific values live here — driven by VITE_ env vars.
 * To white-label for another banker, update .env only — never touch this file.
 */

export const API           = import.meta.env.VITE_API_URL      || 'http://localhost:8000'
export const BANKER_NAME   = import.meta.env.VITE_BANKER_NAME  || ''
export const BANKER_NMLS   = import.meta.env.VITE_BANKER_NMLS  || ''
export const CALCOM        = import.meta.env.VITE_CALCOM_URL   || ''
export const APP_1003      = import.meta.env.VITE_APP_1003_URL || ''
export const ZILLOW        = import.meta.env.VITE_ZILLOW_URL   || ''
export const SERVICE_STATES = import.meta.env.VITE_SERVICE_STATES || ''
