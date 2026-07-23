/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Pravasi Setu Assistant palette — ported verbatim from the
        // reference build so the Yatra chat shell matches pixel-for-pixel.
        //   Primary   = bright blue #2563EB (chat bubbles, buttons, menu icons)
        //   Primary-50 = lavender-blue tint for soft surfaces
        //   AI chip   = yellow ring + soft yellow fill around the avatar
        ink:        '#0F172A',
        muted:      '#475569',
        bdr:        '#E2E8F0',
        'bdr-soft': '#F1F5F9',
        surface:    '#FFFFFF',
        'surface-2':'#F8FAFC',

        primary:      '#2563EB',   // blue-600
        'primary-50': '#EFF6FF',
        'primary-100':'#DBEAFE',
        'primary-200':'#BFDBFE',
        'primary-600':'#2563EB',
        'primary-700':'#1D4ED8',

        // Lavender used by soft cards — slightly warmer than primary-50 so
        // it stands out as a distinct surface tone.
        'lavender-50':  '#EEF2FF',
        'lavender-100': '#E0E7FF',

        // AI badge — yellow ring around the assistant avatar
        'ai-ring':     '#FACC15',   // yellow-400
        'ai-ring-soft':'#FEF3C7',   // yellow-100 fill

        user:  '#2563EB',
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
      boxShadow: {
        card:  '0 1px 2px rgba(15,23,42,0.06), 0 1px 3px rgba(15,23,42,0.04)',
        drawer:'-16px 0 48px rgba(15,23,42,0.14)',
      },
    },
  },
  plugins: [],
}
