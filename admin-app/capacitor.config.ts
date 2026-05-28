import { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.mortgagesesame.admin',
  appName: 'MortgageSesame',
  webDir: 'dist',
  // For iOS: server URL is configured at runtime via the Settings screen.
  // The app reads VITE_API_URL from localStorage (set on first launch).
  // On same-WiFi: http://[YOUR_MAC_IP]:8000/api/v1
  server: {
    // Leave androidScheme as https for security
    androidScheme: 'https',
    // allowNavigation for local backend calls
    allowNavigation: ['192.168.*.*', '10.*.*.*', 'localhost'],
  },
  ios: {
    contentInset: 'automatic',
    allowsLinkPreview: false,
    scrollEnabled: true,
  },
  plugins: {
    Preferences: {},
  },
}

export default config
