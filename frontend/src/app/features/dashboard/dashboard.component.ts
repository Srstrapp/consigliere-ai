import { Component, OnInit, inject, PLATFORM_ID, signal } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { Router } from '@angular/router';

import {
  LucideAngularModule,
  Wallet,
  Brain,
  Scale,
  LayoutDashboard,
  Settings,
  LogOut,
  Bell,
  Search,
  Plus,
  TrendingUp,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  Menu,
  X,
} from 'lucide-angular';
import { AuthService } from '../../services/auth.service';
import { SupabaseService } from '../../services/supabase.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit {
  private readonly platformId = inject(PLATFORM_ID);
  readonly auth = inject(AuthService);
  private readonly sb = inject(SupabaseService);
  private readonly router = inject(Router);

  // Icons
  readonly Wallet = Wallet;
  readonly Brain = Brain;
  readonly Scale = Scale;
  readonly LayoutDashboard = LayoutDashboard;
  readonly Settings = Settings;
  readonly LogOut = LogOut;
  readonly Bell = Bell;
  readonly Search = Search;
  readonly Plus = Plus;
  readonly TrendingUp = TrendingUp;
  readonly Target = Target;
  readonly AlertTriangle = AlertTriangle;
  readonly CheckCircle = CheckCircle;
  readonly Clock = Clock;
  readonly Menu = Menu;
  readonly X = X;

  activeDomain = 'dashboard';
  sidebarOpen = signal(false);

  toggleSidebar(): void {
    this.sidebarOpen.update(v => !v);
  }

  closeSidebar(): void {
    this.sidebarOpen.set(false);
  }

  // ── Financial ──
  gastos: any[] = [];
  metas: any[] = [];
  deudas: any[] = [];
  presupuestoMensual = 0;
  totalGastadoMes = 0;
  loadingData = true;

  // ── Emocional ──
  ultimoCheckin: any = null;
  energiaNivel = 0;

  // ── Legal ──
  asuntoLegalActivo: any = null;

  get greeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Buenos días';
    if (hour < 19) return 'Buenas tardes';
    return 'Buenas noches';
  }

  get porcentajeGastado(): number {
    if (!this.presupuestoMensual) return 0;
    return Math.min(Math.round((this.totalGastadoMes / this.presupuestoMensual) * 100), 100);
  }

  get totalDeudas(): number {
    return this.deudas.reduce((acc, d) => acc + (d.monto_total - d.monto_pagado), 0);
  }

  ngOnInit(): void {
    this.loadData();
    if (isPlatformBrowser(this.platformId)) {
      this.initAnimations();
    }
  }

  private async loadData(): Promise<void> {
    const user = this.auth.user();
    if (!user) return;

    // Obtenemos el user_id de la tabla users (bot) usando el auth_user_id
    const startOfMonth = new Date();
    startOfMonth.setDate(1);
    startOfMonth.setHours(0, 0, 0, 0);

    try {
      // Buscamos el user del bot para tener su ID y presupuesto
      const { data: botUser } = await this.sb.client
        .from('users')
        .select('id, presupuesto_mensual')
        .limit(1)
        .single();

      if (!botUser) {
        // Admin login — buscar presupuesto en user_settings si existe
        const { data: settings } = await this.sb.client
          .from('user_settings')
          .select('presupuesto_mensual')
          .eq('user_id', user.id)
          .single();
        this.presupuestoMensual = settings?.presupuesto_mensual ?? 0;
      } else {
        this.presupuestoMensual = botUser.presupuesto_mensual ?? 0;
      }

      const userId = botUser?.id ?? user.id;

      // Disparamos todo en paralelo
      const [gastosRes, metasRes, deudasRes, checkinRes, legalRes] = await Promise.allSettled([
        this.sb.client
          .from('expenses')
          .select('*')
          .eq('user_id', userId)
          .order('created_at', { ascending: false })
          .limit(5),

        this.sb.client
          .from('goals')
          .select('*')
          .eq('user_id', userId)
          .order('created_at', { ascending: false })
          .limit(4),

        this.sb.client
          .from('debts')
          .select('*')
          .eq('user_id', userId)
          .eq('estado', 'pendiente')
          .order('fecha_vencimiento', { ascending: true })
          .limit(4),

        this.sb.client
          .from('emotional_checkins')
          .select('nivel_energia, emocion_principal, created_at')
          .eq('user_id', userId)
          .order('created_at', { ascending: false })
          .limit(1)
          .single(),

        this.sb.client
          .from('legal_documents')
          .select('titulo, resumen, estado')
          .eq('user_id', userId)
          .neq('estado', 'archivado')
          .order('created_at', { ascending: false })
          .limit(1)
          .single(),
      ]);

      // Gastos
      if (gastosRes.status === 'fulfilled' && gastosRes.value.data) {
        this.gastos = gastosRes.value.data;
        this.totalGastadoMes = this.gastos.reduce((acc, g) => acc + Number(g.monto ?? 0), 0);
      }

      // Metas
      if (metasRes.status === 'fulfilled' && metasRes.value.data) {
        this.metas = metasRes.value.data;
      }

      // Deudas
      if (deudasRes.status === 'fulfilled' && deudasRes.value.data) {
        this.deudas = deudasRes.value.data;
      }

      // Checkin emocional
      if (checkinRes.status === 'fulfilled' && checkinRes.value.data) {
        this.ultimoCheckin = checkinRes.value.data;
        this.energiaNivel = this.ultimoCheckin?.nivel_energia ?? 0;
      }

      // Legal
      if (legalRes.status === 'fulfilled' && legalRes.value.data) {
        this.asuntoLegalActivo = legalRes.value.data;
      }

    } catch (e) {
      console.warn('Error loading dashboard data:', e);
    } finally {
      this.loadingData = false;
    }
  }

  private async initAnimations(): Promise<void> {
    try {
      const gsap = (await import('gsap')).default;
      gsap.fromTo(
        '.dash-card',
        { y: 20, opacity: 0 },
        { duration: 0.6, y: 0, opacity: 1, stagger: 0.08, ease: 'power3.out', delay: 0.1 }
      );
      gsap.fromTo(
        'aside',
        { opacity: 0 },
        { duration: 0.7, opacity: 1, ease: 'power3.out' }
      );
    } catch (_) {}
  }

  setDomain(domain: string): void {
    this.closeSidebar();
    if (domain === 'metanoia') {
      this.router.navigate(['/psicologia']);
    } else if (domain === 'legal') {
      this.router.navigate(['/legal']);
    } else {
      this.activeDomain = domain;
    }
  }

  async signOut(): Promise<void> {
    await this.auth.signOut();
  }

  formatMonto(monto: number | string): string {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(monto));
  }

  getMetaProgreso(meta: any): number {
    if (!meta.meta_amount) return 0;
    return Math.min(Math.round((meta.current_amount / meta.meta_amount) * 100), 100);
  }

  getCategoryIcon(_: string): any {
    return Wallet;
  }
}
