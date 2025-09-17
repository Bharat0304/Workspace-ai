import express, { Request, Response, Router } from 'express';
import Session from '../models/Session';
import ScreenMonitoringService from '../services/screenMonitoring';
// Auth removed for easier testing

const router: Router = express.Router();

// Start monitoring session (no auth) - requires sessionId and userId in body
router.post('/start', async (req: Request, res: Response) => {
  try {
    const { sessionId, userId }: { sessionId: string; userId: string } = req.body;
    if (!sessionId || !userId) {
      return res.status(400).json({ error: 'sessionId and userId are required' });
    }

    // Get screen monitor from app
    const screenMonitor: ScreenMonitoringService = req.app.get('screenMonitor');
    await screenMonitor.startMonitoring(userId, sessionId);

    return res.json({
      success: true,
      message: 'Monitoring started',
      sessionId,
    });
  } catch (error) {
    return res.status(500).json({ error: (error as Error).message });
  }
});

// Stop monitoring session (no auth) - requires userId in body
router.post('/stop', async (req: Request, res: Response) => {
  try {
    const { userId }: { userId: string } = req.body;
    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    // Get screen monitor from app
    const screenMonitor: ScreenMonitoringService = req.app.get('screenMonitor');
    screenMonitor.stopMonitoring(userId);

    return res.json({
      success: true,
      message: 'Monitoring stopped',
    });
  } catch (error) {
    return res.status(500).json({ error: (error as Error).message });
  }
});

// Get monitoring status (no auth)
router.get('/status/:sessionId', async (req: Request, res: Response) => {
  try {
    const { sessionId } = req.params;
    
    const session = await Session.findById(sessionId).populate('userId', 'name email');

    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    return res.json({
      session,
      isActive: session.status === 'active',
    });
  } catch (error) {
    return res.status(500).json({ error: (error as Error).message });
  }
});

export default router;
