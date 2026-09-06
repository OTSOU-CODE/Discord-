import React, { useState, useEffect } from 'react';
import { socket, saveSession, getSavedSession, clearSession, isStaticHost, hasConfiguredServer } from './socket';
import { TRANSLATIONS } from './constants/translations';
import { Navbar } from './components/Navbar';
import { CreateJoinView } from './components/CreateJoinView';
import { LobbyView } from './components/LobbyView';
import { CarouselRoll } from './components/CarouselRoll';
import { GameRoundView } from './components/GameRoundView';
import { VotingReviewView } from './components/VotingReviewView';
import { LeaderboardView } from './components/LeaderboardView';
import { PodiumModal } from './components/PodiumModal';
import { NetworkModal } from './components/NetworkModal';
import { ServerModal } from './components/ServerModal';
import { playStopAlarm } from './utils/soundEffects';

export function App() {
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [lang, setLang] = useState('ar');
  const [room, setRoom] = useState(null);
  const [playerId, setPlayerId] = useState('');
  const [rollingData, setRollingData] = useState(null);
  const [roundEndTime, setRoundEndTime] = useState(null);
  const [isNetworkModalOpen, setIsNetworkModalOpen] = useState(false);
  const [isServerModalOpen, setIsServerModalOpen] = useState(isStaticHost() && !hasConfiguredServer());
  const [initialJoinCode, setInitialJoinCode] = useState('');
  const [initialDraft, setInitialDraft] = useState({});

  const t = TRANSLATIONS[lang] || TRANSLATIONS.ar;

  // Dynamic RTL and document language adjustment
  useEffect(() => {
    document.documentElement.dir = t.dir;
    document.documentElement.lang = lang;
  }, [lang, t.dir]);

  // Read URL query params on initial mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const joinCode = params.get('join');
    if (joinCode) {
      setInitialJoinCode(joinCode.toUpperCase());
    }

    // Try auto-reconnect if session exists in sessionStorage
    const session = getSavedSession();
    if (session.roomCode && session.playerToken) {
      socket.emit('JOIN_ROOM', {
        roomCode: session.roomCode,
        playerToken: session.playerToken
      }, (res) => {
        if (res?.success) {
          setRoom(res.room);
          setPlayerId(res.playerId);
          if (res.room.settings?.lang) {
            setLang(res.room.settings.lang);
          }
          if (res.room.roundEndTime) {
            setRoundEndTime(res.room.roundEndTime);
          }
          if (res.myDraft) {
            setInitialDraft(res.myDraft);
          }
        } else {
          clearSession();
        }
      });
    }
  }, []);

  // Socket event listeners
  useEffect(() => {
    const onConnect = () => {
      setIsConnected(true);
      // Auto-reconnect session when socket connection is established / re-established
      const session = getSavedSession();
      if (session.roomCode && session.playerToken) {
        socket.emit('JOIN_ROOM', {
          roomCode: session.roomCode,
          playerToken: session.playerToken
        }, (res) => {
          if (res?.success) {
            setRoom(res.room);
            setPlayerId(res.playerId);
            if (res.room.settings?.lang) {
              setLang(res.room.settings.lang);
            }
            if (res.room.roundEndTime) {
              setRoundEndTime(res.room.roundEndTime);
            }
            if (res.myDraft) {
              setInitialDraft(res.myDraft);
            }
          } else {
            clearSession();
          }
        });
      }
    };

    const onDisconnect = () => setIsConnected(false);

    const onRoomUpdated = (data) => {
      if (data?.room) {
        setRoom(data.room);
        if (data.room.settings?.lang) {
          setLang(data.room.settings.lang);
        }
      }
    };

    const onRoundRolling = (data) => {
      setRollingData(data);
      setRoom(prev => prev ? { 
        ...prev, 
        status: 'ROLLING', 
        currentRound: data.roundNumber,
        currentLetter: data.letter 
      } : prev);
    };

    const onRoundStarted = (data) => {
      setRollingData(null);
      setRoundEndTime(data.roundEndTime);
      setRoom(prev => prev ? { 
        ...prev, 
        status: 'PLAYING', 
        currentLetter: data.letter,
        currentRound: data.roundNumber 
      } : prev);
    };

    const onRoundStopped = (data) => {
      playStopAlarm();
      setRoom(prev => prev ? { ...prev, status: 'REVIEW', stopTriggeredBy: data.stoppedBy } : prev);
    };

    const onReviewPhaseStarted = (data) => {
      setRollingData(null);
      setRoom(prev => prev ? {
        ...prev,
        status: 'REVIEW',
        currentRound: data.roundNumber,
        currentLetter: data.letter,
        review: data.review
      } : prev);
    };

    const onVoteUpdated = (data) => {
      setRoom(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          review: data.review
        };
      });
    };

    const onReviewCategoryChanged = (data) => {
      setRoom(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          review: {
            ...prev.review,
            categoryIndex: data.categoryIndex
          }
        };
      });
    };

    const onRoundScores = (data) => {
      setRoom(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          status: data.roomStatus,
          review: {
            ...prev.review,
            results: data.results
          }
        };
      });
    };

    const onKicked = (data) => {
      alert(data?.reason || 'You were kicked from the room.');
      clearSession();
      setRoom(null);
      setPlayerId('');
    };

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('ROOM_UPDATED', onRoomUpdated);
    socket.on('ROUND_ROLLING', onRoundRolling);
    socket.on('ROUND_STARTED', onRoundStarted);
    socket.on('ROUND_STOPPED', onRoundStopped);
    socket.on('REVIEW_PHASE_STARTED', onReviewPhaseStarted);
    socket.on('VOTE_UPDATED', onVoteUpdated);
    socket.on('REVIEW_CATEGORY_CHANGED', onReviewCategoryChanged);
    socket.on('ROUND_SCORES', onRoundScores);
    socket.on('KICKED', onKicked);

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('ROOM_UPDATED', onRoomUpdated);
      socket.off('ROUND_ROLLING', onRoundRolling);
      socket.off('ROUND_STARTED', onRoundStarted);
      socket.off('ROUND_STOPPED', onRoundStopped);
      socket.off('REVIEW_PHASE_STARTED', onReviewPhaseStarted);
      socket.off('VOTE_UPDATED', onVoteUpdated);
      socket.off('REVIEW_CATEGORY_CHANGED', onReviewCategoryChanged);
      socket.off('ROUND_SCORES', onRoundScores);
      socket.off('KICKED', onKicked);
    };
  }, []);

  // Room actions
  const handleCreateRoom = ({ playerName, settings }, cb) => {
    if (!socket.connected) {
      if (isStaticHost() && !hasConfiguredServer()) {
        setIsServerModalOpen(true);
        cb('يرجى ضبط خادم اللعبة أولاً في إعدادات الخادم / Please configure backend server in settings first');
      } else {
        cb(t.disconnectWarning || 'Not connected to game server. Reconnecting...');
      }
      return;
    }

    socket.emit('CREATE_ROOM', { playerName, settings }, (res) => {
      if (res?.success) {
        setRoom(res.room);
        setPlayerId(res.playerId);
        saveSession({
          roomCode: res.roomCode,
          playerId: res.playerId,
          playerToken: res.playerToken,
          playerName
        });
        cb(null);
      } else {
        cb(res?.error || 'Failed to create room');
      }
    });
  };

  const handleJoinRoom = ({ playerName, roomCode }, cb) => {
    if (!socket.connected) {
      if (isStaticHost() && !hasConfiguredServer()) {
        setIsServerModalOpen(true);
        cb('يرجى ضبط خادم اللعبة أولاً في إعدادات الخادم / Please configure backend server in settings first');
      } else {
        cb(t.disconnectWarning || 'Not connected to game server. Reconnecting...');
      }
      return;
    }

    socket.emit('JOIN_ROOM', { playerName, roomCode }, (res) => {
      if (res?.success) {
        setRoom(res.room);
        setPlayerId(res.playerId);
        if (res.room.settings?.lang) {
          setLang(res.room.settings.lang);
        }
        saveSession({
          roomCode: res.roomCode,
          playerId: res.playerId,
          playerToken: res.playerToken,
          playerName
        });
        cb(null);
      } else {
        cb(res?.error || 'Failed to join room');
      }
    });
  };

  const handleLeaveRoom = () => {
    socket.emit('LEAVE_ROOM');
    clearSession();
    setRoom(null);
    setPlayerId('');
    window.location.reload();
  };

  const handleStartGame = () => {
    socket.emit('START_GAME');
  };

  const handleKickPlayer = (targetPlayerId) => {
    socket.emit('KICK_PLAYER', { targetPlayerId });
  };

  const handleUpdateSettings = (newSettings) => {
    socket.emit('UPDATE_SETTINGS', { settings: newSettings });
  };

  const handleUpdateDraft = (draft) => {
    socket.emit('UPDATE_DRAFT', { draft });
  };

  const handleSubmitAnswers = (answers) => {
    socket.emit('SUBMIT_ANSWERS', { answers });
  };

  const handleTriggerStop = () => {
    socket.emit('TRIGGER_STOP');
  };

  const handleCastVote = ({ categoryId, targetPlayerId, vote }) => {
    socket.emit('CAST_VOTE', { categoryId, targetPlayerId, vote });
  };

  const handleChangeReviewCategory = (categoryIndex) => {
    socket.emit('CHANGE_REVIEW_CATEGORY', { categoryIndex });
  };

  const handleFinishReview = () => {
    socket.emit('FINISH_REVIEW');
  };

  const handleNextRound = () => {
    socket.emit('NEXT_ROUND');
  };

  const handleRestartGame = () => {
    socket.emit('RESTART_GAME');
  };

  return (
    <div className="min-h-screen bg-notebook-ruled text-ink-900 flex flex-col selection:bg-amber-200">
      
      {/* Top Navigation Bar */}
      <Navbar
        room={room}
        playerId={playerId}
        isConnected={isConnected}
        onLeaveRoom={handleLeaveRoom}
        onOpenNetworkModal={() => setIsNetworkModalOpen(true)}
        onOpenServerModal={() => setIsServerModalOpen(true)}
        t={t}
      />

      {/* Main Game Stage Container */}
      <main className="flex-1 flex flex-col justify-start">
        
        {/* View 1: Not in Room -> Create or Join View */}
        {!room && (
          <CreateJoinView
            onCreateRoom={handleCreateRoom}
            onJoinRoom={handleJoinRoom}
            currentLang={lang}
            onLangChange={setLang}
            initialRoomCode={initialJoinCode}
            t={t}
          />
        )}

        {/* View 2: In Room - Status: LOBBY */}
        {room && room.status === 'LOBBY' && (
          <LobbyView
            room={room}
            playerId={playerId}
            onStartGame={handleStartGame}
            onKickPlayer={handleKickPlayer}
            onUpdateSettings={handleUpdateSettings}
            onOpenNetworkModal={() => setIsNetworkModalOpen(true)}
            t={t}
          />
        )}

        {/* Rolling Letter 3-Second Carousel Overlay */}
        {room && room.status === 'ROLLING' && rollingData && (
          <CarouselRoll
            targetLetter={rollingData.letter}
            pool={rollingData.pool}
            roundNumber={rollingData.roundNumber}
            totalRounds={rollingData.totalRounds}
            t={t}
          />
        )}

        {/* View 3: In Room - Status: PLAYING */}
        {room && room.status === 'PLAYING' && (
          <GameRoundView
            room={room}
            playerId={playerId}
            letter={room.currentLetter}
            roundEndTime={roundEndTime || room?.roundEndTime}
            initialDraft={initialDraft}
            onUpdateDraft={handleUpdateDraft}
            onSubmitAnswers={handleSubmitAnswers}
            onTriggerStop={handleTriggerStop}
            t={t}
          />
        )}

        {/* View 4: In Room - Status: REVIEW (Voting & auto-check) */}
        {room && room.status === 'REVIEW' && (
          <VotingReviewView
            room={room}
            playerId={playerId}
            onCastVote={handleCastVote}
            onChangeCategory={handleChangeReviewCategory}
            onFinishReview={handleFinishReview}
            t={t}
          />
        )}

        {/* View 5: In Room - Status: LEADERBOARD (Round Breakdown) */}
        {room && room.status === 'LEADERBOARD' && (
          <LeaderboardView
            room={room}
            playerId={playerId}
            onNextRound={handleNextRound}
            t={t}
          />
        )}

        {/* View 6: In Room - Status: GAME_OVER (Podium & Confetti) */}
        {room && room.status === 'GAME_OVER' && (
          <PodiumModal
            room={room}
            playerId={playerId}
            onRestartGame={handleRestartGame}
            t={t}
          />
        )}

      </main>

      {/* Network & QR Code Modal */}
      <NetworkModal
        isOpen={isNetworkModalOpen}
        onClose={() => setIsNetworkModalOpen(false)}
        roomCode={room?.code}
        t={t}
      />

      {/* Backend Server Settings Modal */}
      <ServerModal
        isOpen={isServerModalOpen}
        onClose={() => setIsServerModalOpen(false)}
        t={t}
        isConnected={isConnected}
      />

    </div>
  );
}
