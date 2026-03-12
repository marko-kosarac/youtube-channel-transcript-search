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

  searchPlaceholder() {
    console.log('Search placeholder:', this.query);
  }
}