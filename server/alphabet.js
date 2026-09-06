// Alphabet and normalization definitions for Categories game

export const ALPHABETS = {
  ar: {
    standard: [
      'أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر',
      'ز', 'س', 'ش', 'ص', 'ط', 'ع', 'ف', 'ق', 'ك', 'ل',
      'م', 'ن', 'هـ', 'و', 'ي'
    ],
    rare: ['ض', 'ظ', 'غ']
  },
  en: {
    standard: [
      'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
      'K', 'L', 'M', 'N', 'O', 'P', 'R', 'S', 'T', 'U',
      'V', 'W', 'Y'
    ],
    rare: ['Q', 'X', 'Z']
  },
  fr: {
    standard: [
      'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
      'L', 'M', 'N', 'O', 'P', 'R', 'S', 'T', 'U', 'V'
    ],
    rare: ['Q', 'W', 'X', 'Y', 'Z']
  }
};

/**
 * Get available letters for a room based on language and settings
 */
export function getLetterPool(lang = 'ar', includeRare = false) {
  const config = ALPHABETS[lang] || ALPHABETS.ar;
  if (includeRare) {
    return [...config.standard, ...config.rare];
  }
  return [...config.standard];
}

/**
 * Normalize an Arabic string for matching and comparison
 */
export function normalizeArabic(str = '', stripDefiniteArticle = false) {
  if (!str) return '';
  let s = str
    .trim()
    // Remove Arabic diacritics / tashkeel
    .replace(/[\u064B-\u065F\u0670]/g, '')
    // Remove tatweel
    .replace(/\u0640/g, '')
    // Normalize alifs: إ, أ, آ, ٱ -> ا
    .replace(/[إأآٱ]/g, 'ا')
    // Normalize taa marbuta -> ha
    .replace(/ة/g, 'ه')
    // Normalize alif maksura -> ya
    .replace(/ى/g, 'ي')
    // Collapse extra whitespaces
    .replace(/\s+/g, ' ')
    .toLowerCase();

  if (stripDefiniteArticle && s.startsWith('ال') && s.length > 3) {
    if (!['المانيا', 'البانيا'].includes(s)) {
      s = s.slice(2);
    }
  }

  return s;
}

/**
 * Normalize a Latin (English / French) string
 */
export function normalizeLatin(str = '', lang = 'en', stripArticle = false) {
  if (!str) return '';
  let s = str
    .trim()
    // Normalize accents (e.g. é -> e)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ');

  if (stripArticle) {
    if (lang === 'fr') {
      s = s.replace(/^(?:le|la|les|un|une)\s+|^l['’]/, '');
    } else {
      s = s.replace(/^(?:the|a|an)\s+/, '');
    }
  }

  return s;
}

/**
 * General answer normalization for duplicate matching across players
 */
export function normalizeAnswer(str = '', lang = 'ar') {
  if (!str) return '';
  if (lang === 'ar') {
    return normalizeArabic(str, true);
  }
  return normalizeLatin(str, lang, true);
}

/**
 * Checks if a word starts with the specified round letter
 */
export function doesWordStartWithLetter(word = '', letter = '', lang = 'ar') {
  const rawWord = (word || '').trim();
  if (!rawWord || !letter) return false;

  if (lang === 'ar') {
    const normWord = normalizeArabic(rawWord, false);
    const normLetter = normalizeArabic(letter, false);

    // Letter is Alif ('أ' or 'ا')
    if (normLetter === 'ا') {
      // 1. Explicit hamzat qat' at start (e.g. ألمانيا, أحمد, إبراهيم, آسيا)
      if (/^[أإآ]/.test(rawWord)) {
        return true;
      }
      // 2. Starts with 'ال': check if word without 'ال' starts with Alif (e.g. الأسد / الاسد -> أسد / اسد)
      if (normWord.startsWith('ال') && normWord.length > 2) {
        if (normWord.slice(2).startsWith('ا')) {
          return true;
        }
        // Known proper names starting with Al- that are not the Arabic definite article
        if (['المانيا', 'البانيا', 'الماس'].includes(normWord)) {
          return true;
        }
        // Words like الكلب, القط, المغرب, القاهرة start with ك, ق, م and NOT Alif!
        return false;
      }
      // 3. Regular word starting with Alif (e.g. احمد, اسد, ارنب)
      return normWord.startsWith('ا');
    }

    // Direct match: first letter
    if (normWord.startsWith(normLetter)) {
      return true;
    }

    // Special Arabic case: word starts with definite article 'ال' (Al-)
    // Example: If letter is 'م' and word is 'المغرب', without 'ال' it is 'مغرب' which starts with 'م'
    if (normWord.startsWith('ال') && normWord.length > 2) {
      const withoutAl = normWord.slice(2);
      if (withoutAl.startsWith(normLetter)) {
        return true;
      }
    }

    // Special letter: 'هـ' matches 'ه'
    if (normLetter === 'ه' && normWord.startsWith('ه')) {
      return true;
    }

    return false;
  }

  // Latin (English / French)
  const normWord = normalizeLatin(rawWord, lang, false);
  const normLetter = normalizeLatin(letter, lang, false);
  const strippedWord = normalizeLatin(rawWord, lang, true);

  // If word has a leading article (e.g. "The Lion", "Le Tigre"), match against the stripped noun
  if (strippedWord !== normWord) {
    return strippedWord.startsWith(normLetter);
  }

  return normWord.startsWith(normLetter);
}
