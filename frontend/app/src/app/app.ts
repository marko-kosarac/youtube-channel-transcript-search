import { Component, ChangeDetectorRef } from '@angular/core';import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

type StatusResponse = {
  status: string
  message: string
  progress: number
  error: string | null
}

@Component({
  selector: 'app-root',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {

  channel = ''

  message = 'Unesi kanal.'
  progress = 0

  isPreparing = false

  pollInterval: any

constructor(
  private http: HttpClient,
  private cdr: ChangeDetectorRef
) {}

  prepareChannel() {

    if (!this.channel.trim()) {
      this.message = 'Unesi URL kanala'
      return
    }

    this.message = 'Šaljem zahtjev...'
    this.progress = 0
    this.isPreparing = true

    this.http.post('http://127.0.0.1:8000/prepare', {
      channel: this.channel
    }).subscribe({

      next: () => {
        this.message = 'Procesiranje kanala...'
        this.cdr.detectChanges();
        this.startPolling()
      },

      error: () => {
        this.message = 'Greška pri pokretanju.'
        this.isPreparing = false
      }

    })
  }

startPolling() {
  if (this.pollInterval) {
    clearInterval(this.pollInterval);
  }

  this.pollInterval = setInterval(() => {
    this.http.get<StatusResponse>('http://127.0.0.1:8000/status').subscribe({
      next: (res) => {
        console.log('STATUS RESPONSE:', res);

        this.message = res.message;
        this.progress = res.progress;
        this.cdr.detectChanges();

        if (res.status === 'done') {
          this.message = 'Završeno';
          this.progress = 100;
          this.isPreparing = false;
          this.cdr.detectChanges();
          clearInterval(this.pollInterval);
        }

        if (res.status === 'error') {
          this.message = 'Greška: ' + (res.error ?? 'Nepoznata greška');
          this.isPreparing = false;
          this.cdr.detectChanges();
          clearInterval(this.pollInterval);
        }
      },
      error: (err) => {
        console.error('STATUS ERROR:', err);
      }
    });
  }, 500);
}

}