import express, { Request, Response, Router } from 'express';

const router: Router = express.Router();

// Default rules. You can adapt this to read from DB or env.
const ALLOW_DEFAULT = [
  'wikipedia.org',
  'khanacademy.org',
  'coursera.org',
  'edx.org',
  'docs.google.com',
  'stackoverflow.com',
  'stackexchange.com',
  'unacademy.com',
  'physicswallah.live',
  'pw.live',
  'youtube.com',
];

const BLOCK_DEFAULT = ['instagram.com', 'instagr.am'];

// GET /api/enforcement/rules
router.get('/rules', async (_req: Request, res: Response) => {
  try {
    return res.json({ allow: ALLOW_DEFAULT, block: BLOCK_DEFAULT });
  } catch (e) {
    return res.status(500).json({ error: (e as Error).message });
  }
});

export default router;
