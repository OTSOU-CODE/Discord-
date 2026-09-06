import test from 'node:test';
import assert from 'node:assert/strict';
import { doesWordStartWithLetter, normalizeAnswer } from '../server/alphabet.js';
import { calculateRoundScores } from '../server/scoring.js';

test('Alphabet - Arabic First Letter Matching', () => {
  // Direct match
  assert.equal(doesWordStartWithLetter('أحمد', 'أ', 'ar'), true);
  assert.equal(doesWordStartWithLetter('احمد', 'أ', 'ar'), true);
  assert.equal(doesWordStartWithLetter('إبراهيم', 'أ', 'ar'), true);
  assert.equal(doesWordStartWithLetter('آدم', 'أ', 'ar'), true);
  
  // Definite article "ال" (Al-) prefix for non-Alif letters
  assert.equal(doesWordStartWithLetter('المغرب', 'م', 'ar'), true);
  assert.equal(doesWordStartWithLetter('القاهرة', 'ق', 'ar'), true);
  assert.equal(doesWordStartWithLetter('الليمون', 'ل', 'ar'), true);

  // Definite article "ال" with letter Alif ('أ')
  // Valid: base noun starts with Alif
  assert.equal(doesWordStartWithLetter('الأسد', 'أ', 'ar'), true);
  assert.equal(doesWordStartWithLetter('الاسد', 'أ', 'ar'), true);
  assert.equal(doesWordStartWithLetter('الأردن', 'أ', 'ar'), true);
  assert.equal(doesWordStartWithLetter('ألمانيا', 'أ', 'ar'), true);
  assert.equal(doesWordStartWithLetter('المانيا', 'أ', 'ar'), true);

  // INVALID: base noun does NOT start with Alif, even though it has "ال"
  assert.equal(doesWordStartWithLetter('الكلب', 'أ', 'ar'), false, 'الكلب starts with ك, not أ');
  assert.equal(doesWordStartWithLetter('القط', 'أ', 'ar'), false, 'القط starts with ق, not أ');
  assert.equal(doesWordStartWithLetter('السيارة', 'أ', 'ar'), false, 'السيارة starts with س, not أ');
  assert.equal(doesWordStartWithLetter('المغرب', 'أ', 'ar'), false, 'المغرب starts with م, not أ');

  // Mismatch
  assert.equal(doesWordStartWithLetter('سارة', 'م', 'ar'), false);
  assert.equal(doesWordStartWithLetter('', 'م', 'ar'), false);
});

test('Alphabet - English and French First Letter Matching & Article Stripping', () => {
  assert.equal(doesWordStartWithLetter('Apple', 'A', 'en'), true);
  assert.equal(doesWordStartWithLetter('banana', 'B', 'en'), true);
  assert.equal(doesWordStartWithLetter('Cat', 'D', 'en'), false);

  // Leading English articles: "The Lion" is valid for L, not T
  assert.equal(doesWordStartWithLetter('The Lion', 'L', 'en'), true);
  assert.equal(doesWordStartWithLetter('The Lion', 'T', 'en'), false);
  assert.equal(doesWordStartWithLetter('A Bear', 'B', 'en'), true);

  // French accents & articles
  assert.equal(doesWordStartWithLetter('Éléphant', 'E', 'fr'), true);
  assert.equal(doesWordStartWithLetter('âne', 'A', 'fr'), true);
  assert.equal(doesWordStartWithLetter('Le Tigre', 'T', 'fr'), true);
});

test('Alphabet - Duplicate Answer Normalization', () => {
  // Arabic: with and without "ال" should match as duplicate
  assert.equal(normalizeAnswer('المغرب', 'ar'), normalizeAnswer('مغرب', 'ar'));
  assert.equal(normalizeAnswer('التفاح', 'ar'), normalizeAnswer('تفاح', 'ar'));
  assert.equal(normalizeAnswer('الأسد', 'ar'), normalizeAnswer('أسد', 'ar'));
  assert.equal(normalizeAnswer('ألمانيا', 'ar'), normalizeAnswer('المانيا', 'ar'));

  // English: "The Lion" and "Lion" should match as duplicate
  assert.equal(normalizeAnswer('The Lion', 'en'), normalizeAnswer('Lion', 'en'));
  assert.equal(normalizeAnswer('A Bear', 'en'), normalizeAnswer('bear', 'en'));
});

test('Scoring Engine - Uniqueness, Duplication, and Solo Bonus', () => {
  const playerIds = ['p1', 'p2', 'p3'];

  // Test Case 1:
  // p1 says "المغرب", p2 says "مغرب" (normalized duplicate -> 5 pts each)
  // p3 says "مصر" (unique, other players valid -> 10 pts)
  const answers1 = {
    p1: { country: 'المغرب' },
    p2: { country: 'مغرب' }, // normalized duplicate with p1
    p3: { country: 'مصر' }
  };

  const res1 = calculateRoundScores({
    letter: 'م',
    lang: 'ar',
    playerIds,
    answers: answers1,
    votes: {}
  });

  const countryStatus = res1.categoryResults.country.playerStatuses;
  assert.equal(countryStatus.p1.points, 5, 'p1 gets 5 pts for shared answer');
  assert.equal(countryStatus.p2.points, 5, 'p2 gets 5 pts for shared answer');
  assert.equal(countryStatus.p3.points, 10, 'p3 gets 10 pts for unique valid answer');

  // Test Case 2: Solo valid answer in entire lobby -> 20 pts!
  const answers2 = {
    p1: { country: 'Lebanon' },
    p2: { country: '' }, // blank -> 0 pts
    p3: { country: 'Germany' } // wrong letter -> 0 pts
  };

  const res2 = calculateRoundScores({
    letter: 'L',
    lang: 'en',
    playerIds,
    answers: answers2,
    votes: {}
  });

  const countryStatus2 = res2.categoryResults.country.playerStatuses;
  assert.equal(countryStatus2.p1.points, 20, 'Only p1 has valid answer -> 20 pts solo bonus');
  assert.equal(countryStatus2.p2.points, 0, 'Blank -> 0 pts');
  assert.equal(countryStatus2.p3.points, 0, 'Wrong letter -> 0 pts');

  // Test Case 3: Peer vote rejection (2 rejects vs 1 approve -> rejected)
  const answers3 = {
    p1: { object: 'Lamp' },
    p2: { object: 'Laser' }
  };

  const res3 = calculateRoundScores({
    letter: 'L',
    lang: 'en',
    playerIds: ['p1', 'p2', 'p3'],
    answers: answers3,
    votes: {
      'object:p2': { p1: false, p3: false } // 2 rejects against p2
    }
  });

  const objectStatus = res3.categoryResults.object.playerStatuses;
  assert.equal(objectStatus.p2.isValid, false, 'p2 word rejected by majority vote');
  assert.equal(objectStatus.p2.points, 0);
  assert.equal(objectStatus.p1.points, 20, 'p1 is now sole valid answer -> 20 pts');

  // Test Case 4: Tie vote on valid word (1 approve vs 1 reject) -> remains valid
  const res4 = calculateRoundScores({
    letter: 'L',
    lang: 'en',
    playerIds: ['p1', 'p2', 'p3'],
    answers: answers3,
    votes: {
      'object:p2': { p1: false, p3: true } // tie: 1 reject, 1 approve
    }
  });
  assert.equal(res4.categoryResults.object.playerStatuses.p2.isValid, true, 'Tie vote leaves valid word valid');
});
