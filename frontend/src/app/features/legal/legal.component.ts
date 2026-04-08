import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { SupabaseService } from '../../services/supabase.service';

@Component({
  selector: 'app-legal',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './legal.component.html',
  styleUrl: './legal.component.css',
})
export class LegalComponent implements OnInit {
  private router = inject(Router);
  private auth = inject(AuthService);
  private sb = inject(SupabaseService);

  loading = true;
  documentos: any[] = [];

  temas = [
    { emoji: '🏠', title: 'Contratos de alquiler', desc: 'Derechos del inquilino, cláusulas abusivas, rescisión.' },
    { emoji: '👷', title: 'Derechos laborales', desc: 'Despidos, liquidaciones, trabajo informal.' },
    { emoji: '💸', title: 'Deudas y cobros', desc: 'Prescripción, negociación, embargo de sueldo.' },
    { emoji: '🚗', title: 'Accidentes de tránsito', desc: 'Seguro, responsabilidad civil, reclamos.' },
    { emoji: '👪', title: 'Familia', desc: 'Alimentos, divorcio, tenencia, herencias.' },
    { emoji: '🏦', title: 'Consumidor', desc: 'Defensa del consumidor, devoluciones, fraudes.' },
    { emoji: '📋', title: 'Trámites burocráticos', desc: 'Documentación, habilitaciones, certificaciones.' },
    { emoji: '💻', title: 'Delitos digitales', desc: 'Estafas online, phishing, violación de privacidad.' },
  ];

  ngOnInit(): void {
    if (!this.auth.session()) {
      this.router.navigate(['/login']);
      return;
    }
    this.loadDocumentos();
  }

  private async loadDocumentos(): Promise<void> {
    this.loading = true;
    try {
      const { data } = await this.sb.client
        .from('legal_documents')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10);

      this.documentos = data ?? [];
    } catch (e) {
      console.warn('legal_documents not available:', e);
    } finally {
      this.loading = false;
    }
  }

  formatEstado(estado: string): string {
    const map: Record<string, string> = {
      pendiente_revision: 'Pendiente',
      firmado: 'Firmado',
      archivado: 'Archivado',
    };
    return map[estado] ?? estado;
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}
