import { Component, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

type StatusResponse = {
  status: string;
  message: string;
  progress: number;
  error: string | null;
};

type VideoItem = {
  video_id: string;
  title: string;
  duration: number;
  thumbnail: string;
  url: string;
};

@Component({
  selector: 'app-root',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  channel = '';
  query = '';

  message = 'Unesi naziv YouTube kanala.';
  progress = 0;

  isPreparing = false;
  isReadyForSearch = false;

  videos: VideoItem[] = [];

  pollInterval: any;

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  private buildChannelUrl(channelName: string): string {
    const clean = channelName.trim().replace(/^@/, '');
    return `https://www.youtube.com/@${clean}/videos`;
  }

  prepareChannel() {
    if (!this.channel.trim()) {
      this.message = 'Unesi naziv kanala.';
      return;
    }

    const fullChannelUrl = this.buildChannelUrl(this.channel);

    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }

    this.message = 'Procesiranje kanala...';
    this.progress = 0;
    this.isPreparing = true;
    this.isReadyForSearch = false;
    this.videos = [];
    this.cdr.detectChanges();

    this.http.post('http://127.0.0.1:8000/prepare', {
      channel: fullChannelUrl
    }).subscribe({
      next: () => {
        this.startPolling();
      },
      error: () => {
        this.message = 'Greška pri pokretanju pripreme.';
        this.isPreparing = false;
        this.isReadyForSearch = false;
        this.cdr.detectChanges();
      }
    });
  }

  startPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }

    this.pollInterval = setInterval(() => {
      this.http.get<StatusResponse>('http://127.0.0.1:8000/status').subscribe({
        next: (res) => {
          console.log('STATUS RESPONSE:', res);

          this.message = res.message ?? '';
          this.progress = Number(res.progress ?? 0);

          if (res.status === 'running') {
            this.isPreparing = true;
            this.isReadyForSearch = false;
          }

          if (res.status === 'done') {
            this.message = 'Završeno';
            this.progress = 100;
            this.isPreparing = false;
            this.isReadyForSearch = true;
            clearInterval(this.pollInterval);
            this.loadVideos();
          }

          if (res.status === 'error') {
            this.message = 'Greška: ' + (res.error ?? 'Nepoznata greška');
            this.isPreparing = false;
            this.isReadyForSearch = false;
            clearInterval(this.pollInterval);
          }

          this.cdr.detectChanges();
        },
        error: () => {
          this.message = 'Greška pri provjeri statusa.';
          this.isPreparing = false;
          this.isReadyForSearch = false;
          this.cdr.detectChanges();
          clearInterval(this.pollInterval);
        }
      });
    }, 500);
  }

  loadVideos() {
    this.http.get<VideoItem[]>('http://127.0.0.1:8000/videos').subscribe({
      next: (res) => {
        this.videos = res || [];
        this.cdr.detectChanges();
      },
      error: () => {
        this.videos = [];
        this.cdr.detectChanges();
      }
    });
  }

  formatDuration(totalSeconds: number): string {
    const sec = Math.max(0, Number(totalSeconds || 0));
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;

    if (h > 0) {
      return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    return `${m}:${String(s).padStart(2, '0')}`;
  }

  searchPlaceholder() {
    console.log('Search placeholder:', this.query);
  }
  getThumbnail(video: any): string {
  return `https://img.youtube.com/vi/${video.video_id}/maxresdefault.jpg`;
}
}