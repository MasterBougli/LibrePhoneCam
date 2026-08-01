// Translations for both web pages.
//
// Keys used in markup are applied through `data-i18n`; keys built at runtime
// go through `t()`.

export const STRINGS = {
  en: {
    tagline: 'Use this phone as a camera in Streamlabs.',
    quality: 'Quality',
    frameRate: 'Frame rate',
    bitrate: 'Bitrate',
    auto: 'Auto',
    startCamera: 'Start camera',
    flip: 'Flip',
    torch: 'Torch',
    stop: 'Stop',
    hint: 'Your browser will ask for camera permission. Keep this tab open and in front: phones stop the camera when you switch apps.',
    rotate: 'Turn your phone sideways for a landscape image',

    connecting: 'Connecting...',
    live: 'Live',
    waitingViewer: 'Waiting for Streamlabs',
    stopped: 'Stopped',
    reconnecting: 'Reconnecting...',
    waitingPhone: 'Waiting for your phone...',
    connectionLost: 'Connection lost, retrying...',
    serverOffline: 'Server offline, retrying...',

    viewers: (n) => `${n} viewer${n === 1 ? '' : 's'}`,

    errDenied: 'Camera access was denied. Allow it in your browser settings for this site, then reload the page.',
    errBusy: 'The camera is busy. Close any other app using it and try again.',
    errOpen: (msg) => `Could not open the camera: ${msg}`,
    errSwitch: (msg) => `Could not switch camera: ${msg}`,
    errInsecure: 'Open this page over https, since browsers only allow camera access on a secure address.',
    errNoCamera: 'This browser does not offer a camera API.',
    errSuperseded: 'This phone was replaced by another connection.',

    themeToggle: 'Switch between light and dark',
    langToggle: 'Passer en français',
    credit: 'Made by SER-PICO',
    creditTitle: 'Open the project on GitHub',
  },

  fr: {
    tagline: 'Utilisez ce téléphone comme caméra dans Streamlabs.',
    quality: 'Qualité',
    frameRate: 'Images par seconde',
    bitrate: 'Débit',
    auto: 'Auto',
    startCamera: 'Démarrer la caméra',
    flip: 'Pivoter',
    torch: 'Lampe',
    stop: 'Arrêter',
    hint: "Votre navigateur va demander l'accès à la caméra. Gardez cet onglet ouvert et au premier plan : les téléphones coupent la caméra quand vous changez d'application.",
    rotate: "Tournez le téléphone à l'horizontale pour une image paysage",

    connecting: 'Connexion...',
    live: 'En direct',
    waitingViewer: 'En attente de Streamlabs',
    stopped: 'Arrêté',
    reconnecting: 'Reconnexion...',
    waitingPhone: 'En attente du téléphone...',
    connectionLost: 'Connexion perdue, nouvelle tentative...',
    serverOffline: 'Serveur injoignable, nouvelle tentative...',

    viewers: (n) => `${n} spectateur${n === 1 ? '' : 's'}`,

    errDenied: "L'accès à la caméra a été refusé. Autorisez-le dans les réglages du navigateur pour ce site, puis rechargez la page.",
    errBusy: "La caméra est occupée. Fermez les autres applications qui l'utilisent et réessayez.",
    errOpen: (msg) => `Impossible d'ouvrir la caméra : ${msg}`,
    errSwitch: (msg) => `Impossible de changer de caméra : ${msg}`,
    errInsecure: "Ouvrez cette page en https : les navigateurs n'autorisent la caméra que sur une adresse sécurisée.",
    errNoCamera: "Ce navigateur ne propose pas d'API caméra.",
    errSuperseded: 'Ce téléphone a été remplacé par une autre connexion.',

    themeToggle: 'Basculer clair / sombre',
    langToggle: 'Switch to English',
    credit: 'Créé par SER-PICO',
    creditTitle: 'Ouvrir le projet sur GitHub',
  },
};

const STORAGE_KEY = 'lpc-lang';

export function detectLang() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && STRINGS[saved]) return saved;
  return (navigator.language || 'en').toLowerCase().startsWith('fr') ? 'fr' : 'en';
}

export function saveLang(lang) {
  localStorage.setItem(STORAGE_KEY, lang);
}

export function other(lang) {
  return lang === 'fr' ? 'en' : 'fr';
}

export function t(lang, key, ...args) {
  const value = (STRINGS[lang] || STRINGS.en)[key];
  if (value === undefined) return key;
  return typeof value === 'function' ? value(...args) : value;
}

/** Fill every element carrying `data-i18n` with the matching string. */
export function applyDom(lang) {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll('[data-i18n]')) {
    el.textContent = t(lang, el.dataset.i18n);
  }
  for (const el of document.querySelectorAll('[data-i18n-title]')) {
    el.title = t(lang, el.dataset.i18nTitle);
  }
}
