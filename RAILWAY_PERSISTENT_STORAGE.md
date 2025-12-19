# Railway Persistent Storage Setup

## Problem
Images uploaded to the application are lost after redeployment because Railway's filesystem is ephemeral by default. Files saved to the application directory are wiped on each redeploy.

## Solution
Use Railway's Persistent Volume feature to store uploaded images in a location that survives redeployments.

## Setup Instructions

### Step 1: Create a Persistent Volume in Railway

1. Go to your Railway project dashboard
2. Click on your service
3. Click on the **"Volumes"** tab
4. Click **"New Volume"**
5. Configure the volume:
   - **Name**: `uploads` (or any name you prefer)
   - **Mount Path**: `/data`
   - **Size**: Choose appropriate size (e.g., 1GB for small apps, 10GB+ for larger apps)
6. Click **"Create"**

### Step 2: Set Environment Variable (Optional)

You can explicitly set the upload folder path via environment variable:

1. Go to your Railway service
2. Click on the **"Variables"** tab
3. Add a new variable:
   - **Key**: `UPLOAD_FOLDER`
   - **Value**: `/data/uploads`
4. Click **"Add"**

**Note**: If you don't set this variable, the app will automatically detect the `/data` directory and use `/data/uploads` automatically.

### Step 3: Redeploy

After creating the volume and setting the environment variable (if desired), redeploy your application:

1. Railway will automatically redeploy, or
2. You can manually trigger a redeploy from the dashboard

### Step 4: Verify

1. Upload an image through your application
2. Check that it's saved to `/data/uploads/` (you can verify via Railway's logs or by checking if the image persists after redeployment)
3. Redeploy the application
4. Verify the image still loads after redeployment

## How It Works

The application automatically detects if it's running on Railway with a persistent volume:

1. **If `UPLOAD_FOLDER` environment variable is set**: Uses that path
2. **If `/data` directory exists**: Uses `/data/uploads` (Railway persistent volume)
3. **Otherwise**: Uses `static/uploads` (local development)

## Directory Structure on Railway

```
/data/uploads/
├── slides/              # Homepage slide images
│   └── default/         # Default/stock slide images
├── books/
│   ├── covers/         # Book cover images
│   │   └── default/     # Default/stock book cover images
│   └── pdfs/            # PDF files for books
├── recipes/             # Recipe images
└── products/            # Product images
```

## Important Notes

- **Persistent volumes are persistent**: Files saved to `/data/uploads/` will survive redeployments
- **Backup your data**: Consider setting up automated backups of your persistent volume
- **Volume size**: Make sure your volume has enough space for all uploaded images
- **Cost**: Railway charges for persistent volume storage (check current pricing)

## Troubleshooting

### Images still not persisting after redeploy

1. **Check volume is mounted**: Verify the volume is created and mounted at `/data`
2. **Check environment variable**: Ensure `UPLOAD_FOLDER` is set correctly (or let auto-detection work)
3. **Check logs**: Look for any errors in Railway logs about file saving
4. **Verify path**: Check that images are actually being saved to `/data/uploads/` and not `static/uploads/`

### How to check if volume is working

1. Upload an image through your app
2. Check Railway logs for the save path - it should show `/data/uploads/...`
3. Redeploy the app
4. Check if the image still loads - if yes, persistent storage is working!

## Alternative: Cloud Storage

If you prefer not to use Railway's persistent volumes, you can integrate with cloud storage:

- **AWS S3**: Use `boto3` to upload images to S3
- **Cloudinary**: Use `cloudinary` library for image hosting
- **Google Cloud Storage**: Use `google-cloud-storage` library

This requires additional code changes and is more complex but provides better scalability.

