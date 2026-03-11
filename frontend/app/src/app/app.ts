import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  imports: [FormsModule, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  channel = '';
  message = '';
  jobId = '';

  constructor(private http: HttpClient) {}

  prepareChannel() {
    if (!this.channel.trim()) {
      this.message = 'Unesi URL kanala.';
      return;
    }

    this.message = 'Šaljem zahtjev za pripremu kanala...';
    this.jobId = '';

    this.http.post<any>('http://127.0.0.1:8000/prepare', {
      channel: this.channel
    }).subscribe({
      next: (res) => {
        this.jobId = res.job_id;
        this.message = 'Priprema kanala je pokrenuta.';
      },
      error: () => {
        this.message = 'Greška pri pokretanju pripreme kanala.';
      }
    });
  }
}