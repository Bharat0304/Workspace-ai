import express, { Application, Request, Response } from 'express';
import http from 'http';
import { Server as SocketIOServer, Socket } from 'socket.io';
import cors from 'cors';
import mongoose from 'mongoose';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';

// Import routes
import authRoutes from './routes/auth';
import sessionRoutes from './routes/session';
import monitoringRoutes from './routes/monitoring';
import interventionRoutes from './routes/intervention';

// Import services
import ScreenMonitoringService from './services/screenMonitoring';
import CameraMonitoringService from './services/cameraMonitoring';
import PythonBridge from './services/pythonBridge';
import InterventionService from './services/intervention';

// Import types
import { SocketEvents } from './types';

dotenv.config();

const app: Application = express();
let server = http.createServer(app);
const io = new SocketIOServer<SocketEvents>(server, {
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    methods: ['GET', 'POST'],
  },
});

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting (express-rate-limit v7)
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  limit: 1000, // limit each IP to 1000 requests per windowMs
});
app.use(limiter);

// MongoDB connection
const mongoUri: string = process.env.MONGODB_URI || 'mongodb://localhost:27017/workspace-ai';
mongoose.connect(mongoUri, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
} as mongoose.ConnectOptions);

// Initialize Python bridge
const pythonBridge = new PythonBridge();

// Initialize services with Python bridge
const screenMonitor = new ScreenMonitoringService(io, pythonBridge);
const cameraMonitor = new CameraMonitoringService(io, pythonBridge);
const interventionService = new InterventionService();

// Make services available to routes
app.set('screenMonitor', screenMonitor);
app.set('cameraMonitor', cameraMonitor);
app.set('pythonBridge', pythonBridge);

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/session', sessionRoutes);
app.use('/api/monitoring', monitoringRoutes);
app.use('/api/intervention', interventionRoutes);

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
  return res.status(200).json({
    status: 'ok',
    node: process.version,
    env: process.env.NODE_ENV || 'development',
    time: new Date().toISOString(),
  });
});

// Python backend communication endpoint
app.post('/api/python-analysis', async (req: Request, res: Response) => {
  try {
    const { user_id, session_id, analysis_type, result } = req.body;
    
    // Emit results to specific user
    io.to(`user-${user_id}`).emit('python-analysis-result', {
      sessionId: session_id,
      type: analysis_type,
      result: result,
      timestamp: new Date(),
    });
    
    res.json({ success: true });
  } catch (error) {
    console.error('Python analysis callback error:', error);
    res.status(500).json({ error: (error as Error).message });
  }
});

// Socket.IO connection handling
io.on('connection', (socket: Socket) => {
  console.log('Client connected:', socket.id);

  socket.on('join-session', (userId: string) => {
    socket.join(`user-${userId}`);
    console.log(`User ${userId} joined session`);
  });

  socket.on('screen-data', (data: any) => {
    screenMonitor.processScreenData(socket, data);
  });

  socket.on('camera-frame', (data: any) => {
    cameraMonitor.processCameraFrame(socket, data);
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Start Python backend
async function startPythonBackend(): Promise<void> {
  try {
    await pythonBridge.startPythonServer();
    console.log('Python backend started successfully');
  } catch (error) {
    console.error('Failed to start Python backend:', error);
  }
}

let basePort: number = parseInt(process.env.PORT || '5000', 10);

async function startNodeServer(port: number): Promise<void> {
  server.listen(port, async () => {
    console.log(`WorkSpace AI Backend running on port ${port}`);
    await startPythonBackend();
  });

  server.on('error', (err: NodeJS.ErrnoException) => {
    if (err.code === 'EADDRINUSE') {
      const nextPort = port + 1;
      console.warn(`Port ${port} in use, retrying on port ${nextPort}...`);
      // Remove existing error listener to avoid multiple triggers
      server.removeAllListeners('error');
      // Create a new server instance bound to app
      const newServer = http.createServer(app);
      server = newServer;
      io.attach(newServer);
      startNodeServer(nextPort);
    } else {
      console.error('Server failed to start:', err);
      process.exit(1);
    }
  });
}

startNodeServer(basePort);

export default app;
