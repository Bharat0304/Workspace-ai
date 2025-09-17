import express, { Request, Response, Router } from 'express';

const router: Router = express.Router();

// In-memory session store for development fallback
let currentSession: any = null;

// POST /api/session/start
router.post('/start', async (req: Request, res: Response) => {
  try {
    const { subject, goalMinutes } = req.body || {};
    const now = new Date().toISOString();
    currentSession = {
      _id: Math.random().toString(36).slice(2),
      subject,
      goalMinutes,
      status: 'active',
      startTime: now,
    };
    return res.json({ success: true, data: { session: currentSession } });
  } catch (error) {
    return res.status(500).json({ success: false, message: (error as Error).message });
  }
});

// GET /api/session/current
router.get('/current', async (_req: Request, res: Response) => {
  return res.json({ success: true, data: { session: currentSession } });
});

// PUT /api/session/:id/pause
router.put('/:id/pause', async (req: Request, res: Response) => {
  if (!currentSession || currentSession._id !== req.params.id) {
    return res.status(404).json({ success: false, message: 'Session not found' });
  }
  currentSession.status = 'paused';
  return res.json({ success: true, data: { session: currentSession } });
});

// PUT /api/session/:id/resume
router.put('/:id/resume', async (req: Request, res: Response) => {
  if (!currentSession || currentSession._id !== req.params.id) {
    return res.status(404).json({ success: false, message: 'Session not found' });
  }
  currentSession.status = 'active';
  return res.json({ success: true, data: { session: currentSession } });
});

// PUT /api/session/:id/end
router.put('/:id/end', async (req: Request, res: Response) => {
  if (!currentSession || currentSession._id !== req.params.id) {
    return res.status(404).json({ success: false, message: 'Session not found' });
  }
  currentSession.status = 'completed';
  currentSession.endTime = new Date().toISOString();
  const finished = currentSession;
  currentSession = null;
  return res.json({ success: true, data: { session: finished } });
});

export default router;