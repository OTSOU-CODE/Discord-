// Fixed categories for Categories (أتوبيس كومبلي)

export const CATEGORIES = [
  {
    id: 'boy',
    labels: {
      ar: 'ولد',
      en: "Boy's Name",
      fr: 'Prénom Garçon'
    },
    icon: 'User',
    placeholder: {
      ar: 'مثال: أحمد، عمر...',
      en: 'e.g. Alex, Bob...',
      fr: 'ex. Antoine, Bruno...'
    }
  },
  {
    id: 'girl',
    labels: {
      ar: 'بنت',
      en: "Girl's Name",
      fr: 'Prénom Fille'
    },
    icon: 'Heart',
    placeholder: {
      ar: 'مثال: سارة، مريم...',
      en: 'e.g. Alice, Bella...',
      fr: 'ex. Camille, Diane...'
    }
  },
  {
    id: 'animal',
    labels: {
      ar: 'حيوان',
      en: 'Animal',
      fr: 'Animal'
    },
    icon: 'PawPrint',
    placeholder: {
      ar: 'مثال: أسد، نمر...',
      en: 'e.g. Ant, Bear...',
      fr: 'ex. Aigle, Baleine...'
    }
  },
  {
    id: 'plant',
    labels: {
      ar: 'نبات / خضر وفواكه',
      en: 'Fruit / Vegetable',
      fr: 'Fruit / Légume'
    },
    icon: 'Apple',
    placeholder: {
      ar: 'مثال: تفاح، برتقال...',
      en: 'e.g. Apple, Banana...',
      fr: 'ex. Ananas, Banane...'
    }
  },
  {
    id: 'object',
    labels: {
      ar: 'جماد',
      en: 'Object / Inanimate',
      fr: 'Objet'
    },
    icon: 'Box',
    placeholder: {
      ar: 'مثال: قلم، طاولة...',
      en: 'e.g. Axe, Book...',
      fr: 'ex. Armoire, Bouteille...'
    }
  },
  {
    id: 'city',
    labels: {
      ar: 'مدينة',
      en: 'City',
      fr: 'Ville'
    },
    icon: 'Building2',
    placeholder: {
      ar: 'مثال: القاهرة، باريس...',
      en: 'e.g. Amsterdam, Berlin...',
      fr: 'ex. Alger, Bordeaux...'
    }
  },
  {
    id: 'country',
    labels: {
      ar: 'دولة',
      en: 'Country',
      fr: 'Pays'
    },
    icon: 'Globe',
    placeholder: {
      ar: 'مثال: مصر، فرنسا...',
      en: 'e.g. Algeria, Brazil...',
      fr: 'ex. Allemagne, Brésil...'
    }
  },
  {
    id: 'profession',
    labels: {
      ar: 'مهنة',
      en: 'Profession',
      fr: 'Métier'
    },
    icon: 'Briefcase',
    placeholder: {
      ar: 'مثال: طبيب، مهندس...',
      en: 'e.g. Actor, Baker...',
      fr: 'ex. Avocat, Boucher...'
    }
  },
  {
    id: 'color',
    labels: {
      ar: 'لون',
      en: 'Color',
      fr: 'Couleur'
    },
    icon: 'Palette',
    placeholder: {
      ar: 'مثال: أزرق، أحمر...',
      en: 'e.g. Amber, Blue...',
      fr: 'ex. Argent, Bleu...'
    }
  }
];

export function getCategoryList(lang = 'ar') {
  return CATEGORIES.map(cat => ({
    id: cat.id,
    label: cat.labels[lang] || cat.labels.ar,
    placeholder: cat.placeholder[lang] || cat.placeholder.ar,
    icon: cat.icon
  }));
}
