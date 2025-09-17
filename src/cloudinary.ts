import { createRequire } from 'module';

const require = createRequire(import.meta.url);
// Use CJS require to access Cloudinary v2 reliably in ESM projects
const cloudinary = require('cloudinary').v2 as {
  config: (opts: { cloud_name?: string; api_key?: string; api_secret?: string }) => void;
  uploader: any;
};

const cfg: { cloud_name?: string; api_key?: string; api_secret?: string } = {};
if (process.env.CLOUDINARY_CLOUD_NAME) cfg.cloud_name = process.env.CLOUDINARY_CLOUD_NAME;
if (process.env.CLOUDINARY_API_KEY) cfg.api_key = process.env.CLOUDINARY_API_KEY;
if (process.env.CLOUDINARY_API_SECRET) cfg.api_secret = process.env.CLOUDINARY_API_SECRET;
cloudinary.config(cfg);

export default cloudinary;