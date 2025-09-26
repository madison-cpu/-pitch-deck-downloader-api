# Pitch.com Downloader API - Simplified Version

## 🎯 **Streamlined for Reliability**

This is a simplified version that follows your exact workflow:
1. **Detect slide count** (fast method)
2. **Go to first slide** 
3. **Screenshot current slide**
4. **Navigate right** (arrow key)
5. **Repeat** until all slides captured
6. **Create PDF** from screenshots

## 🚀 **Deploy to Render.com**

1. **Upload all files** to your GitHub repository root
2. **Connect to Render.com**
3. **Deploy** using the included `render.yaml`

## 📊 **API Usage**

```bash
curl -X POST https://your-api.onrender.com/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://pitch.com/v/yzi-ui28ms/903508bb-e58f-48ae-a604-75952bc1aecd",
    "format": "base64",
    "filename": "byte-pitch-deck",
    "options": {
      "max_slides": 15
    }
  }'
```

## ✅ **Key Improvements**

- **No complex slide detection** that causes timeouts
- **Fast navigation** using keyboard arrows
- **Simplified PDF generation** 
- **Reduced timeout** (3 minutes max)
- **Better error handling**

## 🎉 **Expected Results**

- ✅ **Detects 9 slides** from BYTE presentation
- ✅ **Captures all slides** properly
- ✅ **Creates landscape PDF**
- ✅ **Returns base64** for n8n/Monday.com
- ✅ **Completes in 2-3 minutes**

