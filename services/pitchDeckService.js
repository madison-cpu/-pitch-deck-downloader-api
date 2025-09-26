const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');
const { PDFDocument } = require('pdf-lib');
const sharp = require('sharp');

class PitchDeckService {
  constructor() {
    this.jobs = new Map();
    this.uploadsDir = path.join(__dirname, '..', 'uploads');
  }

  async downloadPitchDeck(url, options = {}) {
    const { jobId, waitTime = 2000 } = options;
    
    this.jobs.set(jobId, {
      status: 'starting',
      progress: 0,
      error: null,
      downloadUrl: null,
      timestamp: Date.now()
    });

    let browser;
    try {
      this.updateJobStatus(jobId, 'launching_browser', 10);

      browser = await puppeteer.launch({
        headless: 'new',
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--window-size=1280,720',
          '--memory-pressure-off'
        ],
        defaultViewport: {
          width: 1280,
          height: 720,
          deviceScaleFactor: 1
        },
        timeout: 30000
      });

      const page = await browser.newPage();
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

      this.updateJobStatus(jobId, 'loading_page', 20);

      await page.goto(url, {
        waitUntil: 'domcontentloaded',
        timeout: 20000
      });

      await page.waitForTimeout(waitTime);
      this.updateJobStatus(jobId, 'detecting_slides', 30);

      const slideCount = await this.detectSlideCount(page);
      console.log(`Detected ${slideCount} slides`);

      if (slideCount === 0) {
        throw new Error('No slides detected in the presentation');
      }

      this.updateJobStatus(jobId, 'capturing_screenshots', 40);
      const screenshots = await this.captureAllSlides(page, slideCount, jobId);

      this.updateJobStatus(jobId, 'compiling_pdf', 80);
      const filename = `pitch-deck-${jobId}.pdf`;
      const pdfPath = await this.compilePDF(screenshots, filename);

      this.updateJobStatus(jobId, 'completed', 100, null, `/download/${filename}`);

      return {
        downloadUrl: `/download/${filename}`,
        filename,
        slideCount,
        pdfPath
      };

    } catch (error) {
      console.error('Error in downloadPitchDeck:', error);
      this.updateJobStatus(jobId, 'failed', 0, error.message);
      throw error;
    } finally {
      if (browser) {
        await browser.close();
      }
    }
  }

  async detectSlideCount(page) {
    try {
      const slideSelectors = [
        '[data-testid="slide"]',
        '.slide',
        '[class*="slide"]',
        '[data-slide]',
        '.presentation-slide',
        '[role="presentation"]'
      ];

      for (const selector of slideSelectors) {
        try {
          const elements = await page.$$(selector);
          if (elements.length > 0) {
            console.log(`Found ${elements.length} slides using selector: ${selector}`);
            return elements.length;
          }
        } catch (e) {
          // Continue to next selector
        }
      }

      // Fallback: count by navigation
      return await this.countSlidesByNavigation(page);

    } catch (error) {
      console.error('Error detecting slide count:', error);
      return 1;
    }
  }

  async countSlidesByNavigation(page) {
    try {
      let slideCount = 1;
      const maxSlides = 30;

      for (let i = 0; i < maxSlides; i++) {
        const navigationMethods = [
          () => page.keyboard.press('ArrowRight'),
          () => page.keyboard.press('PageDown'),
          () => page.keyboard.press('Space'),
          () => page.click('[data-testid="next-slide"]'),
          () => page.click('.next-slide')
        ];

        let navigated = false;
        for (const method of navigationMethods) {
          try {
            await method();
            await page.waitForTimeout(300);
            slideCount++;
            navigated = true;
            break;
          } catch (e) {
            // Try next method
          }
        }

        if (!navigated) {
          break;
        }
      }

      await this.goToFirstSlide(page);
      return slideCount;
    } catch (error) {
      console.error('Error counting slides by navigation:', error);
      return 1;
    }
  }

  async goToFirstSlide(page) {
    try {
      const resetMethods = [
        () => page.keyboard.press('Home'),
        () => page.keyboard.press('ArrowLeft'),
        () => page.click('[data-testid="first-slide"]'),
        () => page.click('.first-slide')
      ];

      for (const method of resetMethods) {
        try {
          await method();
          await page.waitForTimeout(300);
          break;
        } catch (e) {
          // Try next method
        }
      }
    } catch (error) {
      console.error('Error going to first slide:', error);
    }
  }

  async captureAllSlides(page, slideCount, jobId) {
    const screenshots = [];
    
    for (let i = 0; i < slideCount; i++) {
      try {
        const progress = 40 + (i / slideCount) * 40;
        this.updateJobStatus(jobId, 'capturing_screenshots', progress);

        console.log(`Capturing slide ${i + 1}/${slideCount}`);
        await page.waitForTimeout(500);

        const screenshot = await page.screenshot({
          type: 'png',
          fullPage: false,
          clip: {
            x: 0,
            y: 0,
            width: 1280,
            height: 720
          }
        });

        const optimizedImage = await sharp(screenshot)
          .png({ quality: 70 })
          .resize(1280, 720, { fit: 'inside', withoutEnlargement: true })
          .toBuffer();

        screenshots.push(optimizedImage);

        if (i < slideCount - 1) {
          await this.navigateToNextSlide(page);
        }

      } catch (error) {
        console.error(`Error capturing slide ${i + 1}:`, error);
      }
    }

    return screenshots;
  }

  async navigateToNextSlide(page) {
    try {
      const navigationMethods = [
        () => page.keyboard.press('ArrowRight'),
        () => page.keyboard.press('PageDown'),
        () => page.keyboard.press('Space'),
        () => page.click('[data-testid="next-slide"]'),
        () => page.click('.next-slide')
      ];

      for (const method of navigationMethods) {
        try {
          await method();
          await page.waitForTimeout(300);
          return;
        } catch (e) {
          // Try next method
        }
      }
    } catch (error) {
      console.error('Error navigating to next slide:', error);
    }
  }

  async compilePDF(screenshots, filename) {
    try {
      const pdfDoc = await PDFDocument.create();

      for (const screenshot of screenshots) {
        const pngImage = await pdfDoc.embedPng(screenshot);
        const page = pdfDoc.addPage([1280, 720]);
        
        const { width, height } = page.getSize();
        const scale = Math.min(width / pngImage.width, height / pngImage.height);
        const scaledWidth = pngImage.width * scale;
        const scaledHeight = pngImage.height * scale;
        
        const x = (width - scaledWidth) / 2;
        const y = (height - scaledHeight) / 2;
        
        page.drawImage(pngImage, {
          x,
          y,
          width: scaledWidth,
          height: scaledHeight,
        });
      }

      const pdfBytes = await pdfDoc.save();
      const pdfPath = path.join(this.uploadsDir, filename);
      await fs.writeFile(pdfPath, pdfBytes);

      console.log(`PDF saved: ${pdfPath}`);
      return pdfPath;

    } catch (error) {
      console.error('Error compiling PDF:', error);
      throw error;
    }
  }

  updateJobStatus(jobId, status, progress, error = null, downloadUrl = null) {
    const currentStatus = this.jobs.get(jobId) || {};
    this.jobs.set(jobId, {
      ...currentStatus,
      status,
      progress,
      error,
      downloadUrl,
      timestamp: Date.now()
    });
  }

  getJobStatus(jobId) {
    return this.jobs.get(jobId) || {
      status: 'not_found',
      progress: 0,
      error: 'Job not found',
      downloadUrl: null
    };
  }

  async cleanup() {
    try {
      const files = await fs.readdir(this.uploadsDir);
      const now = Date.now();
      const maxAge = 2 * 60 * 60 * 1000; // 2 hours

      for (const file of files) {
        const filePath = path.join(this.uploadsDir, file);
        const stats = await fs.stat(filePath);
        
        if (now - stats.mtime.getTime() > maxAge) {
          await fs.unlink(filePath);
          console.log(`Cleaned up old file: ${file}`);
        }
      }

      for (const [jobId, job] of this.jobs.entries()) {
        if (job.status === 'completed' || job.status === 'failed') {
          const jobAge = Date.now() - (job.timestamp || 0);
          if (jobAge > 30 * 60 * 1000) {
            this.jobs.delete(jobId);
          }
        }
      }

    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }
}

const pitchDeckService = new PitchDeckService();

// Run cleanup every 30 minutes
setInterval(() => {
  pitchDeckService.cleanup();
}, 30 * 60 * 1000);

module.exports = pitchDeckService;