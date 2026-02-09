const STORAGE_KEY = 'ktizo-theme'
const VALID_THEMES = ['light', 'dark', 'moonlight']
const DEFAULT_THEME = 'light'

function getTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && VALID_THEMES.includes(stored)) return stored
  return DEFAULT_THEME
}

function setTheme(theme) {
  if (!VALID_THEMES.includes(theme)) theme = DEFAULT_THEME
  localStorage.setItem(STORAGE_KEY, theme)
  applyTheme(theme)
}

function applyTheme(theme) {
  if (theme === 'light') {
    document.documentElement.removeAttribute('data-theme')
  } else {
    document.documentElement.setAttribute('data-theme', theme)
  }
}

function initTheme() {
  const theme = getTheme()
  applyTheme(theme)
  return theme
}

export default { getTheme, setTheme, initTheme, VALID_THEMES }
