import { Component, OnDestroy, computed, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef } from '@angular/core';

type StatusResponse = {
  status: 'idle' | 'running' | 'done' | 'error';
  message: string;
  progress: number;
  error: string | null;
  videos_ready?: boolean;
};

type VideoItem = {
  video_id: string;
  title: string;
  duration: number;
  thumbnail?: string;
  url: string;
};

type SearchResultItem = {
  video_id: string;
  seconds: number;
  timestamp: string;
  url: string;
  snippet: string;
};

type SearchResponse = {
  ok: boolean;
  message: string;
  query: string;
  mode?: string;
  count: number;
  results: SearchResultItem[];
  error?: string;
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnDestroy {
  private readonly apiBase = 'http://127.0.0.1:8000';

  channel = '';
  query = '';

  message = 'Unesi naziv YouTube kanala.';
  progress = 0;

  isPreparing = false;
  isReadyForSearch = false;
  isSearching = false;
  searchMessage = '';

  videosVisible = false;
  private videosLoaded = false;

  videos = signal<VideoItem[]>([]);
  searchResults = signal<SearchResultItem[]>([]);
  private pollIntervalId: ReturnType<typeof setInterval> | null = null;

  filteredVideos = computed(() => {
    return this.videos();
  });

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnDestroy(): void {
    this.stopPolling();
  }

  private buildChannelUrl(channelInput: string): string {
    const value = channelInput.trim();

    if (!value) return '';

    if (value.startsWith('http://') || value.startsWith('https://')) {
      try {
        const url = new URL(value);
        const path = url.pathname.replace(/\/+$/, '');

        if (!path.endsWith('/videos')) {
          url.pathname = `${path}/videos`;
        }

        return url.toString();
      } catch {
        return value;
      }
    }

    const clean = value.replace(/^@/, '');
    return `https://www.youtube.com/@${clean}/videos`;
  }

  prepareChannel(): void {
    if (!this.channel.trim()) {
      this.message = 'Unesi naziv kanala.';
      return;
    }

    const fullChannelUrl = this.buildChannelUrl(this.channel);

    this.stopPolling();

    this.message = 'Procesiranje kanala...';
    this.progress = 0;
    this.isPreparing = true;
    this.isReadyForSearch = false;
    this.isSearching = false;
    this.searchMessage = '';
    this.videosVisible = false;
    this.videosLoaded = false;
    this.videos.set([]);
    this.searchResults.set([]);
    this.cdr.detectChanges();

    this.http.post<{ ok: boolean; message: string }>(`${this.apiBase}/prepare`, {
      channel: fullChannelUrl,
    }).subscribe({
      next: (res) => {
        if (!res.ok) {
          this.message = res.message || 'Obrada se nije mogla pokrenuti.';
          this.isPreparing = false;
          this.cdr.detectChanges();
          return;
        }

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

  private startPolling(): void {
    this.stopPolling();

    this.pollIntervalId = setInterval(() => {
      this.http.get<StatusResponse>(`${this.apiBase}/status`).subscribe({
        next: (res) => {
          this.message = res.message ?? '';
          this.progress = Number(res.progress ?? 0);

          const videosReady = !!res.videos_ready;

          if (videosReady) {
            this.videosVisible = true;

            if (!this.videosLoaded) {
              this.videosLoaded = true;
              this.loadVideos();
            }
          }

          if (res.status === 'running') {
            this.isPreparing = true;
            this.isReadyForSearch = false;
            this.cdr.detectChanges();
            return;
          }

          if (res.status === 'done') {
            this.message = 'Završeno';
            this.progress = 100;
            this.isPreparing = false;
            this.isReadyForSearch = true;
            this.videosVisible = true;

            if (!this.videosLoaded) {
              this.videosLoaded = true;
              this.loadVideos();
            }

            this.stopPolling();
            this.cdr.detectChanges();
            return;
          }

          if (res.status === 'error') {
            this.message = 'Greška: ' + (res.error ?? 'Nepoznata greška');
            this.isPreparing = false;
            this.isReadyForSearch = false;
            this.stopPolling();
            this.cdr.detectChanges();
            return;
          }

          if (res.status === 'idle') {
            this.isPreparing = false;
            this.cdr.detectChanges();
          }
        },
        error: () => {
          this.message = 'Greška pri proveri statusa.';
          this.isPreparing = false;
          this.isReadyForSearch = false;
          this.stopPolling();
          this.cdr.detectChanges();
        }
      });
    }, 700);
  }

  private stopPolling(): void {
    if (this.pollIntervalId) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
    }
  }

  loadVideos(): void {
    this.http.get<VideoItem[]>(`${this.apiBase}/videos`).subscribe({
      next: (res) => {
        this.videos.set(res || []);
        this.cdr.detectChanges();
      },
      error: () => {
        this.videos.set([]);
        this.cdr.detectChanges();
      }
    });
  }

  get displayChannelName(): string {
    const value = this.channel.trim();

    if (!value) return '';

    if (value.startsWith('http://') || value.startsWith('https://')) {
      try {
        const url = new URL(value);
        const parts = url.pathname.split('/').filter(Boolean);

        if (parts.length === 0) return value;

        const handlePart = parts.find(part => part.startsWith('@'));
        if (handlePart) {
          return decodeURIComponent(handlePart).replace(/^@/, '');
        }

        if (parts[parts.length - 1] === 'videos' && parts.length >= 2) {
          return decodeURIComponent(parts[parts.length - 2]).replace(/^@/, '');
        }

        return decodeURIComponent(parts[parts.length - 1]).replace(/^@/, '');
      } catch {
        return value.replace(/^@/, '');
      }
    }

    return value.replace(/^@/, '');
  }

  runSearch(): void {
    const q = this.query.trim();

    if (!q) {
      this.searchResults.set([]);
      this.searchMessage = '';
      this.cdr.detectChanges();
      return;
    }

    this.isSearching = true;
    this.searchMessage = 'Pretraga u toku...';
    this.searchResults.set([]);
    this.cdr.detectChanges();

    this.http.get<SearchResponse>(`${this.apiBase}/search`, {
      params: { query: q }
    }).subscribe({
      next: (res) => {
        this.isSearching = false;

        if (!res.ok) {
          this.searchMessage = res.message || 'Pretraga nije uspela.';
          this.searchResults.set([]);
          this.cdr.detectChanges();
          return;
        }

        this.searchResults.set(res.results || []);
        this.searchMessage = `Pronađeno: ${res.count} rezultata`;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isSearching = false;
        this.searchMessage = 'Greška pri pretrazi.';
        this.searchResults.set([]);
        this.cdr.detectChanges();
      }
    });
  }

  getVideoTitle(videoId: string): string {
    const found = this.videos().find(v => v.video_id === videoId);
    return found?.title || videoId;
  }

  getVideoById(videoId: string): VideoItem | undefined {
    return this.videos().find(v => v.video_id === videoId);
  }

  getResultThumbnail(videoId: string): string {
    const video = this.getVideoById(videoId);

    if (video?.thumbnail && video.thumbnail.trim()) {
      return video.thumbnail;
    }

    return `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
  }

  onResultThumbnailError(event: Event, videoId: string): void {
    const img = event.target as HTMLImageElement;

    if (img.dataset['fallbackApplied'] === 'true') {
      img.src = 'https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png';
      return;
    }

    img.dataset['fallbackApplied'] = 'true';
    img.src = `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
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

  getThumbnail(video: VideoItem): string {
    if (video.thumbnail && video.thumbnail.trim()) {
      return video.thumbnail;
    }

    return `https://img.youtube.com/vi/${video.video_id}/hqdefault.jpg`;
  }

  onThumbnailError(event: Event, video: VideoItem): void {
    const img = event.target as HTMLImageElement;

    if (img.dataset['fallbackApplied'] === 'true') {
      img.src = 'https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png';
      return;
    }

    img.dataset['fallbackApplied'] = 'true';
    img.src = `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`;
  }

  trackByVideoId(_: number, video: VideoItem): string {
    return video.video_id;
  }

  trackByResult(_: number, result: SearchResultItem): string {
    return `${result.video_id}-${result.seconds}-${result.timestamp}`;
  }
}