import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { SupabaseService } from '../../services/supabase.service';

@Component({
  selector: 'app-psicologia',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './psicologia.component.html',
  styleUrl: './psicologia.component.css',
})
export class PsicologiaComponent implements OnInit {
  private router = inject(Router);
  private auth = inject(AuthService);
  private sb = inject(SupabaseService);

  loading = true;
  checkins: any[] = [];
  ultimoCheckin: any = null;

  features = [
    { emoji: '💬', title: 'Apoyo emocional', desc: 'Conversaciones de apoyo empático en tiempo real sin juicios.' },
    { emoji: '🌱', title: 'Crecimiento personal', desc: 'Reflexiones, herramientas cognitivas y seguimiento de hábitos.' },
    { emoji: '😌', title: 'Check-in diario', desc: '¿Cómo te sentís hoy? Registrá tu estado con /bienestar.' },
    { emoji: '🎯', title: 'Metas de bienestar', desc: 'Establecé objetivos personales y hacé seguimiento de tu progreso.' },
  ];

  ngOnInit(): void {
    if (!this.auth.session()) {
      this.router.navigate(['/login']);
      return;
    }
    this.loadCheckins();
  }

  private async loadCheckins(): Promise<void> {
    this.loading = true;
    try {
      const { data } = await this.sb.client
        .from('emotional_checkins')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10);

      this.checkins = data ?? [];
      this.ultimoCheckin = this.checkins[0] ?? null;
    } catch (e) {
      console.warn('emotional_checkins not available:', e);
    } finally {
      this.loading = false;
    }
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}
