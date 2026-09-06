import { normalizeAnswer, doesWordStartWithLetter } from './alphabet.js';
import { CATEGORIES } from './categories.js';

/**
 * Evaluates validity and calculates scores for all players in a round
 * 
 * @param {Object} roundData - Contains round parameters
 * @param {string} roundData.letter - The round's letter
 * @param {string} roundData.lang - Room language ('ar', 'en', 'fr')
 * @param {Array<string>} roundData.playerIds - List of player IDs in the room
 * @param {Object} roundData.answers - { [playerId]: { [categoryId]: string } }
 * @param {Object} roundData.votes - { [`${catId}:${targetPlayerId}`]: { [voterId]: boolean } }
 * @returns {Object} Score details, breakdown per category, and updated totals
 */
export function calculateRoundScores({ letter, lang, playerIds, answers, votes = {} }) {
  const categoryResults = {};
  const playerRoundPoints = {};

  playerIds.forEach(id => {
    playerRoundPoints[id] = 0;
  });

  CATEGORIES.forEach(cat => {
    const catId = cat.id;
    const playerStatuses = {};
    const normCounts = {};
    let totalValidCount = 0;

    // First pass: check validity for each player
    playerIds.forEach(playerId => {
      const playerAnswers = answers[playerId] || {};
      const rawAnswer = (playerAnswers[catId] || '').trim();
      const voteKey = `${catId}:${playerId}`;
      const playerVotes = votes[voteKey] || {};

      const approves = Object.values(playerVotes).filter(v => v === true).length;
      const rejects = Object.values(playerVotes).filter(v => v === false).length;
      const totalVotes = approves + rejects;

      if (!rawAnswer) {
        playerStatuses[playerId] = {
          rawAnswer: '',
          normalized: '',
          isValid: false,
          reason: 'blank',
          startsLetter: false,
          approves,
          rejects,
          points: 0
        };
        return;
      }

      const startsLetter = doesWordStartWithLetter(rawAnswer, letter, lang);
      const normalized = normalizeAnswer(rawAnswer, lang);

      // Determine validity based on auto-check and peer voting
      let isValid = false;
      let reason = 'valid';

      if (startsLetter) {
        // Auto-check passes: valid by default unless peer vote rejects by simple majority (rejects > approves)
        if (totalVotes > 0 && rejects > approves) {
          isValid = false;
          reason = 'rejected_by_vote';
        } else {
          isValid = true;
          reason = totalVotes > 0 ? 'approved_by_vote' : 'valid';
        }
      } else {
        // Auto-check failed (wrong letter): rejected by default unless peers explicitly approve by simple majority (approves > rejects)
        if (totalVotes > 0 && approves > rejects) {
          isValid = true;
          reason = 'approved_by_vote';
        } else {
          isValid = false;
          reason = 'wrong_letter';
        }
      }

      if (isValid) {
        totalValidCount++;
        normCounts[normalized] = (normCounts[normalized] || 0) + 1;
      }

      playerStatuses[playerId] = {
        rawAnswer,
        normalized,
        isValid,
        reason,
        startsLetter,
        approves,
        rejects,
        points: 0
      };
    });

    // Second pass: assign points based on validity and uniqueness
    playerIds.forEach(playerId => {
      const status = playerStatuses[playerId];
      if (!status.isValid) {
        status.points = 0;
        return;
      }

      if (totalValidCount === 1 && playerIds.length > 1) {
        // Only one player in the entire lobby provided a valid answer for this category (20 pts)
        status.points = 20;
        status.pointReason = 'solo_valid';
      } else {
        const count = normCounts[status.normalized] || 1;
        if (count > 1) {
          // Shared by two or more players (5 pts)
          status.points = 5;
          status.pointReason = 'shared';
        } else {
          // Unique valid answer (10 pts)
          status.points = 10;
          status.pointReason = 'unique';
        }
      }

      playerRoundPoints[playerId] += status.points;
    });

    categoryResults[catId] = {
      categoryId: catId,
      playerStatuses,
      totalValidCount
    };
  });

  return {
    categoryResults,
    playerRoundPoints,
    playerScores: playerRoundPoints
  };
}
