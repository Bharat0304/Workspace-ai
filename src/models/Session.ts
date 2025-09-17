import mongoose, { Document, Schema } from 'mongoose';
import { Session as ISession, MonitoringData, CameraData, Intervention, ProductivityMetrics } from '../types';

interface SessionDocument extends Document, Omit<ISession, '_id' | 'userId'> {
  userId: mongoose.Types.ObjectId;
}

const monitoringDataSchema = new Schema<MonitoringData>({
  timestamp: { type: Date, required: true },
  activeWindow: { type: Schema.Types.Mixed },
  screenshotUrl: String,
  isDistraction: { type: Boolean, required: true },
  focusLevel: { type: String, required: true },
  distractionScore: Number,
  productivityScore: Number,
  aiAnalysis: Schema.Types.Mixed,
});

const cameraDataSchema = new Schema<CameraData>({
  timestamp: { type: Date, required: true },
  focusScore: { type: Number, required: true },
  eyeGaze: { type: String, required: true },
  posture: { type: String, required: true },
  faceDetected: { type: Boolean, required: true },
  emotionState: String,
  attentionLevel: String,
  aiAnalysis: Schema.Types.Mixed,
});

const interventionSchema = new Schema<Intervention>({
  type: { type: String, required: true },
  timestamp: { type: Date, required: true },
  data: { type: Schema.Types.Mixed, required: true },
  executed: { type: Boolean, required: true },
});

const productivitySchema = new Schema<ProductivityMetrics>({
  focusPercentage: { type: Number, default: 0 },
  distractionCount: { type: Number, default: 0 },
  averageFocusScore: { type: Number, default: 0 },
  totalBreaks: { type: Number, default: 0 },
});

const sessionSchema = new Schema<SessionDocument>({
  userId: {
    type: Schema.Types.ObjectId,
    ref: 'User',
    required: true,
  },
  startTime: {
    type: Date,
    default: Date.now,
  },
  endTime: Date,
  duration: Number,
  subject: String,
  goalMinutes: Number,
  status: {
    type: String,
    enum: ['active', 'paused', 'completed', 'interrupted'],
    default: 'active',
  },
  monitoringData: [monitoringDataSchema],
  cameraData: [cameraDataSchema],
  interventions: [interventionSchema],
  productivity: {
    type: productivitySchema,
    default: () => ({}),
  },
}, {
  timestamps: true,
});

// Calculate productivity metrics before saving
sessionSchema.pre('save', function(this: SessionDocument, next) {
  if (this.monitoringData && this.monitoringData.length > 0) {
    const distractions = this.monitoringData.filter((d: MonitoringData) => d.isDistraction);
    this.productivity.distractionCount = distractions.length;
    this.productivity.focusPercentage = 
      ((this.monitoringData.length - distractions.length) / this.monitoringData.length) * 100;
  }
  
  if (this.cameraData && this.cameraData.length > 0) {
    const totalFocusScore = this.cameraData.reduce((sum: number, d: CameraData) => sum + d.focusScore, 0);
    this.productivity.averageFocusScore = totalFocusScore / this.cameraData.length;
  }
  
  next();
});

export default mongoose.model<SessionDocument>('Session', sessionSchema);
