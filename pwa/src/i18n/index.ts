import deCH from './de-CH'
import enUS from './en-US'
import frFR from './fr-FR'
import ptPT from './pt-PT'

export default {
  // German variants all use Swiss German
  de: deCH,
  'de-AT': deCH,
  'de-CH': deCH,
  'de-DE': deCH,
  'de-LI': deCH,

  // English variants all use US English
  en: enUS,
  'en-AU': enUS,
  'en-CA': enUS,
  'en-GB': enUS,
  'en-US': enUS,

  // Portuguese variants use European Portuguese
  pt: ptPT,
  'pt-PT': ptPT,
  'pt-BR': ptPT,

  // French variants all use French
  fr: frFR,
  'fr-BE': frFR,
  'fr-CA': frFR,
  'fr-CH': frFR,
  'fr-FR': frFR,
}
