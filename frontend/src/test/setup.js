import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest globals are disabled (explicit imports keep lint happy), so Testing
// Library cannot auto-register its cleanup hook. Register it here.
afterEach(() => {
  cleanup()
})

// jsdom does not implement matchMedia; the theme provider needs it to resolve
// the "system" preference. Default to light mode in tests.
if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })
}
