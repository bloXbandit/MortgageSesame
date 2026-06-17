/**
 * Central config for the public site.
 * All operator-specific values live here — driven by VITE_ env vars.
 * To white-label for another banker, update .env only — never touch this file.
 */

export const API           = import.meta.env.VITE_API_URL      || 'http://localhost:8000'
export const BANKER_NAME   = import.meta.env.VITE_BANKER_NAME  || 'Kenneth'
export const BANKER_NMLS   = import.meta.env.VITE_BANKER_NMLS  || '1454510'
export const CALCOM        = import.meta.env.VITE_CALCOM_URL   || 'https://cal.com/kmanjo-vzz/home-purchase-consultation'
export const APP_1003      = import.meta.env.VITE_APP_1003_URL || 'https://2704714.my1003app.com/1454510/register'
export const ZILLOW        = import.meta.env.VITE_ZILLOW_URL   || 'https://www.zillow.com/lender-profile/kmanjo2/'
export const SERVICE_STATES  = import.meta.env.VITE_SERVICE_STATES  || 'Maryland & DC'

// Homepage intro videos — leave blank to hide the section.
// Set to a hosted MP4 URL or path when videos are ready.
export const VIDEO_CONSUMER = import.meta.env.VITE_VIDEO_CONSUMER || ''
export const VIDEO_REALTOR  = import.meta.env.VITE_VIDEO_REALTOR  || ''
